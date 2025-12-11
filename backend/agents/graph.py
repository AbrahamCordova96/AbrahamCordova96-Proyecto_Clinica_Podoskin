"""
Grafo LangGraph - Definición del flujo del agente
=================================================

Define el StateGraph con nodos y edges condicionales.
Usa LangGraph oficial según Decisión 1.

Flujo del grafo:
┌─────────────────┐
│ classify_intent │
└────────┬────────┘
         │
    ┌────▼────┐
    │ router  │ ← Decide siguiente nodo según intent
    └────┬────┘
         │
  ┌──────┼──────┬──────────┐
  ▼      ▼      ▼          ▼
greeting out_of check    generate
response scope  perms    sql
  │      │      │          │
  └──────┴──────┤          ▼
                │      execute_sql
                │          │
                └────┬─────┘
                     ▼
              generate_response
                     │
                     ▼
                   END
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END  # type: ignore

from backend.agents.state import (
    AgentState,
    IntentType,
    ErrorType,
    create_initial_state,
)
from backend.agents.nodes import (
    classify_intent,
    check_permissions,
    generate_sql,
    execute_sql,
    generate_response,
)

logger = logging.getLogger(__name__)


# =============================================================================
# FUNCIONES DE ROUTING (EDGES CONDICIONALES)
# =============================================================================

def route_after_classification(state: AgentState) -> Literal[
    "greeting_response", 
    "out_of_scope_response",
    "clarification_response",
    "check_permissions"
]:
    """
    Decide el siguiente nodo basándose en la intención clasificada.
    
    Returns:
        Nombre del siguiente nodo
    """
    intent = state.get("intent", IntentType.CLARIFICATION)
    
    if intent == IntentType.GREETING:
        return "greeting_response"
    
    if intent == IntentType.OUT_OF_SCOPE:
        return "out_of_scope_response"
    
    if intent == IntentType.CLARIFICATION:
        return "clarification_response"
    
    # Para queries de lectura/agregación, continuar con el flujo
    return "check_permissions"


def route_after_permissions(state: AgentState) -> Literal["generate_sql", "error_response"]:
    """
    Decide si continuar con SQL o mostrar error de permisos.
    """
    error_type = state.get("error_type", ErrorType.NONE)
    
    if error_type == ErrorType.PERMISSION_DENIED:
        return "error_response"
    
    return "generate_sql"


def route_after_sql_generation(state: AgentState) -> Literal["execute_sql", "error_response"]:
    """
    Decide si ejecutar SQL o mostrar error.
    """
    error_type = state.get("error_type", ErrorType.NONE)
    sql_query = state.get("sql_query")
    
    if error_type != ErrorType.NONE or not sql_query:
        return "error_response"
    
    return "execute_sql"


def route_after_execution(state: AgentState) -> Literal["generate_response", "retry_sql"]:
    """
    Decide si formatear respuesta o reintentar.
    """
    error_type = state.get("error_type", ErrorType.NONE)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    
    # Si hay error SQL y quedan reintentos, volver a generar
    if error_type == ErrorType.SQL_ERROR and retry_count < max_retries:
        return "retry_sql"
    
    return "generate_response"


# =============================================================================
# NODOS ESPECIALES (para respuestas rápidas sin SQL)
# =============================================================================

def greeting_response_node(state: AgentState) -> AgentState:
    """Nodo para respuestas de saludo."""
    state["node_path"] = state.get("node_path", []) + ["greeting_response"]
    return generate_response(state)


def out_of_scope_response_node(state: AgentState) -> AgentState:
    """Nodo para consultas fuera de alcance."""
    state["node_path"] = state.get("node_path", []) + ["out_of_scope_response"]
    return generate_response(state)


def clarification_response_node(state: AgentState) -> AgentState:
    """Nodo para pedir clarificación."""
    state["node_path"] = state.get("node_path", []) + ["clarification_response"]
    return generate_response(state)


def error_response_node(state: AgentState) -> AgentState:
    """Nodo para mostrar errores."""
    state["node_path"] = state.get("node_path", []) + ["error_response"]
    return generate_response(state)


# =============================================================================
# CONSTRUCCIÓN DEL GRAFO
# =============================================================================

def build_agent_graph() -> StateGraph:  # type: ignore
    """
    Construye el grafo del agente usando LangGraph.
    
    NUEVO (Fase 2): Soporta dos modos:
    - Subgraph architecture (recomendado): Routing por origen a subgrafos especializados
    - Monolithic (legacy): Grafo único tradicional
    
    Returns:
        StateGraph compilado listo para invocar
    """
    from backend.api.core.config import get_settings
    settings = get_settings()
    
    # ✅ NUEVO - Fase 2: Usar arquitectura de subgrafos si está habilitada
    if settings.ENABLE_SUBGRAPH_ARCHITECTURE:
        logger.info("🔧 Construyendo grafo con arquitectura de subgrafos (Fase 2)")
        from backend.agents.root_graph import build_root_graph
        return build_root_graph()
    
    # Legacy: Grafo monolítico original
    logger.info("🔧 Construyendo grafo monolítico (legacy)")
    
    # Crear grafo con el tipo de estado
    workflow = StateGraph(AgentState)  # type: ignore
    
    # --- Agregar nodos ---
    workflow.add_node("classify_intent", classify_intent)  # type: ignore
    workflow.add_node("check_permissions", check_permissions)  # type: ignore
    workflow.add_node("generate_sql", generate_sql)  # type: ignore
    workflow.add_node("execute_sql", execute_sql)  # type: ignore
    workflow.add_node("generate_response", generate_response)  # type: ignore
    
    # Nodos de respuesta rápida
    workflow.add_node("greeting_response", greeting_response_node)  # type: ignore
    workflow.add_node("out_of_scope_response", out_of_scope_response_node)  # type: ignore
    workflow.add_node("clarification_response", clarification_response_node)  # type: ignore
    workflow.add_node("error_response", error_response_node)  # type: ignore
    
    # --- Definir punto de entrada ---
    workflow.set_entry_point("classify_intent")
    
    # --- Agregar edges condicionales ---
    
    # Después de clasificar, decidir camino
    workflow.add_conditional_edges(
        "classify_intent",
        route_after_classification,
        {
            "greeting_response": "greeting_response",
            "out_of_scope_response": "out_of_scope_response",
            "clarification_response": "clarification_response",
            "check_permissions": "check_permissions",
        }
    )
    
    # Después de verificar permisos
    workflow.add_conditional_edges(
        "check_permissions",
        route_after_permissions,
        {
            "generate_sql": "generate_sql",
            "error_response": "error_response",
        }
    )
    
    # Después de generar SQL
    workflow.add_conditional_edges(
        "generate_sql",
        route_after_sql_generation,
        {
            "execute_sql": "execute_sql",
            "error_response": "error_response",
        }
    )
    
    # Después de ejecutar SQL
    workflow.add_conditional_edges(
        "execute_sql",
        route_after_execution,
        {
            "generate_response": "generate_response",
            "retry_sql": "generate_sql",  # Reintento
        }
    )
    
    # --- Edges finales (a END) ---
    workflow.add_edge("greeting_response", END)
    workflow.add_edge("out_of_scope_response", END)
    workflow.add_edge("clarification_response", END)
    workflow.add_edge("error_response", END)
    workflow.add_edge("generate_response", END)
    
    return workflow


# =============================================================================
# COMPILACIÓN Y EJECUCIÓN
# =============================================================================

# Grafo compilado (singleton)
_compiled_graph = None


def get_compiled_graph():
    """
    Obtiene el grafo compilado (singleton) con checkpointer para memoria episódica.
    
    NUEVO (Fase 1 - Memoria Episódica):
    - Usa PostgresSaver para persistencia de estado
    - Permite conversaciones multi-turno con contexto
    
    Returns:
        Grafo compilado listo para invoke() con checkpointing
    """
    global _compiled_graph
    if _compiled_graph is None:
        from backend.agents.checkpoint_config import get_checkpointer
        
        workflow = build_agent_graph()
        
        # ✅ NUEVO: Compilar con checkpointer para memoria episódica
        try:
            checkpointer = get_checkpointer()
            _compiled_graph = workflow.compile(checkpointer=checkpointer)
            logger.info("✅ Grafo compilado con checkpointer PostgreSQL (memoria episódica activada)")
        except Exception as e:
            logger.error(f"⚠️ Error al compilar con checkpointer: {e}")
            logger.warning("⚠️ Compilando sin checkpointer (modo stateless)")
            _compiled_graph = workflow.compile()
            logger.info("⚠️ Grafo compilado SIN checkpointer (stateless)")
    
    return _compiled_graph


async def run_agent(
    user_query: str,
    user_id: int,
    user_role: str,
    session_id: str | None = None,
    thread_id: str | None = None,
    origin: str = "webapp",
) -> Dict[str, Any]:
    """
    Ejecuta el agente con una consulta del usuario.
    
    NUEVO (Fase 1 - Memoria Episódica):
    - Usa thread_id para mantener contexto entre turnos
    - Configura checkpointing para persistencia de estado
    
    Args:
        user_query: Consulta en lenguaje natural
        user_id: ID del usuario autenticado
        user_role: Rol del usuario (Admin, Podologo, Recepcion)
        session_id: ID de sesión opcional (legacy)
        thread_id: ID de hilo para checkpointing (NUEVO)
        origin: Origen de la conversación ('webapp', 'whatsapp_paciente', 'whatsapp_user')
        
    Returns:
        Dict con response_text, response_data, y metadata
    """
    import uuid
    from datetime import datetime
    from backend.agents.checkpoint_config import create_thread_id
    
    # Generar IDs si no se proporcionan
    session_id = session_id or str(uuid.uuid4())
    
    # ✅ NUEVO: Crear thread_id para checkpointing
    if not thread_id:
        thread_id = create_thread_id(
            user_id=user_id,
            origin=origin,
            conversation_uuid=session_id
        )
    
    # Crear estado inicial con thread_id
    initial_state = create_initial_state(
        user_query=user_query,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        thread_id=thread_id,
        origin=origin,
    )
    
    logger.info(
        f"Ejecutando agente para: '{user_query[:50]}...' "
        f"(user={user_id}, role={user_role}, thread={thread_id})"
    )
    
    try:
        # Obtener grafo y ejecutar
        graph = get_compiled_graph()
        
        # ✅ NUEVO: Configurar checkpointing con thread_id
        config = {
            "configurable": {
                "thread_id": thread_id,
            }
        }
        
        final_state = graph.invoke(initial_state, config=config)
        
        # Agregar timestamp de finalización
        final_state["completed_at"] = datetime.now(timezone.utc)
        
        logger.info(
            f"✅ Agente completado. Path: {final_state.get('node_path', [])} "
            f"(thread={thread_id})"
        )
        
        return {
            "success": True,
            "response_text": final_state.get("response_text", ""),
            "response_data": final_state.get("response_data", {}),
            "intent": final_state.get("intent", "").value if final_state.get("intent") else None,
            "error_type": final_state.get("error_type", "").value if final_state.get("error_type") else None,
            "node_path": final_state.get("node_path", []),
            "session_id": session_id,
            "thread_id": thread_id,  # ✅ NUEVO: Retornar thread_id para continuidad
        }
        
    except Exception as e:
        logger.exception(f"❌ Error ejecutando agente: {e}")
        return {
            "success": False,
            "response_text": "🔧 Ocurrió un error procesando tu consulta. Por favor intenta de nuevo.",
            "response_data": {},
            "error": str(e),
            "session_id": session_id,
            "thread_id": thread_id,
        }


# =============================================================================
# CLASE LEGACY (compatibilidad)
# =============================================================================

class Graph:
    """Wrapper de compatibilidad para código legacy."""
    
    def __init__(self):
        self._graph = get_compiled_graph()  # type: ignore
    
    def invoke(self, state: AgentState) -> AgentState:
        return self._graph.invoke(state)  # type: ignore
    
    async def ainvoke(self, state: AgentState) -> AgentState:
        return await self._graph.ainvoke(state)  # type: ignore


# =============================================================================
# VARIABLE PARA LANGGRAPH CLI 
# =============================================================================

# Variable que exporta el grafo compilado para LangGraph CLI
graph = get_compiled_graph()
