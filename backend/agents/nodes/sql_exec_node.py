"""
Nodo de Ejecución SQL
=====================

Ejecuta la consulta SQL generada de forma segura.
Maneja errores, reintentos y búsqueda difusa para sugerencias.
"""

import logging

from backend.api.core.config import get_settings
from backend.agents.state import (
    AgentState,
    ErrorType,
    add_log_entry,
)
from backend.tools.sql_executor import execute_safe_query
from backend.tools.fuzzy_search import (
    fuzzy_search_patient,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# FUNCIÓN DE EJECUCIÓN SQL
# =============================================================================

def execute_sql(state: AgentState) -> AgentState:
    """
    Nodo que ejecuta la consulta SQL generada.
    
    Maneja:
    - Ejecución segura de queries
    - Reintentos en caso de error
    - Búsqueda difusa para sugerencias cuando no hay resultados
    
    Args:
        state: Estado con sql_query generada
        
    Returns:
        Estado actualizado con execution_result
    """
    add_log_entry(state, "execute_sql", "Ejecutando consulta SQL")
    
    # Verificar que hay una query para ejecutar
    sql_query = state.get("sql_query")
    if not sql_query:
        add_log_entry(state, "execute_sql", "No hay SQL para ejecutar", level="warning")
        state["node_path"] = state.get("node_path", []) + ["execute_sql"]
        return state
    
    # Verificar que no haya errores previos
    if state.get("error_type", ErrorType.NONE) != ErrorType.NONE:
        add_log_entry(state, "execute_sql", "Saltando ejecución por error previo")
        state["node_path"] = state.get("node_path", []) + ["execute_sql"]
        return state
    
    user_role = state.get("user_role", "Recepcion")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", settings.AGENT_MAX_RETRIES)
    
    # Ejecutar query
    result = execute_safe_query(
        sql_query=sql_query,
        user_role=user_role,
        max_results=settings.AGENT_MAX_RESULTS,
        timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
    )
    
    state["execution_result"] = result
    
    if result.success:
        add_log_entry(
            state, "execute_sql",
            f"Ejecución exitosa: {result.row_count} filas en {result.execution_time_ms:.2f}ms"
        )
        
        # Si no hay resultados, intentar sugerir alternativas
        if result.row_count == 0:
            state = _handle_no_results(state)
    else:
        add_log_entry(
            state, "execute_sql",
            f"Error en ejecución: {result.error_message}",
            level="error"
        )
        
        # Intentar reintento si es posible
        if retry_count < max_retries:
            state["retry_count"] = retry_count + 1
            add_log_entry(state, "execute_sql", f"Reintento {retry_count + 1}/{max_retries}")
            # El grafo debe manejar el reintento volviendo a generate_sql
            state["error_type"] = ErrorType.SQL_ERROR
            state["error_internal_message"] = result.error_message or "Error SQL desconocido"
        else:
            # Sin más reintentos
            state["error_type"] = ErrorType.SQL_ERROR
            state["error_user_message"] = (
                "⚠️ No pude completar la búsqueda.\n\n"
                "Intenta reformular tu pregunta de otra manera."
            )
    
    state["node_path"] = state.get("node_path", []) + ["execute_sql"]
    return state


# =============================================================================
# MANEJO DE CASOS ESPECIALES
# =============================================================================

def _handle_no_results(state: AgentState) -> AgentState:
    """
    Maneja el caso de consulta exitosa pero sin resultados.
    
    Intenta buscar sugerencias usando búsqueda difusa.
    """
    entities = state.get("entities_extracted", {})
    suggestions = []
    
    # Buscar sugerencias basadas en las entidades
    if "nombre_paciente" in entities:
        nombre = entities["nombre_paciente"]
        matches = fuzzy_search_patient(nombre, threshold=0.3, limit=3)
        if matches:
            suggestions = [m["nombre_completo"] for m in matches]
    
    if not suggestions:
        # Buscar en otros campos extraídos
        for key, value in entities.items():
            if key.startswith("_"):
                continue
            if isinstance(value, str) and len(value) > 2:
                # Intentar búsqueda genérica
                patient_matches = fuzzy_search_patient(value, threshold=0.3, limit=3)
                if patient_matches:
                    suggestions = [m["nombre_completo"] for m in patient_matches]
                    break
    
    if suggestions:
        state["fuzzy_suggestions"] = suggestions
        state["error_type"] = ErrorType.NO_RESULTS
        state["error_user_message"] = (
            "📭 No encontré resultados exactos.\n\n"
            f"¿Quizás quisiste decir: {', '.join(suggestions[:3])}?"
        )
        add_log_entry(state, "execute_sql", f"Sugerencias encontradas: {suggestions}")
    else:
        state["error_type"] = ErrorType.NO_RESULTS
        state["error_user_message"] = (
            "📭 No encontré información que coincida.\n\n"
            "Verifica que los datos estén escritos correctamente."
        )
        add_log_entry(state, "execute_sql", "Sin resultados ni sugerencias")
    
    return state


# =============================================================================
# NODE WRAPPER PARA LANGGRAPH (compatibilidad)
# =============================================================================

from typing import Any, Optional

class SQLExecNode:
    """Wrapper de nodo para compatibilidad con LangGraph."""
    
    def __init__(self, db_config: Optional[Any] = None):
        self.name = "execute_sql"
        self.db_config = db_config  # Legacy, no usado
    
    def __call__(self, state: AgentState) -> AgentState:
        return execute_sql(state)
    
    def run(self, state: AgentState, sql: str, params: Optional[dict[str, Any]] = None):
        """Método legacy para compatibilidad."""
        from backend.agents.state import SQLQuery, DatabaseTarget
        state["sql_query"] = SQLQuery(
            query=sql,
            params=params or {},
            target_db=DatabaseTarget.CORE,
        )
        return execute_sql(state)
