# =============================================================================
# backend/api/core/security.py
# Funciones de seguridad: JWT encode/decode
# =============================================================================
# Este archivo maneja la creación y verificación de tokens JWT.
#
# ¿QUÉ ES JWT?
# JWT (JSON Web Token) es como un "pase de acceso" temporal.
# Cuando el usuario hace login, le damos un token firmado digitalmente.
# En cada request posterior, el usuario envía este token para demostrar
# que ya se autenticó, sin necesidad de enviar usuario/password cada vez.
#
# ESTRUCTURA DEL TOKEN:
# header.payload.signature
# - header: tipo de token y algoritmo
# - payload: datos (user_id, rol, expiración)
# - signature: firma para verificar que nadie lo modificó
# =============================================================================

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from pydantic import BaseModel

from backend.api.core.config import get_settings


# Obtenemos la configuración una sola vez
settings = get_settings()


class TokenData(BaseModel):
    """
    Datos que extraemos de un token JWT.
    
    Estos son los campos que guardamos dentro del token
    y que recuperamos cuando lo decodificamos.
    """
    user_id: int
    username: str
    rol: str
    clinica_id: Optional[int] = None


class Token(BaseModel):
    """
    Respuesta que devolvemos al hacer login.
    
    Contiene el token de acceso y el tipo (siempre "bearer").
    El frontend guarda esto y lo envía en cada request.
    """
    access_token: str
    token_type: str = "bearer"


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Crea un token JWT firmado.
    
    Args:
        data: Diccionario con datos a incluir en el token (user_id, rol, etc.)
        expires_delta: Tiempo de vida del token. Si no se especifica,
                      usa el valor de configuración.
    
    Returns:
        String con el token JWT codificado.
    
    Ejemplo:
        token = create_access_token(
            data={"user_id": 1, "username": "admin", "rol": "Admin"}
        )
        # Retorna algo como: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    
    NOTA TÉCNICA:
    El token incluye automáticamente un campo "exp" (expiration) que indica
    cuándo expira. Después de esa fecha, el token es inválido.
    """
    # Copiamos los datos para no modificar el original
    to_encode = data.copy()
    
    # Calculamos la fecha de expiración
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Agregamos la expiración al payload
    to_encode.update({"exp": expire})
    
    # Codificamos y firmamos el token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verifica y decodifica un token JWT.
    
    Args:
        token: String con el token JWT a verificar.
    
    Returns:
        TokenData si el token es válido, None si no lo es.
    
    Posibles razones de fallo:
        - Token expirado (pasó la fecha de "exp")
        - Token alterado (la firma no coincide)
        - Token malformado (no tiene la estructura correcta)
    
    ANALOGÍA: Es como el escáner de seguridad del edificio.
    Verifica que tu gafete sea auténtico y no esté vencido.
    """
    try:
        # Decodificamos el token usando la misma clave secreta
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extraemos los datos del payload de forma segura
        user_id = payload.get("user_id")
        username = payload.get("username")
        rol = payload.get("rol")
        clinica_id = payload.get("clinica_id")
        
        # Verificamos que los campos esenciales existan y tengan el tipo correcto
        if not isinstance(user_id, int) or not isinstance(username, str) or not isinstance(rol, str):
            return None
        
        return TokenData(
            user_id=user_id,
            username=username,
            rol=rol,
            clinica_id=clinica_id
        )
        
    except JWTError:
        # Cualquier error de JWT (expirado, inválido, etc.)
        return None
