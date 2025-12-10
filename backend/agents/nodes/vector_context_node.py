"""
Nodo de Contexto Vectorial (Opcional)
=====================================

Busca contexto adicional en el vector store usando embeddings.
Útil para búsquedas semánticas cuando la SQL no es suficiente.

NOTA: Este nodo es opcional y se puede habilitar en futuras versiones.
Por ahora, el flujo principal usa SQL directo.
"""

import logging

from backend.agents.state import AgentState, add_log_entry

logger = logging.getLogger(__name__)


class VectorContextNode:
    """
    Nodo para búsqueda de contexto en vector store.
    
    Actualmente es un placeholder para futuras mejoras con RAG.
    """
    
    def __init__(self, chroma_path: str = "data/chroma_db"):
        self.name = "vector_context"
        self.chroma_path = chroma_path
        self.enabled = False  # Deshabilitado por defecto
    
    def __call__(self, state: AgentState) -> AgentState:
        """Ejecuta búsqueda vectorial si está habilitada."""
        if not self.enabled:
            add_log_entry(state, "vector_context", "Nodo deshabilitado (RAG no activo)")
            state["node_path"] = state.get("node_path", []) + ["vector_context"]
            return state
        
        return self.run(state, state.get("user_query", ""))
    
    def run(self, state: AgentState, query: str) -> AgentState:
        """
        Busca documentos relevantes en el vector store.
        
        Args:
            state: Estado actual
            query: Query del usuario para búsqueda semántica
            
        Returns:
            Estado con vector_docs poblados
        """
        add_log_entry(state, "vector_context", f"Buscando contexto para: {query[:50]}...")
        
        try:
            # Placeholder para futura implementación con ChromaDB
            # from backend.tools.vector_store import search_similar_docs
            # docs = search_similar_docs(query, self.chroma_path)
            
            # Asegurar que entities_extracted existe antes de acceder
            if "entities_extracted" not in state:
                state["entities_extracted"] = {}
            state["entities_extracted"]["_vector_docs"] = []
            add_log_entry(state, "vector_context", "Búsqueda vectorial completada (placeholder)")
            
        except Exception as e:
            logger.error(f"Error en búsqueda vectorial: {e}")
            add_log_entry(state, "vector_context", f"Error: {str(e)}", level="error")
        
        state["node_path"] = state.get("node_path", []) + ["vector_context"]
        return state
