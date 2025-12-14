"""
Nodo de Generación de Respuesta
===============================

Genera respuestas amigables para el usuario basándose en:
- Resultados de la consulta SQL
- Estado de error (si hay)
- Tipo de intención original

Implementa los mensajes amigables según Decisión 5:
- Sin tecnicismos
- Con sugerencias de acción
- Emojis para claridad visual
"""

import json
import logging
from typing import Dict, List

from anthropic import Anthropic

from backend.api.core.config import get_settings
from backend.agents.state import (
    AgentState,
    IntentType,
    ErrorType,
    ExecutionResult,
    add_log_entry,
    format_friendly_error,
)
from backend.agents.maya_personality import (
    get_maya_system_prompt,
    get_maya_greeting_prompt,
    get_maya_error_prompt,
    get_maya_out_of_scope_prompt,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# PROMPTS PARA GENERACIÓN DE RESPUESTA
# =============================================================================

RESPONSE_SYSTEM_PROMPT_BASE = """Eres Maya, la asistente amigable de PodoSkin Clínica Podológica.

Tu tarea es presentar información de forma clara, natural y útil.

## Reglas de Estilo (Personalidad Maya):
1. **Español natural mexicano** - Usa "mira", "oye", "fíjate"
2. **Segura y directa** - Afirma con convicción, no "creo que..."
3. **Cálida pero profesional** - Amable sin ser empalagosa
4. **Emojis moderados** - Solo cuando añaden claridad
5. **Sin tecnicismos** - Nada de nombres de tablas o columnas SQL
6. **Con personalidad** - Un toque de ironía sutil cuando sea apropiado

## Formato de Datos:
- Fechas: "15 de enero de 2024" (no "2024-01-15")
- Teléfonos: mantener formato original
- Nombres: capitalizar correctamente
- Dinero: "$1,500.00 MXN"

## Estructura de Respuestas:
1. Presenta la información de forma clara
2. SIEMPRE termina con pregunta o sugerencia de siguiente paso
3. Sé proactiva - anticipa qué más podrían necesitar

## Ejemplos de Respuestas Buenas:

Para lista de citas:
"📅 **Citas de hoy:**

1. **María García** - 10:00 AM
   - Revisión de uña encarnada
   
2. **Juan Pérez** - 11:30 AM  
   - Control de tratamiento

¿Necesitas ver más detalles de alguna cita?"

Para búsqueda de paciente:
"👤 Encontré a **Juan Pérez López**:
- 📱 Teléfono: 55 1234 5678
- 📧 Email: juan@email.com
- 🎂 Edad: 45 años

¿Quieres ver sus tratamientos o agendar una cita?"
"""

RESPONSE_USER_TEMPLATE = """Consulta original del usuario: "{query}"

Datos obtenidos:
```json
{data}
```

Total de registros: {row_count}
Columnas: {columns}

Genera una respuesta amigable y clara para el usuario."""


# =============================================================================
# FUNCIÓN DE GENERACIÓN DE RESPUESTA
# =============================================================================

def generate_response(state: AgentState) -> AgentState:
    """
    Nodo que genera la respuesta final para el usuario.
    
    Args:
        state: Estado con resultados de ejecución o errores
        
    Returns:
        Estado actualizado con response_text y response_data
    """
    add_log_entry(state, "generate_response", "Generando respuesta para usuario")
    
    intent = state.get("intent", IntentType.QUERY_READ)
    error_type = state.get("error_type", ErrorType.NONE)
    
    # 1. Manejar intenciones especiales primero
    if intent == IntentType.GREETING:
        state["response_text"] = _get_greeting_response(state.get("user_query", ""))
        state["node_path"] = state.get("node_path", []) + ["generate_response"]
        return state
    
    if intent == IntentType.OUT_OF_SCOPE:
        state["response_text"] = _get_out_of_scope_response()
        state["node_path"] = state.get("node_path", []) + ["generate_response"]
        return state

    if intent == IntentType.CLARIFICATION:
        state["response_text"] = _get_clarification_response(state)
        state["node_path"] = state.get("node_path", []) + ["generate_response"]
        return state

    # 2. Manejar errores
    if error_type != ErrorType.NONE:
        state["response_text"] = _format_error_response(state)
        state["node_path"] = state.get("node_path", []) + ["generate_response"]
        return state

    # 3. Generar respuesta desde resultados
    result = state.get("execution_result")
    if not result or not result.success:
        state["response_text"] = "No pude completar la búsqueda. Por favor, intenta de nuevo."
        state["node_path"] = state.get("node_path", []) + ["generate_response"]
        return state

    # Si hay pocos resultados (pero al menos 1), formatear directamente para velocidad
    if 0 < result.row_count <= 5:
        state["response_text"] = _format_simple_results(state, result)
    else:
        # Caso: 0 resultados o > 5 resultados.
        # Usar LLM para:
        # a) Explicar amigablemente que no hubo resultados (ej: "No hay citas, el día está libre")
        # b) Resumir grandes cantidades de datos
        state["response_text"] = _format_with_llm(state, result)

    # Guardar datos estructurados para UI
    state["response_data"] = {
        "row_count": result.row_count,
        "columns": result.columns,
        "data": result.data[:20],  # Limitar para response_data
        "execution_time_ms": result.execution_time_ms,
    }

    add_log_entry(state, "generate_response", f"Respuesta generada ({len(state['response_text'])} chars)")
    state["node_path"] = state.get("node_path", []) + ["generate_response"]
    return state


# =============================================================================
# FUNCIONES DE FORMATEO
# =============================================================================

def _get_greeting_response(query: str) -> str:
    """Genera respuesta de saludo usando LLM."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=300,
            temperature=0.3,
            system="Eres el asistente de una clínica podológica. Responde al saludo de forma amigable y menciona qué tipo de información real de la base de datos puedes consultar.",
            messages=[{
                "role": "user", 
                "content": f"El usuario me dijo: '{query}'. Responde el saludo y explica brevemente qué puedes hacer."
            }]
        )
        first_content = response.content[0]
        return getattr(first_content, 'text', str(first_content))
    except Exception:
        # Fallback mínimo sin ejemplos específicos
        return "¡Hola! Soy tu asistente de la clínica. ¿Qué información necesitas consultar?"


def _get_out_of_scope_response() -> str:
    """Genera respuesta para consultas fuera del alcance usando LLM."""
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    try:
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=300,
            temperature=0.3,
            system="Eres un asistente especializado en bases de datos de clínicas podológicas. Explica amablemente que no puedes ayudar con temas fuera de la gestión clínica.",
            messages=[{
                "role": "user",
                "content": "Explica qué tipo de consultas SÍ puedes responder sobre la base de datos de la clínica."
            }]
        )
        first_content = response.content[0]
        return getattr(first_content, 'text', str(first_content))
    except Exception:
        return "Esa consulta está fuera de mi especialidad. Puedo ayudarte con información de la base de datos de la clínica."
def _get_clarification_response(state: AgentState) -> str:
    """Genera respuesta pidiendo clarificación usando LLM."""
    entities = state.get("entities_extracted", {})
    user_query = state.get("user_query", "")
    
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    try:
        context = f"Usuario preguntó: '{user_query}'"
        if entities.get("_entities"):
            context += f"\nEntidades detectadas: {entities['_entities']}"
        
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=400,
            temperature=0.3,
            system="Eres un asistente de clínica podológica. La consulta del usuario es ambigua. Pide clarificación de forma amigable y sugiere formas específicas de reformular la pregunta.",
            messages=[{
                "role": "user",
                "content": context + "\n\nGenera una respuesta que pida clarificación y dé ejemplos específicos de cómo reformular la pregunta."
            }]
        )
        first_content = response.content[0]
        return getattr(first_content, 'text', str(first_content))
    except Exception:
        return "🤔 No estoy seguro de qué información necesitas. ¿Podrías ser más específico?"


def _format_error_response(state: AgentState) -> str:
    """Formatea respuesta de error amigable."""
    error_type = state.get("error_type", ErrorType.INTERNAL)
    user_message = state.get("error_user_message")
    suggestions = state.get("fuzzy_suggestions", [])
    
    if user_message:
        return user_message
    
    # Usar mensaje predefinido
    friendly = format_friendly_error(
        error_type,
        context={"alternatives": suggestions} if suggestions else {}
    )
    
    response = f"{friendly['title']}\n\n{friendly['message']}"
    if friendly.get("suggestion"):
        response += f"\n\n💡 {friendly['suggestion']}"
    
    return response


def _format_simple_results(state: AgentState, result: ExecutionResult) -> str:
    """Formatea resultados simples sin usar LLM."""
    data: List[Dict[str, str]] = result.data
    columns: List[str] = result.columns
    row_count: int = result.row_count
    
    if row_count == 0:
        return "📭 No encontré resultados para tu búsqueda."
    
    # Detectar tipo de datos para formateo apropiado
    if "nombres" in columns and "apellidos" in columns:
        return _format_patient_results(data)
    elif "fecha_hora" in columns or "fecha" in columns:
        return _format_appointment_results(data)
    elif "nombre_servicio" in columns:
        return _format_service_results(data)
    else:
        return _format_generic_results(data, columns)


def _format_patient_results(data: List[Dict[str, str]]) -> str:
    """Formatea resultados de búsqueda de pacientes."""
    lines = [f"👤 **Encontré {len(data)} paciente(s):**\n"]
    
    for i, row in enumerate(data[:10], 1):
        nombre = f"{row.get('nombres', '')} {row.get('apellidos', '')}".strip()
        lines.append(f"{i}. **{nombre}**")
        
        if row.get("telefono"):
            lines.append(f"   📱 {row['telefono']}")
        if row.get("email"):
            lines.append(f"   📧 {row['email']}")
        if row.get("fecha_nacimiento"):
            lines.append(f"   🎂 {row['fecha_nacimiento']}")
        lines.append("")
    
    lines.append("¿Necesitas más detalles de algún paciente?")
    return "\n".join(lines)


def _format_appointment_results(data: List[Dict[str, str]]) -> str:
    """Formatea resultados de citas."""
    lines = [f"📅 **{len(data)} cita(s) encontrada(s):**\n"]
    
    for row in data[:10]:
        fecha = row.get("fecha_hora") or row.get("fecha")
        paciente = row.get("paciente_nombre") or row.get("nombres", "")
        motivo = row.get("motivo", "")
        estado = row.get("estado", "")
        
        lines.append(f"• **{fecha}** - {paciente}")
        if motivo:
            lines.append(f"  {motivo}")
        if estado:
            lines.append(f"  Estado: {estado}")
        lines.append("")
    
    return "\n".join(lines)


def _format_service_results(data: List[Dict[str, str]]) -> str:
    """Formatea catálogo de servicios."""
    lines = ["📋 **Servicios disponibles:**\n"]
    
    for row in data[:15]:
        nombre = row.get("nombre_servicio", "")
        precio = row.get("precio", "")
        duracion = row.get("duracion_estimada", "")
        
        line = f"• **{nombre}**"
        if precio:
            line += f" - ${precio:,.2f}" if isinstance(precio, (int, float)) else f" - {precio}"
        if duracion:
            line += f" ({duracion} min)"
        lines.append(line)
    
    return "\n".join(lines)


def _format_generic_results(data: List[Dict[str, str]], columns: List[str]) -> str:
    """Formatea resultados genéricos."""
    
    # Detectar si es una consulta de conteo (COUNT)
    if len(data) == 1 and len(columns) == 1:
        col_name = columns[0].lower()
        if any(word in col_name for word in ['count', 'total', 'cantidad']):
            # Es un conteo - mostrar el valor, no el número de filas
            count_value = data[0][columns[0]]
            entity = ""
            if "pacientes" in col_name:
                entity = "pacientes"
            elif "citas" in col_name:
                entity = "citas"
            elif "tratamientos" in col_name:
                entity = "tratamientos"
            elif "servicios" in col_name:
                entity = "servicios"
            
            if entity:
                return f"📊 **Total de {entity}: {count_value}**"
            else:
                return f"📊 **Resultado: {count_value}**"
    
    # Formateo normal para otros tipos de resultado
    lines = [f"📊 **Encontré {len(data)} resultado(s):**\n"]
    
    # Mostrar columnas principales (máx 5)
    display_cols = columns[:5]
    
    for i, row in enumerate(data[:10], 1):
        values = [str(row.get(col, "")) for col in display_cols]
        lines.append(f"{i}. " + " | ".join(values))
    
    if len(data) > 10:
        lines.append(f"\n... y {len(data) - 10} más")
    
    return "\n".join(lines)


def _format_with_llm(state: AgentState, result: ExecutionResult) -> str:
    """Usa LLM con personalidad de Maya para formatear resultados complejos."""
    try:
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Limitar datos para el prompt
        data_sample = result.data[:20]
        
        # ✨ Usar system prompt con personalidad completa de Maya
        user_name = state.get("user_name")
        user_role = state.get("user_role")
        
        system_prompt = get_maya_system_prompt(
            user_name=user_name,
            user_role=user_role,
            is_known_user=False  # Por ahora, no tenemos esta info
        )
        
        # Add specific instruction for data presentation based on previous template logic
        system_prompt += """
        
## Tarea Actual: Presentar Resultados
Tienes datos crudos de la base de datos.
1. Analízalos.
2. Preséntalos usando tu personalidad (Recuerda tu rol según el usuario).
3. Termina con una sugerencia relevante.
"""
        
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1000,
            temperature=0.3,
            system=system_prompt,
            messages=[{
                "role": "user",
                "content": RESPONSE_USER_TEMPLATE.format(
                    query=state.get("user_query", ""),
                    data=json.dumps(data_sample, default=str, ensure_ascii=False),
                    row_count=result.row_count,
                    columns=result.columns,
                )
            }]
        )
        
        # Manejar respuesta de Anthropic con type safety
        first_content = response.content[0]
        return getattr(first_content, 'text', str(first_content))
        
    except Exception as e:
        logger.error(f"Error en formateo con LLM: {e}")
        # Fallback a formateo simple
        return _format_generic_results(result.data, result.columns)


# =============================================================================
# NODE WRAPPER PARA LANGGRAPH (compatibilidad)
# =============================================================================

class LlmResponseNode:
    """Wrapper de nodo para compatibilidad con LangGraph."""
    
    def __init__(self):
        self.name = "generate_response"
    
    def __call__(self, state: AgentState) -> AgentState:
        return generate_response(state)
    
    def run(self, state: AgentState, context: str) -> AgentState:
        """Método legacy para compatibilidad."""
        return generate_response(state)
