# =============================================================================
# backend/api/deps/__init__.py
# Dependencias compartidas de la API
# =============================================================================

from backend.api.deps.database import get_auth_db, get_core_db, get_ops_db
from backend.api.deps.auth import get_current_user, get_current_active_user
from backend.api.deps.permissions import require_role

__all__ = [
    "get_auth_db",
    "get_core_db", 
    "get_ops_db",
    "get_current_user",
    "get_current_active_user",
    "require_role",
]
