# =============================================================================
# backend/api/deps/permissions.py
# Sistema de control de acceso basado en roles (RBAC)
# =============================================================================
# Este archivo implementa el sistema de permisos por rol.
# Define QUÉ puede hacer cada tipo de usuario (Admin, Podologo, Recepcion).
#
# ROLES Y SUS CAPACIDADES:
# - Admin: TODO (incluyendo eliminar permanentemente, crear usuarios)
# - Podologo: Casi todo, excepto eliminar permanente y gestionar usuarios
# - Recepcion: Solo agenda, prospectos y datos básicos de pacientes
#
# ANALOGÍA: Es como el sistema de llaves de un hotel.
# - El gerente (Admin) tiene llave maestra
# - El jefe de piso (Podologo) puede abrir la mayoría de puertas
# - El recepcionista (Recepcion) solo puede abrir algunas puertas
# =============================================================================

from typing import List, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status

from backend.schemas.auth.models import SysUsuario
from backend.api.deps.auth import get_current_active_user


# =============================================================================
# CONSTANTES DE ROLES
# =============================================================================
# Definimos los roles como constantes para evitar errores de tipeo

ROLE_ADMIN = "Admin"
ROLE_PODOLOGO = "Podologo"
ROLE_RECEPCION = "Recepcion"

# Lista de todos los roles válidos
ALL_ROLES = [ROLE_ADMIN, ROLE_PODOLOGO, ROLE_RECEPCION]

# Roles que pueden ver/editar datos clínicos
CLINICAL_ROLES = [ROLE_ADMIN, ROLE_PODOLOGO]


# =============================================================================
# CAMPOS BÁSICOS (lo que Recepción puede ver/editar de pacientes)
# =============================================================================
# Recepción NO puede ver historial médico, solo datos de contacto

PACIENTE_BASIC_FIELDS = [
    "id_paciente",
    "nombres",
    "apellidos",
    "fecha_nacimiento",
    "sexo",
    "estado_civil",
    "ocupacion",
    "domicilio",
    "telefono",
    "email",
    "como_supo_de_nosotros",
    "fecha_registro",
]


# =============================================================================
# DEPENDENCIA: require_role
# =============================================================================

def require_role(allowed_roles: List[str]) -> Callable:
    """
    Crea una dependencia que valida el rol del usuario.
    
    Esta función retorna otra función (una dependencia de FastAPI)
    que verifica si el usuario actual tiene uno de los roles permitidos.
    
    Args:
        allowed_roles: Lista de roles que pueden acceder al endpoint.
                      Ej: ["Admin", "Podologo"]
    
    Returns:
        Función dependencia que valida el rol y retorna el usuario.
    
    Raises:
        HTTPException 403: Si el usuario no tiene un rol permitido.
    
    Uso en endpoints:
        # Solo Admin puede crear usuarios
        @router.post("/usuarios")
        async def create_usuario(
            user: SysUsuario = Depends(require_role(["Admin"]))
        ):
            ...
        
        # Admin y Podologo pueden ver tratamientos
        @router.get("/tratamientos")
        async def get_tratamientos(
            user: SysUsuario = Depends(require_role(["Admin", "Podologo"]))
        ):
            ...
        
        # Todos pueden ver citas
        @router.get("/citas")
        async def get_citas(
            user: SysUsuario = Depends(require_role(["Admin", "Podologo", "Recepcion"]))
        ):
            ...
    """
    
    async def role_checker(
        current_user: SysUsuario = Depends(get_current_active_user)
    ) -> SysUsuario:
        """
        Verifica que el usuario tenga uno de los roles permitidos.
        """
        if current_user.rol not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de estos roles: {', '.join(allowed_roles)}. "
                       f"Tu rol actual es: {current_user.rol}"
            )
        return current_user
    
    return role_checker


# =============================================================================
# HELPERS: Funciones de utilidad para permisos
# =============================================================================

def is_admin(user: SysUsuario) -> bool:
    """Verifica si el usuario es administrador."""
    return user.rol == ROLE_ADMIN


def is_clinical_staff(user: SysUsuario) -> bool:
    """Verifica si el usuario puede ver datos clínicos (Admin o Podologo)."""
    return user.rol in CLINICAL_ROLES


def is_recepcion(user: SysUsuario) -> bool:
    """Verifica si el usuario es recepción."""
    return user.rol == ROLE_RECEPCION


def can_purge_data(user: SysUsuario) -> bool:
    """Verifica si el usuario puede eliminar datos permanentemente."""
    # Solo Admin puede hacer hard delete
    return user.rol == ROLE_ADMIN


def can_manage_users(user: SysUsuario) -> bool:
    """Verifica si el usuario puede crear/eliminar usuarios."""
    return user.rol == ROLE_ADMIN


def can_export_data(user: SysUsuario) -> bool:
    """Verifica si el usuario puede exportar la base de datos."""
    return user.rol == ROLE_ADMIN


def filter_paciente_for_recepcion(paciente_dict: dict) -> dict:
    """
    Filtra los campos de un paciente para mostrar solo datos básicos.
    
    Recepción no debe ver historial médico, solo datos de contacto.
    Esta función elimina los campos clínicos del diccionario.
    
    Args:
        paciente_dict: Diccionario con todos los campos del paciente
    
    Returns:
        Diccionario solo con campos básicos
    """
    return {
        key: value 
        for key, value in paciente_dict.items() 
        if key in PACIENTE_BASIC_FIELDS
    }
