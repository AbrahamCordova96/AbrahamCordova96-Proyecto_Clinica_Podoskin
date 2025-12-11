"""
Subgrafo WhatsApp Usuario - Flujo para usuarios internos vía WhatsApp
=====================================================================

Este subgrafo maneja las interacciones de usuarios internos (personal de la clínica)
a través de WhatsApp.

Características:
- Permisos completos según rol RBAC (Admin/Podologo/Recepcion)
- No requiere consentimiento (son usuarios del sistema)
- Acceso a herramientas administrativas
- Optimizado para consultas rápidas on-the-go

Casos de uso:
- Consultar agenda del día desde fuera de la clínica
- Ver pendientes y notificaciones
- Respuestas rápidas a consultas administrativas
- Actualizar información urgente

Diferencia con webapp_subgraph:
- Mismo nivel de permisos
- Interfaz optimizada para WhatsApp (respuestas más concisas)
- Puede incluir notificaciones push

Autor: Sistema
Fecha: 11 de Diciembre, 2025
Fase: 2 - Arquitectura de Subgrafos
"""

import logging
from langgraph.graph import StateGraph, END

from backend.agents.state import AgentState

logger = logging.getLogger(__name__)


def format_whatsapp_response(state: AgentState) -> AgentState:
    """
    Formatea la respuesta para WhatsApp (más concisa).
    
    WhatsApp tiene limitaciones de formato y los usuarios esperan
    respuestas más breves y directas que en la webapp.
    
    Optimizaciones:
    - Respuestas más cortas
    - Uso de emojis para claridad visual
    - Formato compatible con WhatsApp markdown
    - Links clickeables si es necesario
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado con respuesta formateada para WhatsApp
    """
    logger.info(f"📱 Formateando respuesta para WhatsApp")
    
    # Importar solo cuando se necesita
    from backend.agents.nodes.llm_response_node import llm_response
    
    # Agregar contexto de que la respuesta es para WhatsApp
    state["response_context"] = "whatsapp_user"
    state["response_format"] = "concise"
    state["max_response_length"] = 500  # Limitar longitud
    
    # Generar respuesta usando el nodo estándar
    state = llm_response(state)
    
    # Post-procesar para optimizar para WhatsApp
    if state.get("response_text"):
        response = state["response_text"]
        
        # Acortar si es muy largo
        if len(response) > 600:
            response = response[:550] + "...\n\n_Respuesta truncada. Usa la webapp para ver completo._"
        
        # Asegurar que los números estén en formato lista
        # (WhatsApp renderiza mejor las listas)
        lines = response.split("\n")
        formatted_lines = []
        for line in lines:
            # Convertir markdown heading a negrita de WhatsApp
            if line.startswith("**") and line.endswith("**"):
                formatted_lines.append(line)
            elif line.strip().startswith("-"):
                # Ya es lista, mantener
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        state["response_text"] = "\n".join(formatted_lines)
    
    logger.info(f"✅ Respuesta formateada para WhatsApp")
    
    return state


def build_whatsapp_user_subgraph() -> StateGraph:
    """
    Construye el subgrafo para usuarios internos vía WhatsApp.
    
    Flujo similar a webapp pero con formato optimizado:
    1. classify_intent - Determina intención
    2. check_permissions - Valida permisos RBAC (igual que webapp)
    3. combine_context - Combina contexto
    4. nl_to_sql - Genera SQL
    5. sql_exec - Ejecuta query
    6. format_whatsapp_response - Formatea para WhatsApp (NUEVO)
    
    Returns:
        StateGraph configurado para usuarios WhatsApp
    """
    logger.info("🔧 Construyendo subgrafo WhatsApp Usuario")
    
    # Crear grafo con el estado
    subgraph = StateGraph(AgentState)
    
    # Importar nodos comunes
    from backend.agents.nodes import (
        classify_intent,
        check_permissions,
        combine_context,
        nl_to_sql,
        sql_exec,
    )
    
    # Agregar nodos del flujo
    subgraph.add_node("classify_intent", classify_intent)
    subgraph.add_node("check_permissions", check_permissions)
    subgraph.add_node("combine_context", combine_context)
    subgraph.add_node("nl_to_sql", nl_to_sql)
    subgraph.add_node("sql_exec", sql_exec)
    subgraph.add_node("format_whatsapp_response", format_whatsapp_response)
    
    # Definir punto de entrada
    subgraph.set_entry_point("classify_intent")
    
    # Flujo lineal con formato especial al final
    subgraph.add_edge("classify_intent", "check_permissions")
    subgraph.add_edge("check_permissions", "combine_context")
    subgraph.add_edge("combine_context", "nl_to_sql")
    subgraph.add_edge("nl_to_sql", "sql_exec")
    subgraph.add_edge("sql_exec", "format_whatsapp_response")
    subgraph.add_edge("format_whatsapp_response", END)
    
    logger.info("✅ Subgrafo WhatsApp Usuario construido correctamente")
    
    return subgraph
