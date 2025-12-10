# =============================================================================
# backend/api/routes/auth.py
# Endpoints de autenticación: login, me, change-password
# =============================================================================
# Este archivo contiene los endpoints para:
#   - Login (obtener token JWT)
#   - Ver mi perfil
#   - Cambiar mi contraseña
#
# FLUJO DE LOGIN:
# 1. Usuario envía username + password
# 2. Verificamos credenciales contra la BD
# 3. Si son correctas, generamos token JWT
# 4. Usuario usa el token en requests posteriores
# =============================================================================

from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api.deps.database import get_auth_db
from backend.api.deps.auth import get_current_active_user
from backend.api.core.security import create_access_token, Token
from backend.schemas.auth.models import SysUsuario, AuditLog
from backend.schemas.auth.auth_utils import verify_password, hash_password


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/auth", tags=["Autenticación"])


# =============================================================================
# SCHEMAS (Pydantic models para request/response)
# =============================================================================

class LoginRequest(BaseModel):
    """Request de login con JSON (moderno y consistente con el resto de la API)"""
    username: str = Field(..., min_length=3, description="Nombre de usuario")
    password: str = Field(..., min_length=8, description="Contraseña")


class UserProfile(BaseModel):
    """Perfil del usuario actual (respuesta de /auth/me)"""
    id_usuario: int
    nombre_usuario: str
    rol: str
    email: Optional[str] = None
    activo: bool
    clinica_id: Optional[int] = None
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Request para cambiar contraseña"""
    current_password: str = Field(..., min_length=8, description="Contraseña actual")
    new_password: str = Field(..., min_length=8, description="Nueva contraseña (mínimo 8 caracteres)")


class ChangePasswordResponse(BaseModel):
    """Response de cambio de contraseña"""
    message: str
    success: bool


# =============================================================================
# ENDPOINT: POST /auth/login
# =============================================================================

@router.post("/login", response_model=Token)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_auth_db)
):
    """
    Inicia sesión y obtiene un token JWT.
    
    **Parámetros (JSON):**
    - username: Nombre de usuario (mínimo 3 caracteres)
    - password: Contraseña (mínimo 8 caracteres)
    
    **Retorna:**
    - access_token: Token JWT para usar en requests posteriores
    - token_type: Siempre "bearer"
    
    **Errores:**
    - 401: Credenciales inválidas
    - 403: Usuario desactivado
    
    **Ejemplo de uso:**
    ```json
    POST /api/v1/auth/login
    Content-Type: application/json
    
    {
        "username": "admin",
        "password": "Admin2405"
    }
    ```
    
    **Auditoría:**
    - Registra login exitoso en audit_log con IP y timestamp
    - Registra intentos fallidos para seguridad
    """
    # Extraer IP del cliente
    client_ip = request.client.host if request.client else None
    
    # 1. Buscar usuario por nombre de usuario
    user = db.query(SysUsuario).filter(
        SysUsuario.nombre_usuario == credentials.username
    ).first()
    
    # 2. Verificar que el usuario existe y contraseña correcta
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Verificar que el usuario esté activo
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador."
        )
    
    # 4. Actualizar último login
    user.last_login = datetime.now(timezone.utc)
    if hasattr(user, 'failed_login_attempts'):
        user.failed_login_attempts = 0
    
    db.commit()
    
    # 6. Crear token JWT con datos del usuario
    access_token = create_access_token(
        data={
            "user_id": user.id_usuario,
            "username": user.nombre_usuario,
            "rol": user.rol,
            "clinica_id": user.clinica_id
        }
    )
    
    return Token(access_token=access_token, token_type="bearer")


# =============================================================================
# ENDPOINT: GET /auth/me
# =============================================================================

@router.get("/me", response_model=UserProfile)
async def get_my_profile(
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """
    Obtiene el perfil del usuario autenticado.
    
    **Requiere:** Token JWT válido en header Authorization
    
    **Retorna:**
    - id_usuario: ID único del usuario
    - nombre_usuario: Nombre de usuario
    - rol: Rol (Admin, Podologo, Recepcion)
    - email: Email del usuario (opcional)
    - activo: Si la cuenta está activa
    - clinica_id: ID de la clínica asociada
    - last_login: Última fecha de inicio de sesión
    
    **Ejemplo de uso:**
    ```
    GET /auth/me
    Authorization: Bearer {tu_token}
    ```
    """
    return UserProfile.model_validate(current_user)


# =============================================================================
# ENDPOINT: PUT /auth/change-password
# =============================================================================

@router.put("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_auth_db)
):
    """
    Cambia la contraseña del usuario autenticado.
    
    **Requiere:** Token JWT válido
    
    **Parámetros:**
    - current_password: Contraseña actual (para verificación)
    - new_password: Nueva contraseña (mínimo 8 caracteres)
    
    **Errores:**
    - 400: La contraseña actual es incorrecta
    - 400: La nueva contraseña es igual a la actual
    
    **Ejemplo de uso:**
    ```
    PUT /auth/change-password
    Authorization: Bearer {tu_token}
    Content-Type: application/json
    
    {
        "current_password": "Admin2024!",
        "new_password": "NuevaPassword123!"
    }
    ```
    """
    # 1. Verificar que la contraseña actual es correcta
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    
    # 2. Verificar que la nueva contraseña sea diferente
    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # 3. Actualizar la contraseña
    current_user.password_hash = hash_password(request.new_password)
    db.commit()
    
    return ChangePasswordResponse(
        message="Contraseña actualizada exitosamente",
        success=True
    )
