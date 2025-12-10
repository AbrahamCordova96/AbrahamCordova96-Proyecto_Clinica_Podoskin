"""
Nodo de Verificación de Permisos
================================

Verifica que el usuario tenga permisos para la operación solicitada
basándose en su rol (Admin, Podologo, Recepcion).

Implementa RBAC según la matriz de permisos del proyecto.
"""

import logging
from typing import Dict, Set, List

from backend.agents.state import (
    AgentState,
    IntentType,
    ErrorType,
    add_log_entry,
    format_friendly_error,
)

logger = logging.getLogger(__name__)


# =============================================================================
# MATRIZ DE PERMISOS POR ROL
# =============================================================================

# Permisos de lectura por rol y tabla
READ_PERMISSIONS: Dict[str, Set[str]] = {
    "Admin": {
        # Todas las tablas
        "auth.clinicas", "auth.sys_usuarios", "auth.audit_logs",
        "clinic.pacientes", "clinic.tratamientos", "clinic.evoluciones", "clinic.evidencias",
        "ops.podologos", "ops.citas", "ops.catalogo_servicios", "ops.solicitudes_prospectos",
        "finance.pagos", "finance.transacciones", "finance.gastos",
    },
    "Podologo": {
        # Todo clínico + agenda + auditoría limitada
        "clinic.pacientes", "clinic.tratamientos", "clinic.evoluciones", "clinic.evidencias",
        "ops.podologos", "ops.citas", "ops.catalogo_servicios", "ops.solicitudes_prospectos",
        "auth.audit_logs",  # Solo lectura
    },
    "Recepcion": {
        # Solo agenda y contacto (NO historial médico detallado)
        "clinic.pacientes",  # Solo datos de contacto, no historial
        "ops.citas", "ops.catalogo_servicios", "ops.solicitudes_prospectos",
        "ops.podologos",
    },
}

# Permisos de escritura (mutaciones) por rol
WRITE_PERMISSIONS: Dict[str, Set[str]] = {
    "Admin": {
        # Todas las tablas
        "auth.clinicas", "auth.sys_usuarios",
        "clinic.pacientes", "clinic.tratamientos", "clinic.evoluciones", "clinic.evidencias",
        "ops.podologos", "ops.citas", "ops.catalogo_servicios", "ops.solicitudes_prospectos",
        "finance.pagos", "finance.transacciones", "finance.gastos",
    },
    "Podologo": {
        # Datos clínicos + agenda
        "clinic.pacientes", "clinic.tratamientos", "clinic.evoluciones", "clinic.evidencias",
        "ops.citas",
    },
    "Recepcion": {
        # Solo agenda y prospectos
        "ops.citas", "ops.solicitudes_prospectos",
        "clinic.pacientes",  # Solo crear/actualizar datos de contacto
    },
}

# Campos restringidos para Recepción en pacientes
# (no pueden ver historial médico completo)
RESTRICTED_PATIENT_FIELDS = {
    "Recepcion": [
        "antecedentes_patologicos",
        "antecedentes_familiares", 
        "alergias",
        "medicamentos",
        "observaciones_medicas",
    ]
}

# Operaciones sensibles que requieren confirmación adicional
SENSITIVE_OPERATIONS = {
    IntentType.MUTATION_DELETE,  # Borrados siempre sensibles
}


# =============================================================================
# FUNCIÓN DE VERIFICACIÓN DE PERMISOS
# =============================================================================

def check_permissions(state: AgentState) -> AgentState:
    """
    Nodo que verifica permisos del usuario para la operación.
    
    Args:
        state: Estado actual con intent y entidades
        
    Returns:
        Estado actualizado, posiblemente con error de permisos
    """
    add_log_entry(state, "check_permissions", "Verificando permisos de usuario")
    
    user_role = state.get("user_role", "Recepcion")
    intent = state.get("intent", IntentType.QUERY_READ)
    entities = state.get("entities_extracted", {})
    tables = entities.get("_tables", [])
    
    # 1. Verificar que el rol sea válido
    if user_role not in READ_PERMISSIONS:
        state["error_type"] = ErrorType.PERMISSION_DENIED
        state["error_internal_message"] = f"Rol desconocido: {user_role}"
        state["error_user_message"] = "Tu cuenta no tiene un rol válido configurado."
        add_log_entry(state, "check_permissions", f"Rol inválido: {user_role}", level="warning")
        state["node_path"] = state.get("node_path", []) + ["check_permissions"]
        return state
    
    # 2. Determinar si es lectura o escritura
    is_write_operation = intent in [
        IntentType.MUTATION_CREATE,
        IntentType.MUTATION_UPDATE,
        IntentType.MUTATION_DELETE,
    ]
    
    # 3. Verificar permisos para cada tabla involucrada
    permissions_set = WRITE_PERMISSIONS if is_write_operation else READ_PERMISSIONS
    allowed_tables = permissions_set.get(user_role, set())
    
    denied_tables: List[str] = []
    for table in tables:
        if table and table not in allowed_tables:
            denied_tables.append(table)
    
    if denied_tables:
        state["error_type"] = ErrorType.PERMISSION_DENIED
        state["error_internal_message"] = f"Acceso denegado a: {denied_tables}"
        
        # Mensaje amigable según el caso
        friendly = format_friendly_error(ErrorType.PERMISSION_DENIED)
        if is_write_operation:
            state["error_user_message"] = (
                f"{friendly['title']}\n\n"
                "No tienes permisos para modificar esta información. "
                "Solo puedes consultar datos."
            )
        else:
            state["error_user_message"] = (
                f"{friendly['title']}\n\n"
                "No tienes acceso a ver esta información con tu rol actual."
            )
        
        state["error_suggestions"] = [
            "Contacta al administrador si necesitas acceso.",
            "Verifica que estás consultando información dentro de tu área."
        ]
        
        add_log_entry(
            state, "check_permissions", 
            f"Permiso denegado para {user_role} en {denied_tables}",
            level="warning"
        )
        state["node_path"] = state.get("node_path", []) + ["check_permissions"]
        return state
    
    # 4. Verificar restricciones especiales para Recepción en pacientes
    if user_role == "Recepcion" and "clinic.pacientes" in tables:
        # Marcar que hay campos restringidos
        entities = state.get("entities_extracted") or {}
        entities["_restricted_fields"] = RESTRICTED_PATIENT_FIELDS.get(user_role, [])
        state["entities_extracted"] = entities
        add_log_entry(
            state, "check_permissions",
            "Aplicando restricciones de campos para Recepcion"
        )
    
    # 5. Marcar operaciones sensibles que requieren confirmación
    if intent in SENSITIVE_OPERATIONS:
        entities = state.get("entities_extracted") or {}
        entities["_requires_confirmation"] = True
        state["entities_extracted"] = entities
        add_log_entry(state, "check_permissions", "Operación marcada como sensible")
    
    # 6. Todo OK - permisos concedidos
    add_log_entry(
        state, "check_permissions",
        f"Permisos OK para {user_role}: {intent.value} en {tables}"
    )
    
    state["node_path"] = state.get("node_path", []) + ["check_permissions"]
    return state


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def get_allowed_tables_for_role(role: str, write: bool = False) -> Set[str]:
    """
    Obtiene las tablas permitidas para un rol.
    
    Args:
        role: Nombre del rol
        write: Si True, devuelve permisos de escritura
        
    Returns:
        Set de nombres de tablas permitidas
    """
    permissions = WRITE_PERMISSIONS if write else READ_PERMISSIONS
    return permissions.get(role, set())


def can_access_table(role: str, table: str, write: bool = False) -> bool:
    """
    Verifica si un rol puede acceder a una tabla.
    
    Args:
        role: Nombre del rol
        table: Nombre de la tabla (con schema)
        write: Si True, verifica permisos de escritura
        
    Returns:
        True si tiene acceso
    """
    allowed = get_allowed_tables_for_role(role, write)
    return table in allowed


# =============================================================================
# NODE WRAPPER PARA LANGGRAPH
# =============================================================================

class CheckPermissionsNode:
    """Wrapper de nodo para compatibilidad con LangGraph."""
    
    def __init__(self):
        self.name = "check_permissions"
    
    def __call__(self, state: AgentState) -> AgentState:
        return check_permissions(state)
