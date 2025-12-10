"""
Nodo de Generación SQL desde Lenguaje Natural
==============================================

Convierte la consulta del usuario en SQL usando Claude Haiku 3.5.
Incluye contexto del esquema y ejemplos para mejor precisión.
"""

import json
import logging
from typing import Dict, Any

from anthropic import Anthropic

from backend.api.core.config import get_settings
from backend.agents.state import (
    AgentState,
    IntentType,
    ErrorType,
    DatabaseTarget,
    SQLQuery,
    add_log_entry,
)
from backend.tools.schema_info import (
    get_schema_context_for_prompt,
    build_query_context,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# PROMPTS PARA GENERACIÓN SQL
# =============================================================================

SQL_GENERATION_SYSTEM_PROMPT = """Eres un experto en SQL para PostgreSQL que genera consultas para un sistema de gestión clínica podológica.

## Reglas ESTRICTAS:
1. SOLO genera consultas SELECT (lectura)
2. USA los esquemas correctos: auth., clinic., ops., finance.
3. SIEMPRE usa `deleted_at IS NULL` para tablas con soft delete (NO `activo = true`)
4. USA ILIKE para búsquedas de texto (case insensitive)  
5. LIMITA resultados a 100 filas máximo
6. NO uses subconsultas complejas ni funciones de ventana
7. USA alias claros para columnas en el resultado

## ⚠️ CRÍTICO: NO HAGAS JOINs ENTRE BASES DE DATOS DIFERENTES
- clinic.* tablas están en clinica_core_db
- ops.* tablas están en clinica_ops_db  
- auth.* tablas están en clinica_auth_db
- finance.* tablas están en clinica_ops_db
- Solo puedes hacer JOIN entre tablas del MISMO esquema/base
- Si necesitas datos de múltiples bases, usa consultas separadas

## Esquema de Base de Datos:
{schema_context}

## Formato de Respuesta:
Responde SIEMPRE con JSON válido:
{{
  "sql": "SELECT ... FROM ...",
  "params": {{}},
  "target_db": "core",
  "tables_involved": ["clinic.pacientes"],
  "explanation": "Esta consulta busca..."
}}

## Ejemplos CORRECTOS:

Usuario: "Lista los pacientes"
{{
  "sql": "SELECT id_paciente, nombres, apellidos, telefono, email, fecha_nacimiento FROM clinic.pacientes WHERE deleted_at IS NULL ORDER BY apellidos, nombres LIMIT 100",
  "params": {{}},
  "target_db": "core",
  "tables_involved": ["clinic.pacientes"],
  "explanation": "Lista todos los pacientes activos ordenados por apellido"
}}

Usuario: "Muestra las citas de hoy"
{{
  "sql": "SELECT id_cita, paciente_id, fecha_cita, hora_inicio, hora_fin, status FROM ops.citas WHERE DATE(fecha_cita) = CURRENT_DATE AND deleted_at IS NULL ORDER BY hora_inicio",
  "params": {{}},
  "target_db": "ops", 
  "tables_involved": ["ops.citas"],
  "explanation": "Muestra citas programadas para hoy (solo IDs de paciente, no nombres)"
}}

Usuario: "¿Cuántos tratamientos en curso tenemos?"
{{
  "sql": "SELECT COUNT(*) as total_en_curso FROM clinic.tratamientos WHERE estado_tratamiento = 'En Curso' AND deleted_at IS NULL",
  "params": {{}},
  "target_db": "core",
  "tables_involved": ["clinic.tratamientos"],
  "explanation": "Cuenta tratamientos activos en estado 'En Curso'"
}}

Usuario: "Busca al paciente Juan Pérez"
{{
  "sql": "SELECT id_paciente, nombres, apellidos, telefono, email, fecha_nacimiento FROM clinic.pacientes WHERE (nombres ILIKE :nombre OR apellidos ILIKE :nombre) AND deleted_at IS NULL LIMIT 10",
  "params": {{"nombre": "%Juan Pérez%"}},
  "target_db": "core",
  "tables_involved": ["clinic.pacientes"],
  "explanation": "Busca pacientes cuyo nombre o apellido contenga 'Juan Pérez'"
}}"""


SQL_GENERATION_USER_TEMPLATE = """Consulta del usuario: "{query}"

Contexto detectado:
- Intención: {intent}
- Entidades: {entities}
- Valores extraídos: {values}

Genera la consulta SQL correspondiente."""


# =============================================================================
# FUNCIÓN DE GENERACIÓN SQL
# =============================================================================

def generate_sql(state: AgentState) -> AgentState:
    """
    Nodo que genera SQL a partir de la consulta del usuario.
    
    Args:
        state: Estado actual con intent y entidades clasificadas
        
    Returns:
        Estado actualizado con sql_query
    """
    add_log_entry(state, "generate_sql", "Generando consulta SQL")
    
    user_query = state.get("user_query", "")
    intent = state.get("intent", IntentType.QUERY_READ)
    entities = state.get("entities_extracted", {})
    
    # Para intenciones que no requieren SQL
    if intent in [IntentType.GREETING, IntentType.OUT_OF_SCOPE, IntentType.CLARIFICATION]:
        add_log_entry(state, "generate_sql", f"Intent {intent.value} no requiere SQL")
        state["node_path"] = state.get("node_path", []) + ["generate_sql"]
        return state
    
    # Solo permitir lecturas desde el agente
    if intent in [IntentType.MUTATION_CREATE, IntentType.MUTATION_UPDATE, IntentType.MUTATION_DELETE]:
        state["error_type"] = ErrorType.PERMISSION_DENIED
        state["error_user_message"] = (
            "🔒 Las operaciones de modificación deben hacerse desde la interfaz principal.\n\n"
            "Este asistente solo puede consultar información."
        )
        add_log_entry(state, "generate_sql", "Mutación rechazada - solo lectura permitida")
        state["node_path"] = state.get("node_path", []) + ["generate_sql"]
        return state
    
    try:
        # Construir contexto de esquema
        schema_context = get_schema_context_for_prompt()
        
        # Obtener contexto adicional de las tablas detectadas
        tables_detected = entities.get("_tables", [])
        if tables_detected:
            query_context = build_query_context(entities.get("_entities", []))
            # Agregar JOINs sugeridos al contexto
            if query_context.get("suggested_joins"):
                schema_context += "\n\n## JOINs Sugeridos:\n"
                for join in query_context["suggested_joins"]:
                    schema_context += f"- {join['from_table']}.{join['from_column']} -> {join['to_table']}.{join['to_column']}\n"
        
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        response = client.messages.create(
            model=settings.CLAUDE_MODEL,
            max_tokens=1000,
            temperature=0.0,  # Determinístico para SQL
            system=SQL_GENERATION_SYSTEM_PROMPT.format(schema_context=schema_context),
            messages=[{
                "role": "user",
                "content": SQL_GENERATION_USER_TEMPLATE.format(
                    query=user_query,
                    intent=intent.value,
                    entities=entities.get("_entities", []),
                    values={k: v for k, v in entities.items() if not k.startswith("_")},
                )
            }]
        )
        
        # Parsear respuesta
        # Manejar respuesta de Anthropic con type safety
        first_content = response.content[0]
        result_text: str = getattr(first_content, 'text', str(first_content))
        result = _parse_sql_response(result_text)
        
        # Crear SQLQuery
        target_db = _map_target_db(result.get("target_db", "core"))
        
        state["sql_query"] = SQLQuery(
            query=result["sql"],
            params=result.get("params", {}),
            target_db=target_db,
            is_mutation=False,
            tables_involved=result.get("tables_involved", []),
        )
        
        state["target_database"] = target_db
        
        add_log_entry(
            state, "generate_sql",
            f"SQL generado: {result['sql'][:100]}..."
        )
        
    except Exception as e:
        logger.error(f"Error generando SQL: {str(e)}")
        add_log_entry(state, "generate_sql", f"Error: {str(e)}", level="error")
        
        state["error_type"] = ErrorType.SQL_ERROR
        state["error_internal_message"] = str(e)
        state["error_user_message"] = (
            "⚠️ No pude interpretar tu consulta correctamente.\n\n"
            "Intenta reformularla de otra manera."
        )
    
    state["node_path"] = state.get("node_path", []) + ["generate_sql"]
    return state


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _parse_sql_response(response_text: str) -> Dict[str, Any]:
    """Parsea la respuesta JSON del LLM."""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Buscar JSON en la respuesta
    import re
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group())
        except json.JSONDecodeError:
            pass
    
    # Fallback: intentar extraer SQL directamente
    sql_match = re.search(r'SELECT.*?(?:LIMIT \d+|;|$)', response_text, re.IGNORECASE | re.DOTALL)
    if sql_match:
        return {
            "sql": sql_match.group().strip().rstrip(';'),
            "params": {},
            "target_db": "core",
            "tables_involved": [],
        }
    
    raise ValueError(f"No se pudo parsear respuesta SQL: {response_text[:200]}")


def _map_target_db(db_name: str) -> DatabaseTarget:
    """Mapea nombre de BD a DatabaseTarget."""
    mapping = {
        "auth": DatabaseTarget.AUTH,
        "core": DatabaseTarget.CORE,
        "clinic": DatabaseTarget.CORE,
        "ops": DatabaseTarget.OPS,
        "finance": DatabaseTarget.OPS,
    }
    return mapping.get(db_name.lower(), DatabaseTarget.CORE)


# =============================================================================
# NODE WRAPPER PARA LANGGRAPH (compatibilidad)
# =============================================================================

class NLToSQLNode:
    """Wrapper de nodo para compatibilidad con LangGraph."""
    
    def __init__(self):
        self.name = "generate_sql"
    
    def __call__(self, state: AgentState) -> AgentState:
        return generate_sql(state)
    
    def run(self, state: AgentState, question: str) -> AgentState:
        """Método legacy para compatibilidad."""
        state["user_query"] = question
        return generate_sql(state)
