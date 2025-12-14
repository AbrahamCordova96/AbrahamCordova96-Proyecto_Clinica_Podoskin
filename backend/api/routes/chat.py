"""
Chat Endpoint - API para el agente conversacional
=================================================

Expone el agente LangGraph como endpoint REST con middleware integrado.
Requiere autenticación JWT.

**NUEVO (Fase 2):**
- Middleware de seguridad (PromptController, Guardrails)
- Observabilidad con LangSmith
- Respuestas con información de escalamiento
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario
from backend.agents.graph import run_agent

# ✅ NUEVO: Importar middleware
from backend.middleware import PromptController, Guardrails, ObservabilityMiddleware

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat - Agente IA"])

# Rate limiter for chat endpoint to protect Anthropic API costs
limiter = Limiter(key_func=get_remote_address)

# ✅ NUEVO: Inicializar middleware
prompt_controller = PromptController()
guardrails = Guardrails()
observability = ObservabilityMiddleware()


# =============================================================================
# SCHEMAS DE REQUEST/RESPONSE
# =============================================================================

class ChatRequest(BaseModel):
    """Request para enviar mensaje al agente."""
    message: str = Field(..., min_length=1, max_length=1000, description="Consulta en lenguaje natural")
    session_id: Optional[str] = Field(None, description="ID de sesión para continuidad (legacy)")
    thread_id: Optional[str] = Field(None, description="ID de hilo para checkpointing (NUEVO - Fase 1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Muéstrame las citas de hoy",
                "session_id": "abc-123",
                "thread_id": "5_webapp_abc-123"
            }
        }


class ChatResponse(BaseModel):
    """Respuesta del agente."""
    success: bool = Field(..., description="Si la consulta se procesó correctamente")
    message: str = Field(..., description="Respuesta formateada para el usuario")
    data: Optional[dict] = Field(None, description="Datos estructurados (para UI)")
    intent: Optional[str] = Field(None, description="Intención detectada")
    session_id: str = Field(..., description="ID de sesión para seguimiento (legacy)")
    thread_id: Optional[str] = Field(None, description="ID de hilo para checkpointing (NUEVO - Fase 1)")
    processing_time_ms: float = Field(..., description="Tiempo de procesamiento")
    # ✅ NUEVO: Campos de middleware
    requires_human_review: bool = Field(False, description="Si requiere revisión humana (Fase 2)")
    escalation_reason: Optional[str] = Field(None, description="Razón de escalamiento (Fase 2)")
    risk_level: Optional[str] = Field(None, description="Nivel de riesgo del prompt (Fase 2)")
    trace_id: Optional[str] = Field(None, description="ID de trace para observabilidad (Fase 2)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "📅 **Citas de hoy:**\n\n1. María García - 10:00 AM",
                "data": {"row_count": 5},
                "intent": "query_read",
                "session_id": "abc-123",
                "thread_id": "5_webapp_abc-123",
                "processing_time_ms": 523.5,
                "requires_human_review": False,
                "escalation_reason": None,
                "risk_level": "safe",
                "trace_id": "trace_123abc"
            }
        }


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post(
    "",
    response_model=ChatResponse,
    summary="Enviar mensaje al agente",
    description="""
    Procesa una consulta en lenguaje natural y devuelve una respuesta.
    
    El agente puede:
    - Buscar pacientes, citas, tratamientos
    - Mostrar estadísticas y conteos
    - Responder preguntas sobre la clínica
    
    **NUEVO (Fase 1 - Memoria Episódica):**
    - Usa thread_id para mantener contexto entre turnos de conversación
    - El frontend debe enviar el mismo thread_id para continuar una conversación
    
    **NUEVO (Fase 2 - Middleware y Guardrails):**
    - Validación y sanitización de prompts
    - Detección automática de riesgos
    - Guardrails para temas clínicos sensibles
    - Escalamiento a humano cuando es necesario
    - Trazabilidad completa con LangSmith
    
    **Rate Limiting:** 30 requests/minute per IP para proteger costos de API de IA.
    
    **Requiere autenticación.** Los resultados se filtran según el rol del usuario.
    """,
)
@limiter.limit("30/minute")  # Rate limit: 30 chat requests per minute per IP
async def chat(
    request: Request,
    chat_request: ChatRequest,
    current_user: SysUsuario = Depends(get_current_active_user),
):
    """
    Endpoint principal del chat con el agente.
    
    NUEVO (Fase 1): Soporta memoria episódica mediante thread_id.
    NUEVO (Fase 2): Integra middleware de seguridad y guardrails.
    """
    import time
    start_time = time.time()
    
    logger.info(
        f"Chat request from user {current_user.id_usuario} ({current_user.rol}): "
        f"{chat_request.message[:50]}... (thread={chat_request.thread_id})"
    )
    
    try:
        # ✅ FASE 2 - PASO 1: Validar y sanitizar prompt
        validation = prompt_controller.validate_and_sanitize(
            chat_request.message,
            current_user.rol
        )
        
        if not validation.is_valid:
            logger.warning(f"Prompt inválido de usuario {current_user.id_usuario}: {validation.warnings}")
            return ChatResponse(
                success=False,
                message="❌ Tu mensaje no pudo ser procesado. Por favor, reformúlalo sin caracteres especiales o comandos.",
                data={"validation_errors": validation.warnings},
                intent=None,
                session_id=chat_request.session_id or "",
                thread_id=chat_request.thread_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                requires_human_review=False,
                risk_level=validation.risk_level.value,
                trace_id=None
            )
        
        # ✅ FASE 2 - PASO 2: Verificar guardrails
        guardrail_decision = guardrails.check(
            validation.sanitized_prompt,
            current_user.rol,
            intent=None,  # Intent aún no clasificado
            context={"user_id": current_user.id_usuario}
        )
        
        if guardrail_decision.should_block:
            logger.warning(
                f"Guardrail bloqueó mensaje de usuario {current_user.id_usuario}: "
                f"{guardrail_decision.reason.value}"
            )
            
            # Registrar en observabilidad
            trace_id = observability.trace_interaction(
                user_id=current_user.id_usuario,
                user_role=current_user.rol,
                user_input=chat_request.message,
                agent_response=guardrail_decision.message,
                intent="blocked_by_guardrail",
                execution_time_ms=round((time.time() - start_time) * 1000, 2),
                metadata={
                    "guardrail_reason": guardrail_decision.reason.value,
                    "blocked": True
                }
            )
            
            return ChatResponse(
                success=False,
                message=guardrail_decision.message,
                data={"blocked_reason": guardrail_decision.reason.value},
                intent="blocked_by_guardrail",
                session_id=chat_request.session_id or "",
                thread_id=chat_request.thread_id,
                processing_time_ms=round((time.time() - start_time) * 1000, 2),
                requires_human_review=guardrail_decision.requires_human,
                escalation_reason=guardrail_decision.escalation_notes,
                risk_level=validation.risk_level.value,
                trace_id=trace_id
            )
        
        # ✅ FASE 2 - PASO 3: Procesar con el agente (usando prompt sanitizado)
        result = await run_agent(
            user_query=validation.sanitized_prompt,  # ✅ Usar prompt sanitizado
            user_id=current_user.id_usuario,
            user_role=current_user.rol,
            session_id=chat_request.session_id,
            thread_id=chat_request.thread_id,
            origin="webapp",
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # ✅ FASE 2 - PASO 4: Registrar en observabilidad
        trace_id = observability.trace_interaction(
            user_id=current_user.id_usuario,
            user_role=current_user.rol,
            user_input=chat_request.message,
            agent_response=result.get("response_text", ""),
            intent=result.get("intent"),
            execution_time_ms=round(processing_time, 2),
            metadata={
                "risk_level": validation.risk_level.value,
                "thread_id": chat_request.thread_id,
                "success": result.get("success", False)
            }
        )
        
        return ChatResponse(
            success=result.get("success", False),
            message=result.get("response_text", "No pude procesar tu consulta."),
            data=result.get("response_data"),
            intent=result.get("intent"),
            session_id=result.get("session_id", ""),
            thread_id=result.get("thread_id"),
            processing_time_ms=round(processing_time, 2),
            requires_human_review=False,  # El agente actual no genera esta flag, pero está preparado
            escalation_reason=None,
            risk_level=validation.risk_level.value,
            trace_id=trace_id
        )
        
    except Exception as e:
        logger.exception(f"Error en chat endpoint: {e}")
        processing_time = (time.time() - start_time) * 1000
        
        # ✅ FASE 2: Registrar error en observabilidad
        observability.log_error(
            error_type="CHAT_ENDPOINT_ERROR",
            error_message=str(e),
            user_id=current_user.id_usuario,
            context={
                "message": chat_request.message[:100],
                "thread_id": chat_request.thread_id
            }
        )
        
        return ChatResponse(
            success=False,
            message="🔧 Ocurrió un error procesando tu consulta. Por favor intenta de nuevo.",
            data=None,
            intent=None,
            session_id=chat_request.session_id or "",
            thread_id=chat_request.thread_id,
            processing_time_ms=round(processing_time, 2),
            requires_human_review=True,
            escalation_reason=f"Error técnico: {str(e)}",
            risk_level="high",
            trace_id=None
        )


@router.get("/health", summary="Estado del agente")
async def chat_health():
    """Health check del agente con información de middleware."""
    try:
        from backend.agents.graph import get_compiled_graph
        from backend.api.core.config import get_settings
        
        settings = get_settings()
        graph = get_compiled_graph()
        
        return {
            "status": "healthy",
            "agent_ready": graph is not None,
            "llm_configured": bool(settings.ANTHROPIC_API_KEY),
            "model": settings.CLAUDE_MODEL,
            # ✅ NUEVO: Estado del middleware
            "middleware": {
                "prompt_controller": "active",
                "guardrails": "active",
                "observability": "active" if observability.enabled else "disabled",
                "langsmith_configured": bool(observability.enabled)
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


@router.get("/capabilities", summary="Capacidades del agente")
async def chat_capabilities():
    """Devuelve las capacidades del agente."""
    return {
        "capabilities": [
            {"category": "Pacientes", "examples": ["Busca al paciente Juan", "¿Cuántos pacientes hay?"]},
            {"category": "Citas", "examples": ["Citas de hoy", "Agenda de mañana"]},
            {"category": "Tratamientos", "examples": ["Tratamientos activos", "Evolución del paciente X"]},
            {"category": "Servicios", "examples": ["Lista de servicios", "Precios"]},
        ],
        "limitations": ["Solo consultas de lectura", "Máximo 100 resultados"]
    }


# ============================================================================
# CATÁLOGO DE COMANDOS DISPONIBLES PARA EL CHATBOT
# ============================================================================
# Este catálogo permite al frontend saber qué comandos puede ejecutar el chatbot.
# Cada comando tiene:
# - id: Identificador único del comando
# - name: Nombre descriptivo para mostrar al usuario
# - description: Descripción de qué hace el comando
# - category: Categoría para organizar (Pacientes, Citas, Tratamientos, etc.)
# - examples: Ejemplos de cómo el usuario puede invocar el comando
# - backend_function: Nombre de la función en el backend que ejecuta el comando
# - endpoint: Endpoint de la API REST asociado
# - method: Método HTTP (GET, POST, PUT, DELETE)
# - params: Parámetros que acepta el comando
# - required_role: Roles que tienen permiso para ejecutar el comando
# - response_format: Tipo de respuesta (list, object, etc.)

COMMAND_CATALOG = [
    {
        "id": "list_appointments_today",
        "name": "Listar citas de hoy",
        "description": "Obtiene todas las citas programadas para el día actual",
        "category": "Citas",
        "examples": [
            "Citas de hoy",
            "¿Qué citas tengo hoy?",
            "Muéstrame la agenda de hoy",
            "¿Cuántas citas hay hoy?"
        ],
        "backend_function": "get_todays_appointments",
        "endpoint": "/citas",
        "method": "GET",
        "params": {"fecha_inicio": "{today}", "fecha_fin": "{today}"},
        "required_role": ["Admin", "Podologo", "Recepcion"],
        "response_format": "list"
    },
    {
        "id": "search_patient",
        "name": "Buscar paciente",
        "description": "Busca pacientes por nombre, apellido o teléfono usando búsqueda difusa",
        "category": "Pacientes",
        "examples": [
            "Busca al paciente Juan",
            "Encuentra a María García",
            "¿Quién es el paciente con teléfono 555-1234?",
            "Pacientes con apellido López"
        ],
        "backend_function": "search_patient",
        "endpoint": "/pacientes",
        "method": "GET",
        "params": {"busqueda": "{query}"},
        "required_role": ["Admin", "Podologo"],
        "response_format": "list"
    },
    {
        "id": "get_active_treatments",
        "name": "Listar tratamientos activos",
        "description": "Obtiene la lista de todos los tratamientos en estado activo",
        "category": "Tratamientos",
        "examples": [
            "Tratamientos activos",
            "¿Qué tratamientos están en curso?",
            "Muéstrame los tratamientos abiertos",
            "Lista de tratamientos sin terminar"
        ],
        "backend_function": "get_active_treatments",
        "endpoint": "/tratamientos",
        "method": "GET",
        "params": {"estado": "activo"},
        "required_role": ["Admin", "Podologo"],
        "response_format": "list"
    },
    {
        "id": "create_patient",
        "name": "Crear nuevo paciente",
        "description": "Registra un nuevo paciente en el sistema con sus datos personales",
        "category": "Pacientes",
        "examples": [
            "Crea un paciente llamado Juan Pérez",
            "Registra un nuevo paciente",
            "Quiero dar de alta un paciente",
            "Agrega al paciente María López con teléfono 555-1234"
        ],
        "backend_function": "create_patient",
        "endpoint": "/pacientes",
        "method": "POST",
        "body_schema": {
            "nombres": {"type": "string", "required": True},
            "apellidos": {"type": "string", "required": True},
            "telefono": {"type": "string", "required": True},
            "email": {"type": "string", "required": False},
            "fecha_nacimiento": {"type": "date", "required": False}
        },
        "required_role": ["Admin", "Podologo"],
        "response_format": "object"
    },
    {
        "id": "schedule_appointment",
        "name": "Agendar cita",
        "description": "Programa una nueva cita para un paciente con un podólogo",
        "category": "Citas",
        "examples": [
            "Agenda una cita",
            "Quiero agendar una cita para mañana",
            "Programa una consulta",
            "Crea una cita para el paciente 123 con el doctor 5"
        ],
        "backend_function": "schedule_appointment",
        "endpoint": "/citas",
        "method": "POST",
        "body_schema": {
            "paciente_id": {"type": "number", "required": True},
            "podologo_id": {"type": "number", "required": True},
            "fecha_hora": {"type": "datetime", "required": True},
            "motivo": {"type": "string", "required": False}
        },
        "required_role": ["Admin", "Podologo", "Recepcion"],
        "response_format": "object"
    },
    {
        "id": "list_services",
        "name": "Listar servicios",
        "description": "Obtiene el catálogo completo de servicios podológicos disponibles",
        "category": "Servicios",
        "examples": [
            "¿Qué servicios ofrecen?",
            "Lista de servicios",
            "Muéstrame los servicios disponibles",
            "Catálogo de servicios"
        ],
        "backend_function": "get_services",
        "endpoint": "/servicios",
        "method": "GET",
        "params": {},
        "required_role": ["Admin", "Podologo", "Recepcion"],
        "response_format": "list"
    },
    {
        "id": "get_patient_history",
        "name": "Ver historial de paciente",
        "description": "Obtiene el historial clínico completo de un paciente incluyendo tratamientos y evoluciones",
        "category": "Pacientes",
        "examples": [
            "Historial del paciente 123",
            "Muéstrame el expediente de Juan",
            "¿Qué tratamientos ha tenido el paciente?",
            "Evoluciones del paciente 45"
        ],
        "backend_function": "get_patient_history",
        "endpoint": "/pacientes/{id}/historial",
        "method": "GET",
        "params": {"paciente_id": "{id}"},
        "required_role": ["Admin", "Podologo"],
        "response_format": "object"
    },
    {
        "id": "get_financial_summary",
        "name": "Resumen financiero",
        "description": "Obtiene un resumen de ingresos, gastos y ganancias en un período",
        "category": "Finanzas",
        "examples": [
            "Resumen financiero de hoy",
            "¿Cuánto ganamos esta semana?",
            "Ingresos y gastos del mes",
            "Balance financiero"
        ],
        "backend_function": "get_financial_summary",
        "endpoint": "/finanzas/resumen",
        "method": "GET",
        "params": {"fecha_inicio": "{start}", "fecha_fin": "{end}"},
        "required_role": ["Admin"],
        "response_format": "object"
    }
]


@router.get("/commands", summary="Catálogo de comandos disponibles")
async def get_command_catalog(
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """
    Devuelve el catálogo completo de comandos disponibles para el chatbot.
    
    Este endpoint es fundamental para que el frontend sepa:
    - Qué comandos puede ejecutar el usuario según su rol
    - Cómo se mapean las consultas en lenguaje natural a endpoints del backend
    - Qué ejemplos mostrar al usuario para guiarlo
    
    **Filtrado por rol:**
    Los comandos se filtran automáticamente según el rol del usuario autenticado.
    Por ejemplo:
    - Admin: Ve todos los comandos (8)
    - Podologo: Ve comandos clínicos pero no financieros (7)
    - Recepcion: Solo ve comandos de agenda y contacto (3)
    
    **Uso típico:**
    1. Frontend llama este endpoint al iniciar el chat
    2. Guarda el catálogo en el estado local
    3. Cuando el usuario escribe, usa los examples para autocompletar
    4. Cuando Gemini genera un function call, mapea a estos comandos
    
    **Respuesta:**
    ```json
    {
        "total": 7,
        "commands": [
            {
                "id": "list_appointments_today",
                "name": "Listar citas de hoy",
                "description": "Obtiene todas las citas...",
                "examples": ["Citas de hoy", "¿Qué citas..."],
                ...
            },
            ...
        ],
        "user_role": "Podologo",
        "user_id": 5
    }
    ```
    """
    # Filtrar comandos según el rol del usuario
    # Solo muestra los comandos donde el rol del usuario está en required_role
    available_commands = [
        cmd for cmd in COMMAND_CATALOG
        if current_user.rol in cmd["required_role"]
    ]
    
    logger.info(f"Usuario {current_user.nombre_usuario} ({current_user.rol}) tiene acceso a {len(available_commands)} comandos")
    
    return {
        "total": len(available_commands),
        "commands": available_commands,
        "user_role": current_user.rol,
        "user_id": current_user.id_usuario
    }


@router.get("/commands/{command_id}", summary="Detalle de un comando específico")
async def get_command_detail(
    command_id: str,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """
    Obtiene el detalle completo de un comando específico.
    
    Este endpoint permite al frontend obtener información detallada
    sobre un comando particular, incluyendo todos sus parámetros y ejemplos.
    
    **Uso típico:**
    - Usuario hace clic en un comando sugerido
    - Frontend llama este endpoint para mostrar detalles y ejemplos
    - Usuario puede ver exactamente cómo usar el comando
    
    **Parámetros:**
    - command_id: ID del comando (ej: "list_appointments_today")
    
    **Errores:**
    - 404: Comando no encontrado
    - 403: Usuario no tiene permiso para este comando
    """
    # Buscar el comando en el catálogo
    command = next(
        (cmd for cmd in COMMAND_CATALOG if cmd["id"] == command_id),
        None
    )
    
    if not command:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comando '{command_id}' no encontrado en el catálogo"
        )
    
    # Verificar que el usuario tenga permisos para este comando
    if current_user.rol not in command["required_role"]:
        logger.warning(f"Usuario {current_user.nombre_usuario} intentó acceder al comando '{command_id}' sin permisos")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes permiso para usar el comando '{command['name']}'"
        )
    
    return command


def get_router():
    """Función para obtener el router (compatibilidad)."""
    return router
