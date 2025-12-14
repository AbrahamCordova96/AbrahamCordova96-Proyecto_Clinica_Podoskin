"""
Nodo de Clasificación de Intención
==================================

Analiza la consulta del usuario para determinar:
- Tipo de intención (lectura, escritura, fuera de alcance)
- Entidades mencionadas (pacientes, citas, etc.)
- Confianza de la clasificación

Usa Claude Haiku 3.5 para clasificación inteligente.
"""

import json
import logging
from typing import Dict, Any, Tuple

from anthropic import Anthropic
from anthropic.types import TextBlock

from backend.api.core.config import get_settings
from backend.agents.state import (
    AgentState,
    IntentType,
    ErrorType,
    add_log_entry,
)
from backend.tools.schema_info import ENTITY_TO_TABLE
from backend.agents.maya_personality import enhance_prompt_with_maya_personality

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# PROMPTS PARA CLASIFICACIÓN
# =============================================================================

CLASSIFICATION_SYSTEM_PROMPT_BASE = """Eres un clasificador de intenciones para un sistema de gestión clínica podológica (PodoSkin).

Tu tarea es analizar la consulta del usuario y determinar:
1. El tipo de intención
2. Las entidades mencionadas
3. Tu nivel de confianza

## Tipos de Intención Válidos:
- query_read: Consultas de lectura (buscar pacientes, ver citas, listar tratamientos)
- query_aggregate: Consultas de agregación (contar, sumar, promediar)
- mutation_create: Crear nuevos registros (agendar cita, registrar paciente)
- mutation_update: Actualizar registros existentes
- mutation_delete: Eliminar registros
- clarification: La consulta es ambigua y necesita más información
- out_of_scope: La consulta no está relacionada con la clínica
- greeting: Saludo o conversación casual

## Entidades del Dominio:
- paciente/pacientes: Datos de pacientes
- tratamiento/tratamientos: Carpetas de problemas médicos
- evolucion/evoluciones: Notas clínicas de visitas
- cita/citas: Agenda de citas
- podologo/podologos: Personal clínico
- servicio/servicios: Catálogo de servicios
- prospecto/prospectos: Leads/contactos potenciales
- pago/pagos: Pagos recibidos
- gasto/gastos: Gastos operativos

## Responde SIEMPRE en formato JSON:
{
  "intent": "query_read",
  "confidence": 0.95,
  "entities": ["paciente", "cita"],
  "extracted_values": {
    "nombre_paciente": "Juan Pérez",
    "fecha": "hoy"
  },
  "reasoning": "El usuario busca las citas de un paciente específico"
}"""


CLASSIFICATION_USER_TEMPLATE = """Consulta del usuario: "{query}"

Contexto adicional:
- Rol del usuario: {role}
- Hora actual: {current_time}

Clasifica esta consulta y extrae las entidades relevantes."""


# =============================================================================
# FUNCIÓN DE CLASIFICACIÓN
# =============================================================================

def classify_intent(state: AgentState) -> AgentState:
    """
    Nodo que clasifica la intención del usuario.
    
    Este es el primer nodo del grafo y determina el flujo posterior.
    
    Args:
        state: Estado actual del agente
        
    Returns:
        Estado actualizado con intent, entities, confidence
    """
    add_log_entry(state, "classify_intent", "Iniciando clasificación de intención")
    
    user_query = state.get("user_query", "")
    user_role = state.get("user_role", "Recepcion")
    
    # Clasificación rápida para casos obvios (sin llamar a LLM)
    quick_result = _quick_classify(user_query)
    if quick_result:
        intent, confidence = quick_result
        state["intent"] = intent
        state["intent_confidence"] = confidence
        state["entities_extracted"] = {}
        add_log_entry(state, "classify_intent", f"Clasificación rápida: {intent.value}")
        return state
    
    # Llamar a Claude para clasificación inteligente
    try:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        from datetime import datetime
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # ✨ NUEVO: Mejorar prompt con personalidad de Maya
        user_name = state.get("user_name")
        enhanced_system_prompt = enhance_prompt_with_maya_personality(
            CLASSIFICATION_SYSTEM_PROMPT_BASE,
            user_name=user_name,
            user_role=user_role
        )
        
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=500,
            temperature=0.0,  # Determinístico para clasificación
            system=enhanced_system_prompt,
            messages=[{
                "role": "user",
                "content": CLASSIFICATION_USER_TEMPLATE.format(
                    query=user_query,
                    role=user_role,
                    current_time=current_time,
                )
            }]
        )
        
        # Parsear respuesta JSON - filtrar solo TextBlock
        text_blocks = [block for block in response.content if isinstance(block, TextBlock)]
        result_text = text_blocks[0].text if text_blocks else ""
        
        result = _parse_classification_response(result_text)
        
        # Verificar que el resultado tenga las claves necesarias
        if "intent" not in result:
            raise KeyError(f"Resultado de clasificación inválido: {result}")
        
        state["intent"] = IntentType(result["intent"])
        state["intent_confidence"] = result["confidence"]
        state["entities_extracted"] = result.get("extracted_values", {})
        
        # Mapear entidades a tablas
        entities = result.get("entities", [])
        state["entities_extracted"]["_entities"] = entities
        state["entities_extracted"]["_tables"] = [
            ENTITY_TO_TABLE.get(e, e) for e in entities if e in ENTITY_TO_TABLE
        ]
        
        add_log_entry(
            state, "classify_intent", 
            f"Clasificación LLM: {result['intent']} (confianza: {result['confidence']})"
        )
        
    except Exception as e:
        logger.error(f"Error en clasificación: {str(e)}")
        add_log_entry(state, "classify_intent", f"Error: {str(e)}", level="error")
        
        # Fallback: asumir consulta de lectura con baja confianza
        state["intent"] = IntentType.CLARIFICATION
        state["intent_confidence"] = 0.3
        state["error_type"] = ErrorType.INTERNAL
        state["error_internal_message"] = str(e)
    
    state["node_path"] = state.get("node_path", []) + ["classify_intent"]
    return state


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _quick_classify(query: str) -> Tuple[IntentType, float] | None:
    """
    Clasificación rápida para casos obvios sin usar LLM.
    
    Returns:
        Tuple (IntentType, confidence) o None si necesita LLM
    """
    query_lower = query.lower().strip()
    
    # Saludos
    greetings = ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal"]
    if any(query_lower.startswith(g) for g in greetings) and len(query_lower) < 30:
        return (IntentType.GREETING, 0.95)
    
    # Fuera de alcance obvio
    out_of_scope = ["clima", "tiempo", "noticias", "chiste", "juego", "música"]
    if any(word in query_lower for word in out_of_scope):
        return (IntentType.OUT_OF_SCOPE, 0.9)
    
    # Consultas de conteo
    if any(word in query_lower for word in ["cuántos", "cuantos", "total de", "número de"]):
        return (IntentType.QUERY_AGGREGATE, 0.85)
    
    # Consultas de lectura obvias
    read_patterns = [
        "muéstrame", "muestrame", "ver ", "buscar", "listar", 
        "mostrar", "dame", "cuáles", "cuales", "quién", "quien"
    ]
    if any(pattern in query_lower for pattern in read_patterns):
        return (IntentType.QUERY_READ, 0.8)
    
    return None


def _parse_classification_response(response_text: str) -> Dict[str, Any]:
    """
    Parsea la respuesta JSON del LLM.
    
    Maneja casos donde el LLM incluye texto adicional.
    """
    # Buscar JSON en la respuesta
    try:
        # Intentar parseo directo
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Buscar JSON más robusto - buscar desde primera { hasta última }
    start = response_text.find('{')
    end = response_text.rfind('}')
    
    if start != -1 and end != -1 and end > start:
        json_text = response_text[start:end+1]
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass
    
    # Buscar JSON línea por línea
    lines = response_text.split('\n')
    for i, line in enumerate(lines):
        if line.strip().startswith('{'):
            # Intentar desde esta línea hasta el final
            remaining = '\n'.join(lines[i:])
            try:
                return json.loads(remaining)
            except json.JSONDecodeError:
                continue
    
    # Fallback: extraer campos manualmente
    logger.warning(f"No se pudo parsear JSON de clasificación: {response_text[:200]}")
    
    return {
        "intent": "clarification",
        "confidence": 0.5,
        "entities": [],
        "extracted_values": {},
        "reasoning": "No se pudo parsear la respuesta del clasificador"
    }


# =============================================================================
# NODE WRAPPER PARA LANGGRAPH
# =============================================================================

class ClassifyIntentNode:
    """Wrapper de nodo para compatibilidad con LangGraph."""
    
    def __init__(self):
        self.name = "classify_intent"
    
    def __call__(self, state: AgentState) -> AgentState:
        return classify_intent(state)
