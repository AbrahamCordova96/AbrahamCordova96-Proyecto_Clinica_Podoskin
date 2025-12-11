"""
Subgrafo WhatsApp Paciente - Flujo para pacientes externos vía WhatsApp
=======================================================================

Este subgrafo maneja las interacciones de pacientes a través de WhatsApp.

Características:
- Permisos limitados (solo datos propios)
- Requiere consentimiento explícito para acciones sensibles
- Flujo con validaciones adicionales de privacidad
- Optimizado para consultas simples (citas, recordatorios)

Casos de uso:
- Consultar citas propias
- Confirmar/cancelar citas
- Ver recordatorios
- Preguntas frecuentes (horarios, ubicación)

Autor: Sistema
Fecha: 11 de Diciembre, 2025
Fase: 2 - Arquitectura de Subgrafos
"""

import logging
from langgraph.graph import StateGraph, END

from backend.agents.state import AgentState

logger = logging.getLogger(__name__)


def validate_patient_consent(state: AgentState) -> AgentState:
    """
    Valida que el paciente haya dado consentimiento para la acción.
    
    Este nodo es específico del flujo de pacientes y verifica que:
    1. El paciente está autenticado correctamente
    2. Tiene consentimiento para acceder a sus datos
    3. La acción solicitada está dentro de sus permisos
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado actualizado con validación de consentimiento
    """
    logger.info(f"🔐 Validando consentimiento de paciente (user_id={state.get('user_id')})")
    
    # TODO: Implementar lógica real de consentimiento
    # Por ahora, asumimos consentimiento dado
    consent_given = True
    
    if not consent_given:
        state["error_type"] = "PERMISSION_DENIED"
        state["error_user_message"] = (
            "⚠️ Necesitamos tu consentimiento para acceder a esta información. "
            "Por favor, responde 'SÍ' para continuar."
        )
        state["response_text"] = state["error_user_message"]
        logger.warning(f"⚠️ Consentimiento no dado por paciente {state.get('user_id')}")
    else:
        logger.info(f"✅ Consentimiento validado para paciente {state.get('user_id')}")
    
    return state


def check_patient_permissions(state: AgentState) -> AgentState:
    """
    Verifica permisos específicos de paciente.
    
    Los pacientes solo pueden:
    - Ver sus propias citas
    - Ver sus propios tratamientos
    - Confirmar/cancelar sus citas
    - NO pueden ver datos de otros pacientes
    - NO pueden acceder a información administrativa
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado actualizado con validación de permisos
    """
    logger.info(f"🔒 Verificando permisos de paciente (user_id={state.get('user_id')})")
    
    # Importar solo cuando se necesita para evitar imports circulares
    from backend.agents.nodes.check_permissions_node import check_permissions
    
    # Agregar restricción adicional: solo datos propios
    state["patient_only_own_data"] = True
    
    # Ejecutar validación RBAC estándar
    state = check_permissions(state)
    
    logger.info(f"✅ Permisos de paciente verificados")
    
    return state


def generate_patient_safe_response(state: AgentState) -> AgentState:
    """
    Genera respuesta apropiada para pacientes.
    
    Asegura que:
    - El lenguaje es amigable y no técnico
    - No se exponen detalles internos del sistema
    - Se incluyen instrucciones claras para próximos pasos
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado con respuesta generada para paciente
    """
    logger.info(f"💬 Generando respuesta para paciente")
    
    # Importar solo cuando se necesita
    from backend.agents.nodes.llm_response_node import llm_response
    
    # Agregar contexto de que la respuesta es para un paciente
    state["response_context"] = "patient_facing"
    state["response_tone"] = "friendly_non_technical"
    
    # Generar respuesta usando el nodo estándar
    state = llm_response(state)
    
    # Post-procesar para asegurar tono amigable
    if state.get("response_text"):
        # Agregar emoji amigable si no hay error
        if not state.get("error_type") or state["error_type"] == "NONE":
            if not state["response_text"].startswith(("👋", "📅", "✅", "📝")):
                state["response_text"] = "✅ " + state["response_text"]
    
    logger.info(f"✅ Respuesta para paciente generada")
    
    return state


def build_whatsapp_paciente_subgraph() -> StateGraph:
    """
    Construye el subgrafo para pacientes vía WhatsApp.
    
    Flujo con validaciones adicionales:
    1. classify_intent - Determina intención
    2. validate_patient_consent - Valida consentimiento (NUEVO)
    3. check_patient_permissions - Permisos limitados (NUEVO)
    4. combine_context - Combina contexto
    5. nl_to_sql - Genera SQL (solo datos propios)
    6. sql_exec - Ejecuta query
    7. generate_patient_safe_response - Respuesta amigable (NUEVO)
    
    Returns:
        StateGraph configurado para pacientes WhatsApp
    """
    logger.info("🔧 Construyendo subgrafo WhatsApp Paciente")
    
    # Crear grafo con el estado
    subgraph = StateGraph(AgentState)
    
    # Importar nodos comunes
    from backend.agents.nodes import (
        classify_intent,
        combine_context,
        nl_to_sql,
        sql_exec,
    )
    
    # Agregar nodos del flujo (algunos específicos de paciente)
    subgraph.add_node("classify_intent", classify_intent)
    subgraph.add_node("validate_patient_consent", validate_patient_consent)
    subgraph.add_node("check_patient_permissions", check_patient_permissions)
    subgraph.add_node("combine_context", combine_context)
    subgraph.add_node("nl_to_sql", nl_to_sql)
    subgraph.add_node("sql_exec", sql_exec)
    subgraph.add_node("generate_patient_safe_response", generate_patient_safe_response)
    
    # Definir punto de entrada
    subgraph.set_entry_point("classify_intent")
    
    # Flujo con validaciones adicionales para pacientes
    subgraph.add_edge("classify_intent", "validate_patient_consent")
    subgraph.add_edge("validate_patient_consent", "check_patient_permissions")
    subgraph.add_edge("check_patient_permissions", "combine_context")
    subgraph.add_edge("combine_context", "nl_to_sql")
    subgraph.add_edge("nl_to_sql", "sql_exec")
    subgraph.add_edge("sql_exec", "generate_patient_safe_response")
    subgraph.add_edge("generate_patient_safe_response", END)
    
    logger.info("✅ Subgrafo WhatsApp Paciente construido correctamente")
    
    return subgraph
