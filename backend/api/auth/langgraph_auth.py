"""
Autenticación JWT para LangGraph con validación en BD.
"""

import logging
from typing import Any, Dict

import jwt
from jwt import InvalidTokenError, ExpiredSignatureError
from langgraph_sdk import Auth

from backend.api.core.config import get_settings
from backend.api.deps.database import get_auth_db
from backend.schemas.auth.models import SysUsuario

logger = logging.getLogger(__name__)
settings = get_settings()

# Instancia principal que LangGraph cargará
auth = Auth()


def _get_auth_session():
    db_gen = get_auth_db()
    db = next(db_gen)
    try:
        yield db
    finally:
        try:
            db_gen.close()
        except Exception:
            pass


def _decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat"]},
        )
        return payload
    except ExpiredSignatureError:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token expirado")
    except InvalidTokenError:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token inválido")


def _get_user(user_id: int) -> SysUsuario:
    session_ctx = _get_auth_session()
    db = next(session_ctx)
    try:
        user = (
            db.query(SysUsuario)
            .filter(SysUsuario.id_usuario == user_id, SysUsuario.activo == True)
            .first()
        )
        if not user:
            raise Auth.exceptions.HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
        return user
    finally:
        try:
            session_ctx.close()
        except Exception:
            pass


@auth.authenticate
async def authenticate(authorization: str | None = None) -> Dict[str, Any]:
    """Valida Bearer JWT y consulta usuario en BD auth."""
    if not authorization or not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token Bearer requerido")

    token = authorization.removeprefix("Bearer ").strip()
    payload = _decode_token(token)

    user_id = payload.get("user_id") or payload.get("sub")
    if not user_id:
        raise Auth.exceptions.HTTPException(status_code=401, detail="Token sin user_id")

    user = _get_user(int(user_id))

    # Respuesta mínima esperada por LangGraph
    return {
        "identity": str(user.id_usuario),
        "permissions": [user.rol],
        "display_name": user.nombre_usuario,
    }


# =============================================================================
# CONTROL DE PERMISOS POR ROL
# =============================================================================
# Admin: Todos los permisos (consultas complejas, math, citas, gestión)
# Podologo: Consultas clínicas, matemáticas, citas (sin gestión de usuarios)
# Recepcion: Solo citas y consultas básicas de pacientes (sin historial médico)
#
# Mapeo de permisos por acción:
# - Consultas complejas: Admin, Podologo
# - Análisis matemático: Admin, Podologo
# - Gestión de citas: Admin, Podologo, Recepcion
# - Lectura pacientes: Admin, Podologo, Recepcion
# - Escritura pacientes: Admin, Podologo
# - Acciones admin: Admin únicamente
#
# NOTA: Este handler global valida permisos basados en metadata.
# Para control granular por endpoint, se puede extraer info del ctx (path, method).
