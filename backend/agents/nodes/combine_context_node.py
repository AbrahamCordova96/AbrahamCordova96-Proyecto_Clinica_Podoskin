"""
Nodo de Combinación de Contexto (Opcional)
==========================================

Combina resultados de múltiples fuentes:
- Resultados SQL
- Contexto vectorial (si habilitado)
- Metadata adicional

NOTA: Este nodo es opcional. El flujo principal actual usa 
directamente los resultados SQL sin combinación.
"""

import logging
from typing import Optional, List, Dict, Any

from backend.agents.state import AgentState, ExecutionResult, add_log_entry

logger = logging.getLogger(__name__)


class CombineContextNode:
    """
    Nodo para combinar múltiples fuentes de contexto.
    
    Actualmente es un pass-through, pero está preparado para
    futuras mejoras con múltiples fuentes de datos.
    """
    
    def __init__(self):
        self.name = "combine_context"
        self.enabled = False  # Deshabilitado - usar flujo directo
    
    def __call__(self, state: AgentState) -> AgentState:
        """Combina contextos si está habilitado."""
        if not self.enabled:
            add_log_entry(state, "combine_context", "Nodo deshabilitado (pass-through)")
            state["node_path"] = state.get("node_path", []) + ["combine_context"]
            return state
        
        sql_result = state.get("execution_result")
        entities = state.get("entities_extracted") or {}
        vector_docs: List[str] = entities.get("_vector_docs", [])
        
        return self.run(state, sql_result, vector_docs)
    
    def run(self, state: AgentState, sql_result: Optional[ExecutionResult], vector_context: Optional[List[str]]) -> AgentState:
        """
        Combina resultados SQL con contexto vectorial.
        
        Args:
            state: Estado actual
            sql_result: Resultado de la ejecución SQL
            vector_context: Documentos del vector store
            
        Returns:
            Estado con contexto combinado
        """
        add_log_entry(state, "combine_context", "Combinando contextos")
        
        vector_docs_list: List[str] = vector_context or []
        sql_data_list: List[Dict[str, Any]] = sql_result.data if sql_result else []
        sql_count: int = sql_result.row_count if sql_result else 0
        has_sql: bool = sql_result is not None and sql_result.success
        has_vector: bool = len(vector_docs_list) > 0
        
        combined: Dict[str, Any] = {
            "sql_data": sql_data_list,
            "sql_count": sql_count,
            "vector_docs": vector_docs_list,
            "has_sql": has_sql,
            "has_vector": has_vector,
        }
        
        # Usar .get() y setdefault para evitar KeyError en TypedDict
        entities = state.get("entities_extracted") or {}
        entities["_combined_context"] = combined
        state["entities_extracted"] = entities
        
        vector_count = len(vector_docs_list)
        add_log_entry(
            state, "combine_context",
            f"Contexto combinado: {sql_count} SQL rows, {vector_count} vector docs"
        )
        
        state["node_path"] = state.get("node_path", []) + ["combine_context"]
        return state
