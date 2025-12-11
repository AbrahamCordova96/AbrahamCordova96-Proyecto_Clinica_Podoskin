"""
Root Graph con Routing por Origen - Fase 2
==========================================

Implementa el grafo raíz que enruta a subgrafos especializados según el origen
de la conversación (webapp, whatsapp_paciente, whatsapp_user).

Arquitectura:
┌─────────────────────┐
│   Ingress Gateway   │ (normalización externa)
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│ Root Graph          │
│ - route_by_origin   │
└──────────┬──────────┘
           │
    ┌──────┼──────┐
    ▼      ▼      ▼
┌────────┐ ┌────────┐ ┌────────┐
│ webapp │ │  wh... │ │  wh... │
│  sub   │ │ paci.. │ │ user.. │
└────────┘ └────────┘ └────────┘

Autor: Sistema
Fecha: 11 de Diciembre, 2025
Fase: 2 - Arquitectura de Subgrafos
"""

import logging
from typing import Literal
from langgraph.graph import StateGraph, END

from backend.agents.state import AgentState
from backend.agents.subgraphs import (
    build_webapp_subgraph,
    build_whatsapp_paciente_subgraph,
    build_whatsapp_user_subgraph,
)

logger = logging.getLogger(__name__)


# =============================================================================
# NODO DE ROUTING
# =============================================================================

def route_by_origin_node(state: AgentState) -> AgentState:
    """
    Nodo que registra el origen y prepara el estado para routing.
    
    Este nodo es el entry point del root graph y se encarga de:
    1. Validar que el campo 'origin' existe
    2. Registrar en logs el origen detectado
    3. Agregar metadata útil para debugging
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado con metadata de origen agregada
    """
    origin = state.get("origin", "webapp")
    user_id = state.get("user_id")
    thread_id = state.get("thread_id", "unknown")
    
    logger.info(
        f"🚦 Routing por origen: origin={origin}, "
        f"user_id={user_id}, thread_id={thread_id}"
    )
    
    # Agregar a logs para debugging
    state["logs"] = state.get("logs", [])
    state["logs"].append({
        "node": "route_by_origin",
        "origin": origin,
        "user_id": user_id,
        "thread_id": thread_id,
    })
    
    # Agregar a node_path
    state["node_path"] = state.get("node_path", [])
    state["node_path"].append(f"route_by_origin_{origin}")
    
    return state


def route_by_origin(state: AgentState) -> Literal["webapp_flow", "whatsapp_paciente_flow", "whatsapp_user_flow"]:
    """
    Función de routing condicional que decide qué subgrafo ejecutar.
    
    Basándose en el campo 'origin' del estado, determina el flujo apropiado:
    - 'webapp' → webapp_flow (usuarios internos vía web)
    - 'whatsapp_paciente' → whatsapp_paciente_flow (pacientes vía WhatsApp)
    - 'whatsapp_user' → whatsapp_user_flow (usuarios internos vía WhatsApp)
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Nombre del subgrafo a ejecutar
    """
    origin = state.get("origin", "webapp")
    
    # Mapeo de origen a flujo
    routing_map = {
        "webapp": "webapp_flow",
        "whatsapp_paciente": "whatsapp_paciente_flow",
        "whatsapp_user": "whatsapp_user_flow",
    }
    
    target_flow = routing_map.get(origin, "webapp_flow")  # Default a webapp
    
    logger.info(f"✅ Routing decision: {origin} → {target_flow}")
    
    return target_flow


# =============================================================================
# CONSTRUCCIÓN DEL ROOT GRAPH
# =============================================================================

def build_root_graph() -> StateGraph:
    """
    Construye el grafo raíz con routing a subgrafos.
    
    Este es el nuevo grafo principal que reemplaza al grafo monolítico.
    Implementa la arquitectura de orquestación centralizada con subgrafos
    especializados.
    
    Flujo:
    1. route_by_origin_node - Nodo que registra origen
    2. Conditional routing basado en origin
    3. Ejecución del subgrafo apropiado
    
    Returns:
        StateGraph configurado con subgrafos
    """
    logger.info("🔧 Construyendo Root Graph con subgrafos")
    
    # Crear grafo raíz
    root_graph = StateGraph(AgentState)
    
    # Construir subgrafos
    logger.info("📦 Construyendo subgrafos...")
    webapp_subgraph = build_webapp_subgraph().compile()
    whatsapp_paciente_subgraph = build_whatsapp_paciente_subgraph().compile()
    whatsapp_user_subgraph = build_whatsapp_user_subgraph().compile()
    logger.info("✅ Subgrafos construidos")
    
    # Agregar nodo de routing
    root_graph.add_node("route_by_origin", route_by_origin_node)
    
    # Agregar subgrafos como nodos
    root_graph.add_node("webapp_flow", webapp_subgraph)
    root_graph.add_node("whatsapp_paciente_flow", whatsapp_paciente_subgraph)
    root_graph.add_node("whatsapp_user_flow", whatsapp_user_subgraph)
    
    # Definir entry point
    root_graph.set_entry_point("route_by_origin")
    
    # Routing condicional desde el nodo de routing a los subgrafos
    root_graph.add_conditional_edges(
        "route_by_origin",
        route_by_origin,  # Función que decide el routing
        {
            "webapp_flow": "webapp_flow",
            "whatsapp_paciente_flow": "whatsapp_paciente_flow",
            "whatsapp_user_flow": "whatsapp_user_flow",
        }
    )
    
    # Todos los subgrafos terminan en END
    root_graph.add_edge("webapp_flow", END)
    root_graph.add_edge("whatsapp_paciente_flow", END)
    root_graph.add_edge("whatsapp_user_flow", END)
    
    logger.info("✅ Root Graph construido correctamente con 3 subgrafos")
    
    return root_graph
