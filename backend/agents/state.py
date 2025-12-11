"""
Estado del Agente LangGraph - PodoSkin API
==========================================

Define el TypedDict que fluye a través del grafo de LangGraph.
Implementa manejo de errores amigable según Decisión 5.

Autor: Agente IA
Fecha: 2025
"""

from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


# =============================================================================
# ENUMS DE ESTADO Y ERRORES
# =============================================================================

class IntentType(str, Enum):
    """Tipos de intención detectada en la consulta del usuario."""
    QUERY_READ = "query_read"           # SELECT, consultas de lectura
    QUERY_AGGREGATE = "query_aggregate"  # COUNT, SUM, AVG, etc.
    MUTATION_CREATE = "mutation_create"  # INSERT (requiere confirmación)
    MUTATION_UPDATE = "mutation_update"  # UPDATE (requiere confirmación)
    MUTATION_DELETE = "mutation_delete"  # DELETE (requiere confirmación)
    CLARIFICATION = "clarification"      # Necesita más contexto
    OUT_OF_SCOPE = "out_of_scope"        # Fuera del dominio clínico
    GREETING = "greeting"                # Saludo o conversación casual


class ErrorType(str, Enum):
    """Tipos de error para manejo amigable."""
    NONE = "none"
    AMBIGUOUS_QUERY = "ambiguous_query"       # Consulta ambigua
    NO_RESULTS = "no_results"                 # Sin resultados
    PERMISSION_DENIED = "permission_denied"   # Sin permisos
    INVALID_ENTITY = "invalid_entity"         # Entidad no encontrada (paciente, etc.)
    SQL_ERROR = "sql_error"                   # Error de ejecución SQL
    VALIDATION_ERROR = "validation_error"     # Validación falló
    TIMEOUT = "timeout"                       # Tiempo agotado
    RATE_LIMIT = "rate_limit"                 # Límite de solicitudes
    INTERNAL = "internal"                     # Error interno


class DatabaseTarget(str, Enum):
    """Base de datos objetivo para la consulta."""
    AUTH = "auth"     # clinica_auth_db
    CORE = "core"     # clinica_core_db  
    OPS = "ops"       # clinica_ops_db
    MULTIPLE = "multiple"  # Requiere varias BDs


# =============================================================================
# MENSAJES AMIGABLES (Decisión 5)
# =============================================================================

FRIENDLY_MESSAGES: Dict[ErrorType, Dict[str, str]] = {
    ErrorType.AMBIGUOUS_QUERY: {
        "title": "🤔 Necesito más detalles",
        "message": "Tu consulta podría referirse a varias cosas. ¿Podrías ser más específico?",
        "suggestion": "Por ejemplo, puedes indicar el nombre del paciente, un rango de fechas, o el tipo de tratamiento.",
    },
    ErrorType.NO_RESULTS: {
        "title": "📭 Sin resultados",
        "message": "No encontré información que coincida con tu búsqueda.",
        "suggestion": "Intenta con otros términos o verifica que el nombre esté escrito correctamente.",
    },
    ErrorType.PERMISSION_DENIED: {
        "title": "🔒 Acceso restringido",
        "message": "No tienes permisos para ver esta información.",
        "suggestion": "Si necesitas acceso, contacta al administrador del sistema.",
    },
    ErrorType.INVALID_ENTITY: {
        "title": "❓ No encontrado",
        "message": "No pude encontrar lo que buscas en el sistema.",
        "suggestion": "Verifica el nombre o identificador. ¿Quizás quisiste decir algo similar?",
    },
    ErrorType.SQL_ERROR: {
        "title": "⚠️ Error procesando la consulta",
        "message": "Hubo un problema al buscar la información.",
        "suggestion": "Intenta reformular tu pregunta de otra manera.",
    },
    ErrorType.VALIDATION_ERROR: {
        "title": "📝 Datos incompletos",
        "message": "Faltan algunos datos necesarios para completar la acción.",
        "suggestion": "Asegúrate de incluir toda la información requerida.",
    },
    ErrorType.TIMEOUT: {
        "title": "⏱️ Tiempo agotado",
        "message": "La búsqueda tardó demasiado tiempo.",
        "suggestion": "Intenta con una consulta más específica o en un momento con menos actividad.",
    },
    ErrorType.RATE_LIMIT: {
        "title": "🚦 Demasiadas solicitudes",
        "message": "Has realizado muchas consultas en poco tiempo.",
        "suggestion": "Espera unos segundos antes de continuar.",
    },
    ErrorType.INTERNAL: {
        "title": "🔧 Error del sistema",
        "message": "Ocurrió un error inesperado.",
        "suggestion": "Por favor intenta de nuevo. Si el problema persiste, contacta soporte.",
    },
}


# =============================================================================
# DATACLASSES AUXILIARES
# =============================================================================

@dataclass
class FuzzyMatch:
    """Resultado de búsqueda difusa para sugerencias."""
    original_term: str
    matched_term: str
    similarity: float  # 0.0 a 1.0
    table: str
    column: str


@dataclass 
class SQLQuery:
    """Consulta SQL generada con metadata."""
    query: str
    params: Dict[str, Any] = field(default_factory=dict)
    target_db: DatabaseTarget = DatabaseTarget.CORE
    is_mutation: bool = False
    tables_involved: List[str] = field(default_factory=list)
    estimated_rows: Optional[int] = None


@dataclass
class ExecutionResult:
    """Resultado de ejecución de consulta."""
    success: bool
    data: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error_message: Optional[str] = None


# =============================================================================
# ESTADO PRINCIPAL DEL AGENTE (TypedDict para LangGraph)
# =============================================================================

class AgentState(TypedDict, total=False):
    """
    Estado que fluye a través del grafo de LangGraph.
    
    Todos los campos son opcionales (total=False) para permitir
    actualizaciones parciales en cada nodo.
    
    NUEVO (Fase 1 - Memoria Episódica):
    - thread_id: Identificador único para checkpointing
    - messages: Lista de mensajes para contexto multi-turno
    - origin: Origen de la conversación (webapp, whatsapp_paciente, whatsapp_user)
    """
    
    # --- Input del usuario ---
    user_query: str                      # Consulta en lenguaje natural
    user_id: int                         # ID del usuario autenticado
    user_role: str                       # Rol: Admin, Podologo, Recepcion
    session_id: str                      # ID de sesión para logging (legacy)
    
    # --- Threading y Persistencia (NUEVO - Fase 1) ---
    thread_id: str                       # ID único para checkpointing
    origin: str                          # Origen: 'webapp', 'whatsapp_paciente', 'whatsapp_user'
    messages: List[Dict[str, str]]       # Historial: [{"role": "user", "content": "..."}]
    
    # --- Clasificación de intención ---
    intent: IntentType                   # Tipo de intención detectada
    intent_confidence: float             # Confianza (0.0 a 1.0)
    entities_extracted: Dict[str, Any]   # Entidades: {paciente: "Juan", fecha: "2024-01-01"}
    
    # --- Generación SQL ---
    target_database: DatabaseTarget      # BD objetivo
    sql_query: SQLQuery                  # Query generada
    sql_is_valid: bool                   # ¿Pasó validación?
    sql_validation_errors: List[str]     # Errores de validación
    
    # --- Ejecución ---
    execution_result: ExecutionResult    # Resultado de la query
    retry_count: int                     # Intentos de reintento
    max_retries: int                     # Máximo de reintentos (default: 2)
    
    # --- Búsqueda difusa ---
    fuzzy_matches: List[FuzzyMatch]      # Coincidencias difusas encontradas
    fuzzy_suggestions: List[str]         # Sugerencias para el usuario
    
    # --- Respuesta ---
    response_text: str                   # Respuesta formateada para el usuario
    response_data: Dict[str, Any]        # Datos estructurados (para UI)
    
    # --- Manejo de errores ---
    error_type: ErrorType                # Tipo de error (si hay)
    error_internal_message: str          # Mensaje técnico (para logs)
    error_user_message: str              # Mensaje amigable (para usuario)
    error_suggestions: List[str]         # Sugerencias de acción
    
    # --- Metadata y logging ---
    started_at: datetime                 # Timestamp inicio
    completed_at: datetime               # Timestamp fin
    node_path: List[str]                 # Nodos visitados en el grafo
    logs: List[Dict[str, Any]]           # Logs internos para debugging


# =============================================================================
# FUNCIONES HELPER PARA ESTADO
# =============================================================================

def create_initial_state(
    user_query: str,
    user_id: int,
    user_role: str,
    session_id: str,
    thread_id: Optional[str] = None,
    origin: str = "webapp"
) -> AgentState:
    """
    Crea el estado inicial para una nueva consulta.
    
    Args:
        user_query: Consulta del usuario en lenguaje natural
        user_id: ID del usuario autenticado
        user_role: Rol del usuario (Admin, Podologo, Recepcion)
        session_id: ID único de la sesión (legacy, usar thread_id)
        thread_id: ID único para checkpointing (NUEVO - Fase 1)
        origin: Origen de la conversación: 'webapp', 'whatsapp_paciente', 'whatsapp_user'
        
    Returns:
        AgentState inicializado con valores por defecto
    """
    return AgentState(
        # Input
        user_query=user_query,
        user_id=user_id,
        user_role=user_role,
        session_id=session_id,
        
        # Threading (NUEVO - Fase 1)
        thread_id=thread_id or session_id,
        origin=origin,
        messages=[{"role": "user", "content": user_query}],
        
        # Defaults
        intent=IntentType.CLARIFICATION,
        intent_confidence=0.0,
        entities_extracted={},
        
        target_database=DatabaseTarget.CORE,
        sql_is_valid=False,
        sql_validation_errors=[],
        
        retry_count=0,
        max_retries=2,
        
        fuzzy_matches=[],
        fuzzy_suggestions=[],
        
        response_text="",
        response_data={},
        
        error_type=ErrorType.NONE,
        error_internal_message="",
        error_user_message="",
        error_suggestions=[],
        
        started_at=datetime.now(timezone.utc),
        node_path=[],
        logs=[],
    )


def format_friendly_error(error_type: ErrorType, context: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Genera un mensaje de error amigable para el usuario.
    
    Args:
        error_type: Tipo de error
        context: Contexto adicional (entidades, sugerencias, etc.)
        
    Returns:
        Dict con title, message, suggestion formateados
    """
    base = FRIENDLY_MESSAGES.get(error_type, FRIENDLY_MESSAGES[ErrorType.INTERNAL])
    result = base.copy()
    
    # Personalizar con contexto si está disponible
    if context:
        if "entity_name" in context:
            result["message"] = result["message"].replace(
                "lo que buscas", 
                f"'{context['entity_name']}'"
            )
        if "alternatives" in context and context["alternatives"]:
            alts = ", ".join(context["alternatives"][:3])
            result["suggestion"] = f"¿Quizás quisiste decir: {alts}?"
            
    return result


def add_log_entry(state: AgentState, node: str, message: str, level: str = "info") -> None:
    """
    Agrega una entrada de log al estado (para debugging interno).
    
    Args:
        state: Estado actual del agente
        node: Nombre del nodo que genera el log
        message: Mensaje del log
        level: Nivel (info, warning, error)
    """
    if "logs" not in state:
        state["logs"] = []
    
    state["logs"].append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node": node,
        "level": level,
        "message": message,
    })
