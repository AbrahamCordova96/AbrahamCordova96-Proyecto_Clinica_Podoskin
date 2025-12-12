# =============================================================================
# backend/api/routes/usuarios.py
# CRUD de Usuarios del Sistema (Solo Admin)
# =============================================================================
# Este archivo implementa los endpoints de usuarios:
#   - GET /usuarios → Listar usuarios
#   - GET /usuarios/{id} → Detalle de usuario
#   - POST /usuarios → Crear usuario
#   - PUT /usuarios/{id} → Editar usuario
#   - DELETE /usuarios/{id} → Desactivar usuario
#
# PERMISOS: Todo exclusivo para Admin
# =============================================================================

from typing import Optional
from datetime import datetime, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_auth_db
from backend.api.deps.permissions import require_role, ROLE_ADMIN, CLINICAL_ROLES
from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario
from backend.schemas.auth.auth_utils import hash_password
from backend.api.core.encryption import encrypt_api_key, decrypt_api_key
from backend.api.services.gemini_validator import validate_gemini_api_key
from backend.schemas.auth.schemas import GeminiKeyUpdate, GeminiKeyStatus

# Logger para registrar operaciones importantes
logger = logging.getLogger(__name__)


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/usuarios", tags=["Usuarios del Sistema"])


# =============================================================================
# SCHEMAS
# =============================================================================

class UsuarioBase(BaseModel):
    """Campos base de usuario"""
    nombre_usuario: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    email: Optional[EmailStr] = None
    rol: str = Field(..., pattern="^(Admin|Podologo|Recepcion)$")
    clinica_id: Optional[int] = None


class UsuarioCreate(UsuarioBase):
    """Request para crear usuario"""
    password: str = Field(..., min_length=8)


class UsuarioUpdate(BaseModel):
    """Request para actualizar usuario"""
    nombre_usuario: Optional[str] = Field(None, min_length=3, max_length=50, pattern="^[a-zA-Z0-9_.]+$")
    email: Optional[EmailStr] = None
    rol: Optional[str] = Field(None, pattern="^(Admin|Podologo|Recepcion)$")
    activo: Optional[bool] = None


class UsuarioResetPassword(BaseModel):
    """Request para resetear contraseña"""
    new_password: str = Field(..., min_length=8)


class UsuarioResponse(BaseModel):
    """Response de usuario"""
    id_usuario: int
    nombre_usuario: str
    email: Optional[str] = None
    rol: str
    activo: bool
    clinica_id: Optional[int] = None
    last_login: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT: GET /usuarios
# =============================================================================

@router.get("")
async def list_usuarios(
    activo: Optional[bool] = Query(None, description="Filtrar por activos"),
    rol: Optional[str] = Query(None, description="Filtrar por rol"),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),  # Admin o Podologo pueden ver
    db: Session = Depends(get_auth_db)
):
    """
    Lista los usuarios del sistema.
    
    **Permisos:** Admin y Podologo (solo lectura para Podologo)
    """
    query = db.query(SysUsuario)
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(SysUsuario.clinica_id == current_user.clinica_id)
    
    # Aplicar filtros
    if activo is not None:
        query = query.filter(SysUsuario.activo == activo)
    if rol:
        query = query.filter(SysUsuario.rol == rol)
    
    usuarios = query.order_by(SysUsuario.nombre_usuario).all()
    
    return {
        "total": len(usuarios),
        "usuarios": [UsuarioResponse.model_validate(u) for u in usuarios]
    }


# =============================================================================
# ENDPOINT: GET /usuarios/{id}
# =============================================================================

@router.get("/{usuario_id}")
async def get_usuario(
    usuario_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_auth_db)
):
    """
    Obtiene detalle de un usuario.
    
    **Permisos:** 
    - Admin: Puede ver cualquier usuario
    - Podologo: Solo puede ver su propio perfil
    """
    # Si no es admin, solo puede ver su propio perfil
    if current_user.rol != ROLE_ADMIN and usuario_id != current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo puedes ver tu propio perfil"
        )
    
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    return UsuarioResponse.model_validate(usuario)


# =============================================================================
# ENDPOINT: POST /usuarios
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_usuario(
    data: UsuarioCreate,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_auth_db)
):
    """
    Crea un nuevo usuario del sistema.
    
    **Permisos:** Solo Admin
    
    **Roles válidos:**
    - Admin: Control total del sistema
    - Podologo: Acceso clínico completo
    - Recepcion: Solo agenda y datos básicos
    """
    # Verificar que el nombre de usuario no exista
    existing = db.query(SysUsuario).filter(
        SysUsuario.nombre_usuario == data.nombre_usuario
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El usuario '{data.nombre_usuario}' ya existe"
        )
    
    usuario = SysUsuario(
        nombre_usuario=data.nombre_usuario,
        password_hash=hash_password(data.password),
        email=data.email,
        rol=data.rol,
        clinica_id=data.clinica_id or current_user.clinica_id,
        activo=True
    )
    
    db.add(usuario)
    db.commit()
    db.refresh(usuario)
    
    return UsuarioResponse.model_validate(usuario)


# =============================================================================
# ENDPOINT: PUT /usuarios/{id}
# =============================================================================

@router.put("/{usuario_id}")
async def update_usuario(
    usuario_id: int,
    data: UsuarioUpdate,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_auth_db)
):
    """
    Actualiza un usuario del sistema.
    
    **Permisos:** Solo Admin
    
    **Nota:** No usa este endpoint para cambiar contraseñas.
    Para resetear contraseña, usar PUT /usuarios/{id}/reset-password.
    """
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Prevenir que se desactive al propio admin
    if data.activo is False and usuario_id == current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivarte a ti mismo"
        )
    
    # Verificar nombre único si se está cambiando
    if data.nombre_usuario and data.nombre_usuario != usuario.nombre_usuario:
        existing = db.query(SysUsuario).filter(
            SysUsuario.nombre_usuario == data.nombre_usuario
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario '{data.nombre_usuario}' ya existe"
            )
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(usuario, field, value)
    
    db.commit()
    db.refresh(usuario)
    
    return UsuarioResponse.model_validate(usuario)


# =============================================================================
# ENDPOINT: PUT /usuarios/{id}/reset-password
# =============================================================================

@router.put("/{usuario_id}/reset-password")
async def reset_usuario_password(
    usuario_id: int,
    data: UsuarioResetPassword,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_auth_db)
):
    """
    Resetea la contraseña de un usuario.
    
    **Permisos:** Solo Admin
    
    **Nota:** El admin establece una nueva contraseña que el usuario
    debe cambiar en su próximo login.
    """
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    usuario.password_hash = hash_password(data.new_password)
    db.commit()
    
    return {
        "message": f"Contraseña de '{usuario.nombre_usuario}' reseteada exitosamente"
    }


# =============================================================================
# ENDPOINT: DELETE /usuarios/{id}
# =============================================================================

@router.delete("/{usuario_id}")
async def delete_usuario(
    usuario_id: int,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_auth_db)
):
    """
    Desactiva un usuario del sistema.
    
    **Permisos:** Solo Admin
    
    **Nota:** No elimina, solo desactiva (activo=False).
    """
    if usuario_id == current_user.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes desactivarte a ti mismo"
        )
    
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    usuario.activo = False
    db.commit()
    
    return {"message": f"Usuario '{usuario.nombre_usuario}' desactivado", "id": usuario_id}


# =============================================================================
# ENDPOINT: GET /usuarios/{id}/gemini-key/status
# Obtiene el estado de la API Key de Gemini del usuario
# =============================================================================

@router.get("/{usuario_id}/gemini-key/status", response_model=GeminiKeyStatus)
async def get_gemini_key_status(
    usuario_id: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Obtiene el estado de la API Key de Gemini del usuario.
    
    Este endpoint permite verificar:
    - Si el usuario tiene una API Key configurada
    - Si la API Key es válida (hace validación en tiempo real)
    - Cuándo fue la última actualización
    - Cuándo fue la última validación exitosa
    
    **Permisos:** 
    - Un usuario puede ver su propio estado
    - Admin puede ver el estado de cualquier usuario
    
    **Uso típico:**
    - Frontend llama este endpoint al cargar el perfil del usuario
    - Si has_key=False, mostrar botón "Configurar API Key"
    - Si has_key=True pero is_valid=False, mostrar advertencia
    
    **Respuesta:**
    ```json
    {
        "has_key": true,
        "is_valid": true,
        "last_updated": "2024-12-12T10:30:00Z",
        "last_validated": "2024-12-12T10:30:00Z"
    }
    ```
    """
    # Control de acceso: Solo el propio usuario o Admin pueden ver el estado
    if usuario_id != current_user.id_usuario and current_user.rol != ROLE_ADMIN:
        logger.warning(f"Usuario {current_user.id_usuario} intentó acceder al estado de API Key del usuario {usuario_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver esta información"
        )
    
    # Buscar el usuario en la base de datos
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar si tiene API Key configurada
    has_key = bool(usuario.gemini_api_key_encrypted)
    
    # Si tiene key, verificar si es válida haciendo una llamada a la API de Google
    # NOTA: Esto valida en cada llamada, lo cual puede causar rate limiting si se
    # llama frecuentemente. En producción, considerar cachear el resultado por ~1 hora.
    # Ejemplo: usar Redis o una variable de caché en memoria con TTL.
    is_valid = None
    if has_key:
        try:
            # Desencriptar la API Key
            decrypted_key = decrypt_api_key(usuario.gemini_api_key_encrypted)
            # Validar contra la API de Gemini
            is_valid, _ = await validate_gemini_api_key(decrypted_key)
            logger.info(f"Validación de API Key para usuario {usuario_id}: {'válida' if is_valid else 'inválida'}")
        except Exception as e:
            logger.error(f"Error validando API Key para usuario {usuario_id}: {e}")
            is_valid = False
    
    return GeminiKeyStatus(
        has_key=has_key,
        is_valid=is_valid,
        last_updated=usuario.gemini_api_key_updated_at,
        last_validated=usuario.gemini_api_key_last_validated
    )


# =============================================================================
# ENDPOINT: PUT /usuarios/{id}/gemini-key
# Actualiza la API Key de Gemini del usuario
# =============================================================================

@router.put("/{usuario_id}/gemini-key")
async def update_gemini_key(
    usuario_id: int,
    data: GeminiKeyUpdate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Actualiza la API Key de Gemini del usuario.
    
    Proceso de actualización:
    1. Valida permisos (usuario propio o Admin)
    2. Verifica que el usuario existe
    3. Valida la API Key contra la API de Google Gemini
    4. Si es válida, la encripta con Fernet
    5. Guarda en la base de datos
    6. Actualiza los timestamps
    
    **Permisos:** 
    - Un usuario puede actualizar su propia API Key
    - Admin puede actualizar la API Key de cualquier usuario
    
    **Seguridad:**
    - La API Key se valida antes de guardar (evita keys inválidas)
    - Se encripta con Fernet antes de almacenar en BD (nunca en texto plano)
    - Se loguea la operación para auditoría (sin exponer la key)
    
    **Request body:**
    ```json
    {
        "api_key": "AIzaSyC1234567890abcdefghijklmnopqrstuv"
    }
    ```
    
    **Respuesta exitosa (200):**
    ```json
    {
        "message": "API Key de Gemini actualizada exitosamente",
        "status": "valid",
        "updated_at": "2024-12-12T10:30:00Z"
    }
    ```
    
    **Errores:**
    - 400: API Key inválida (no pasa validación de Google)
    - 403: Sin permisos para modificar la API Key de este usuario
    - 404: Usuario no encontrado
    - 500: Error al guardar la API Key
    """
    # Control de acceso: Solo el propio usuario o Admin pueden actualizar
    if usuario_id != current_user.id_usuario and current_user.rol != ROLE_ADMIN:
        logger.warning(f"Usuario {current_user.id_usuario} intentó modificar API Key del usuario {usuario_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar esta API Key"
        )
    
    # Buscar el usuario en la base de datos
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # PASO CRÍTICO: Validar API Key contra la API de Gemini ANTES de guardar
    # Esto evita almacenar keys incorrectas o expiradas
    logger.info(f"Validando API Key de Gemini para usuario {usuario_id} (key empieza con: {data.api_key[:10]}...)")
    is_valid, validation_message = await validate_gemini_api_key(data.api_key)
    
    if not is_valid:
        logger.warning(f"API Key inválida para usuario {usuario_id}: {validation_message}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"API Key inválida: {validation_message}"
        )
    
    # API Key válida: encriptar y guardar
    try:
        # Encriptar la API Key con Fernet
        encrypted_key = encrypt_api_key(data.api_key)
        
        # Actualizar los campos en el modelo
        usuario.gemini_api_key_encrypted = encrypted_key
        # Usar datetime.now(timezone.utc) en lugar de sql_func.now() para consistencia
        # con el resto de la aplicación y mejor control en Python
        usuario.gemini_api_key_updated_at = datetime.now(timezone.utc)
        usuario.gemini_api_key_last_validated = datetime.now(timezone.utc)
        
        # Guardar en la base de datos
        db.commit()
        
        logger.info(f"✓ API Key de Gemini actualizada exitosamente para usuario {usuario_id}")
        
        return {
            "message": "API Key de Gemini actualizada exitosamente",
            "status": "valid",
            "updated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"✗ Error guardando API Key encriptada para usuario {usuario_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la API Key"
        )


# =============================================================================
# ENDPOINT: DELETE /usuarios/{id}/gemini-key
# Elimina la API Key de Gemini del usuario
# =============================================================================

@router.delete("/{usuario_id}/gemini-key")
async def delete_gemini_key(
    usuario_id: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Elimina la API Key de Gemini del usuario.
    
    Este endpoint realiza un "borrado suave" estableciendo los campos
    de API Key a NULL. No se elimina el usuario, solo su API Key.
    
    **Casos de uso:**
    - Usuario quiere revocar el acceso del sistema a su API Key
    - Usuario quiere cambiar a una cuenta de Google diferente
    - Admin necesita forzar reconfiguración por seguridad
    
    **Permisos:** 
    - Un usuario puede eliminar su propia API Key
    - Admin puede eliminar la API Key de cualquier usuario
    
    **Respuesta exitosa (200):**
    ```json
    {
        "message": "API Key de Gemini eliminada exitosamente"
    }
    ```
    
    **Errores:**
    - 403: Sin permisos para eliminar la API Key de este usuario
    - 404: Usuario no encontrado o no tiene API Key configurada
    """
    # Control de acceso: Solo el propio usuario o Admin pueden eliminar
    if usuario_id != current_user.id_usuario and current_user.rol != ROLE_ADMIN:
        logger.warning(f"Usuario {current_user.id_usuario} intentó eliminar API Key del usuario {usuario_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta API Key"
        )
    
    # Buscar el usuario en la base de datos
    usuario = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == usuario_id
    ).first()
    
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Verificar que el usuario tenga una API Key configurada
    if not usuario.gemini_api_key_encrypted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Este usuario no tiene API Key configurada"
        )
    
    # Eliminar la API Key (borrado suave: establecer campos a NULL)
    usuario.gemini_api_key_encrypted = None
    usuario.gemini_api_key_updated_at = None
    usuario.gemini_api_key_last_validated = None
    
    db.commit()
    
    logger.info(f"✓ API Key de Gemini eliminada para usuario {usuario_id}")
    
    return {
        "message": "API Key de Gemini eliminada exitosamente"
    }
