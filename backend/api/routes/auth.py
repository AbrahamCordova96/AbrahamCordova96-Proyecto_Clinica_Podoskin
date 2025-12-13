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
#
# SEGURIDAD:
# - Rate limiting: 5 intentos de login por minuto por IP
# - Password migration: Automatic upgrade from bcrypt to Argon2
# =============================================================================

from datetime import datetime, timezone, timedelta
from typing import Optional
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, Field, field_validator
from slowapi import Limiter
from slowapi.util import get_remote_address
import re

from backend.api.deps.database import get_auth_db
from backend.api.deps.auth import get_current_active_user
from backend.api.core.security import create_access_token, Token
from backend.api.core.config import get_settings
from backend.schemas.auth.models import SysUsuario, AuditLog
from backend.schemas.auth.auth_utils import verify_password, hash_password, needs_rehash
from backend.api.core.encryption import decrypt_api_key
from backend.api.services.gemini_validator import validate_gemini_api_key

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)

# Logger para registrar operaciones de autenticación
logger = logging.getLogger(__name__)


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


def validate_password_complexity(password: str) -> str:
    """
    Valida que la contraseña cumpla con requisitos de complejidad.
    
    Requisitos:
    - Al menos 8 caracteres
    - Al menos una letra mayúscula
    - Al menos una letra minúscula
    - Al menos un número
    - Al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)
    """
    if len(password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    
    if not re.search(r'[A-Z]', password):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")
    
    if not re.search(r'[a-z]', password):
        raise ValueError("La contraseña debe contener al menos una letra minúscula")
    
    if not re.search(r'\d', password):
        raise ValueError("La contraseña debe contener al menos un número")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password):
        raise ValueError("La contraseña debe contener al menos un carácter especial (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    
    return password


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
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Valida complejidad de la nueva contraseña"""
        return validate_password_complexity(v)


class ChangePasswordResponse(BaseModel):
    """Response de cambio de contraseña"""
    message: str
    success: bool


# =============================================================================
# ENDPOINT: POST /auth/login
# =============================================================================

@router.post("/login")
@limiter.limit("5/minute")  # Rate limit: 5 login attempts per minute per IP
async def login(
    credentials: LoginRequest,
    request: Request,
    db: Session = Depends(get_auth_db)
):
    """
    Inicia sesión y obtiene un token JWT.
    
    **NUEVO:** Ahora también verifica si el usuario tiene API Key de Gemini configurada
    y retorna información adicional del usuario.
    
    **IMPORTANTE:** Puedes hacer login con cualquiera de estos 3 métodos:
    1. **Username**: "admin" o "santiago.ornelas"
    2. **Email**: "admin@podoskin.local" o "santiago@podoskin.com"
    3. **ID estructurado**: "ASGO-1213-00001"
    
    **Parámetros (JSON):**
    - username: Puede ser cualquiera de los siguientes (mínimo 3 caracteres):
      * Nombre de usuario (ej: "admin", "santiago.ornelas")
      * Email (ej: "admin@podoskin.local")
      * ID estructurado (ej: "ASGO-1213-00001")
    - password: Contraseña (mínimo 8 caracteres)
    
    **Retorna:**
    - access_token: Token JWT para usar en requests posteriores
    - token_type: Siempre "bearer"
    - user: Información del usuario incluyendo:
      - id_usuario: ID único del usuario
      - nombre_usuario: Nombre de usuario
      - email: Email del usuario
      - rol: Rol (Admin, Podologo, Recepcion)
      - clinica_id: ID de la clínica asociada
      - has_gemini_key: Si tiene API Key de Gemini configurada (NUEVO)
      - gemini_key_status: Estado de la API Key ("valid", "invalid", "error", o null) (NUEVO)
    
    **Errores:**
    - 401: Credenciales inválidas
    - 403: Usuario desactivado o cuenta bloqueada
    
    **Ejemplo de uso (con username):**
    ```json
    {
        "username": "admin",
        "password": "Admin2024!"
    }
    ```
    
    **Ejemplo de uso (con email):**
    ```json
    {
        "username": "santiago@podoskin.com",
        "password": "Ornelas2025!"
    }
    ```
    
    **Ejemplo de uso (con ID estructurado):**
    ```json
    {
        "username": "ASGO-1213-00001",
        "password": "Ornelas2025!"
    }
    ```
    
    **Ejemplo de respuesta:**
    ```json
    {
        "access_token": "eyJ0eXAi...",
        "token_type": "bearer",
        "user": {
            "id_usuario": 1,
            "nombre_usuario": "admin",
            "email": "admin@podoskin.com",
            "rol": "Admin",
            "clinica_id": 1,
            "has_gemini_key": true,
            "gemini_key_status": "valid"
        }
    }
    ```
    
    **Auditoría:**
    - Registra login exitoso en audit_log con IP y timestamp
    - Registra intentos fallidos para seguridad
    - Valida API Key de Gemini si está configurada
    """
    # Extraer IP del cliente
    client_ip = request.client.host if request.client else None
    settings = get_settings()
    
    # 1. Buscar usuario por nombre de usuario, email o código interno (ID estructurado)
    # Permite login con cualquiera de los 3 métodos:
    # - Username: "admin" o "santiago.ornelas"
    # - Email: "admin@podoskin.local" o "santiago@podoskin.com"
    # - ID estructurado: "ASGO-1213-00001"
    user = db.query(SysUsuario).filter(
        or_(
            SysUsuario.nombre_usuario == credentials.username,
            SysUsuario.email == credentials.username,
            SysUsuario.codigo_interno == credentials.username
        )
    ).first()
    
    # 2. Verificar que el usuario existe
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 3. Verificar si la cuenta está bloqueada
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        minutes_remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() / 60)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cuenta bloqueada por múltiples intentos fallidos. Intente de nuevo en {minutes_remaining} minutos."
        )
    
    # 4. Si el bloqueo ha expirado, resetear el contador
    if user.locked_until and user.locked_until <= datetime.now(timezone.utc):
        user.locked_until = None
        user.failed_login_attempts = 0
    
    # 5. Verificar contraseña
    if not verify_password(credentials.password, user.password_hash):
        # Incrementar contador de intentos fallidos
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        
        # Bloquear cuenta si se alcanzó el máximo de intentos
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cuenta bloqueada por {settings.ACCOUNT_LOCKOUT_MINUTES} minutos debido a múltiples intentos fallidos."
            )
        
        db.commit()
        
        attempts_remaining = settings.MAX_FAILED_LOGIN_ATTEMPTS - user.failed_login_attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Credenciales inválidas. Intentos restantes: {attempts_remaining}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 6. Verificar que el usuario esté activo
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador."
        )
    
    # 7. Migrate password from bcrypt to Argon2 if needed (transparent upgrade)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(credentials.password)
    
    # 8. Actualizar último login y resetear contador de intentos fallidos
    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    user.locked_until = None
    
    db.commit()
    
    # 9. NUEVO: Verificar estado de API Key de Gemini
    has_gemini_key = bool(user.gemini_api_key_encrypted)
    gemini_key_status = None
    
    if has_gemini_key:
        try:
            # Desencriptar la API Key almacenada
            decrypted_key = decrypt_api_key(user.gemini_api_key_encrypted)
            # Validar contra la API de Google Gemini
            is_valid, _ = await validate_gemini_api_key(decrypted_key)
            
            # Establecer el estado basado en la validación
            gemini_key_status = "valid" if is_valid else "invalid"
            
            if is_valid:
                # Si es válida, actualizar el timestamp de última validación
                user.gemini_api_key_last_validated = datetime.now(timezone.utc)
                db.commit()
                logger.info(f"✓ API Key de Gemini validada exitosamente para usuario {user.id_usuario}")
            else:
                logger.warning(f"⚠ API Key de Gemini inválida para usuario {user.id_usuario}")
                
        except Exception as e:
            # Si hay cualquier error al validar (desencriptación, red, etc)
            logger.error(f"✗ Error validando API Key en login para usuario {user.id_usuario}: {e}")
            gemini_key_status = "error"
    
    # 10. Crear token JWT con datos del usuario
    access_token = create_access_token(
        data={
            "user_id": user.id_usuario,
            "username": user.nombre_usuario,
            "rol": user.rol,
            "clinica_id": user.clinica_id
        }
    )
    
    # 11. Retornar token y información completa del usuario (incluye estado de API Key)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id_usuario": user.id_usuario,
            "nombre_usuario": user.nombre_usuario,
            "email": user.email,
            "rol": user.rol,
            "clinica_id": user.clinica_id,
            # NUEVO: Información sobre API Key de Gemini
            "has_gemini_key": has_gemini_key,
            "gemini_key_status": gemini_key_status
        }
    }


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
@limiter.limit("10/minute")  # Rate limit: 10 password changes per minute per IP
async def change_password(
    password_data: ChangePasswordRequest,
    request: Request,
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
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta"
        )
    
    # 2. Verificar que la nueva contraseña sea diferente
    if password_data.current_password == password_data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La nueva contraseña debe ser diferente a la actual"
        )
    
    # 3. Actualizar la contraseña (usando Argon2)
    current_user.password_hash = hash_password(password_data.new_password)
    db.commit()
    
    return ChangePasswordResponse(
        message="Contraseña actualizada exitosamente",
        success=True
    )
