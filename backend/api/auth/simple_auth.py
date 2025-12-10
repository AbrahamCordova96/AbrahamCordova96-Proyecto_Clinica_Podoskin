"""
Autenticación simple para LangGraph (modo desarrollo)
====================================================

Implementa un Auth minimal basado en langgraph_sdk.Auth.
En DEBUG permite acceso libre; en producción usa tokens fijos de prueba.
"""

import os
from typing import Any, Dict
from langgraph_sdk import Auth

# Configuración básica
DEBUG = os.getenv("DEBUG", "True").lower() == "true"

# Instancia principal usada por langgraph.json
auth = Auth()


@auth.authenticate
async def authenticate(authorization: str | None = None) -> Dict[str, Any]:
    """Autenticación mínima para desarrollo y pruebas."""

    if DEBUG:
        return {
            "identity": "dev_user",
            "permissions": ["*"],
            "role": "Admin",
            "debug": True,
        }

    if not authorization or not authorization.startswith("Bearer "):
        raise Auth.exceptions.HTTPException(
            status_code=401, detail="Token Bearer requerido"
        )

    token = authorization.removeprefix("Bearer ").strip()

    if token == "test-admin-token":
        return {"identity": "admin", "permissions": ["*"], "role": "Admin"}
    if token == "test-podologo-token":
        return {
            "identity": "podologo",
            "permissions": ["clinical"],
            "role": "Podologo",
        }

    raise Auth.exceptions.HTTPException(status_code=401, detail="Token inválido")