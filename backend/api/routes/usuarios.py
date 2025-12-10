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
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_auth_db
from backend.api.deps.permissions import require_role, ROLE_ADMIN, CLINICAL_ROLES
from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario
from backend.schemas.auth.auth_utils import hash_password


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
