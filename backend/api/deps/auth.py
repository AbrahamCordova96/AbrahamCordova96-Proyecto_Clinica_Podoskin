# =============================================================================
# backend/api/deps/auth.py
# Dependencias de autenticación
# =============================================================================
# Este archivo proporciona funciones para obtener el usuario actual
# a partir del token JWT enviado en el header Authorization.
#
# FLUJO DE AUTENTICACIÓN:
# 1. Usuario hace login → recibe token JWT
# 2. Usuario hace request con header "Authorization: Bearer {token}"
# 3. Este módulo extrae el token, lo valida, y obtiene el usuario
# 4. El endpoint recibe el objeto usuario listo para usar
#
# ANALOGÍA: Es el "guardia de seguridad" que verifica tu gafete
# en la entrada de cada oficina (endpoint).
# =============================================================================

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.api.core.security import verify_token, TokenData
from backend.api.deps.database import get_auth_db
from backend.schemas.auth.models import SysUsuario


# =============================================================================
# OAUTH2 SCHEME
# =============================================================================
# OAuth2PasswordBearer define CÓMO se envía el token.
# - tokenUrl: endpoint donde se obtiene el token (login)
# - El token se envía en header: "Authorization: Bearer {token}"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =============================================================================
# DEPENDENCIA: get_current_user
# =============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_auth_db)
) -> SysUsuario:
    """
    Obtiene el usuario actual a partir del token JWT.
    
    Esta es LA dependencia principal de autenticación.
    Cualquier endpoint que requiera autenticación debe incluirla.
    
    Args:
        token: Extraído automáticamente del header Authorization
        db: Sesión de BD para buscar al usuario
    
    Returns:
        Objeto SysUsuario completo con todos sus datos
    
    Raises:
        HTTPException 401: Si el token es inválido o expirado
        HTTPException 401: Si el usuario no existe en la BD
    
    Uso en endpoints:
        @router.get("/mi-perfil")
        def get_perfil(current_user: SysUsuario = Depends(get_current_user)):
            return {"usuario": current_user.nombre_usuario, "rol": current_user.rol}
    """
    # Excepción que lanzamos si hay problemas con las credenciales
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 1. Verificar y decodificar el token
    token_data: Optional[TokenData] = verify_token(token)
    if token_data is None:
        raise credentials_exception
    
    # 2. Buscar el usuario en la base de datos
    # Usamos el user_id del token para encontrar al usuario
    user = db.query(SysUsuario).filter(
        SysUsuario.id_usuario == token_data.user_id
    ).first()
    
    if user is None:
        raise credentials_exception
    
    return user


# =============================================================================
# DEPENDENCIA: get_current_active_user
# =============================================================================

async def get_current_active_user(
    current_user: SysUsuario = Depends(get_current_user)
) -> SysUsuario:
    """
    Verifica que el usuario actual esté activo.
    
    Además de validar el token, verifica que la cuenta no esté desactivada.
    Si un admin desactiva un usuario, sus tokens existentes dejan de funcionar.
    
    Returns:
        Usuario si está activo
    
    Raises:
        HTTPException 403: Si el usuario está desactivado
    
    Uso:
        @router.post("/alguna-accion")
        def hacer_algo(user: SysUsuario = Depends(get_current_active_user)):
            # Solo usuarios activos llegan aquí
            ...
    """
    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado. Contacte al administrador."
        )
    
    return current_user
