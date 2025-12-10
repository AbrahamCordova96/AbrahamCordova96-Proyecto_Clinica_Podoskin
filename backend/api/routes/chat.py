"""
Chat Endpoint - API para el agente conversacional
=================================================

Expone el agente LangGraph como endpoint REST.
Requiere autenticación JWT.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario
from backend.agents.graph import run_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat - Agente IA"])


# =============================================================================
# SCHEMAS DE REQUEST/RESPONSE
# =============================================================================

class ChatRequest(BaseModel):
    """Request para enviar mensaje al agente."""
    message: str = Field(..., min_length=1, max_length=1000, description="Consulta en lenguaje natural")
    session_id: Optional[str] = Field(None, description="ID de sesión para continuidad")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Muéstrame las citas de hoy",
                "session_id": "abc-123"
            }
        }


class ChatResponse(BaseModel):
    """Respuesta del agente."""
    success: bool = Field(..., description="Si la consulta se procesó correctamente")
    message: str = Field(..., description="Respuesta formateada para el usuario")
    data: Optional[dict] = Field(None, description="Datos estructurados (para UI)")
    intent: Optional[str] = Field(None, description="Intención detectada")
    session_id: str = Field(..., description="ID de sesión para seguimiento")
    processing_time_ms: float = Field(..., description="Tiempo de procesamiento")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "📅 **Citas de hoy:**\n\n1. María García - 10:00 AM",
                "data": {"row_count": 5},
                "intent": "query_read",
                "session_id": "abc-123",
                "processing_time_ms": 523.5
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
    
    **Requiere autenticación.** Los resultados se filtran según el rol del usuario.
    """,
)
async def chat(
    request: ChatRequest,
    current_user: SysUsuario = Depends(get_current_active_user),
):
    """Endpoint principal del chat con el agente."""
    import time
    start_time = time.time()
    
    logger.info(f"Chat request from user {current_user.id_usuario} ({current_user.rol}): {request.message[:50]}...")
    
    try:
        result = await run_agent(
            user_query=request.message,
            user_id=current_user.id_usuario,
            user_role=current_user.rol,
            session_id=request.session_id,
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            success=result.get("success", False),
            message=result.get("response_text", "No pude procesar tu consulta."),
            data=result.get("response_data"),
            intent=result.get("intent"),
            session_id=result.get("session_id", ""),
            processing_time_ms=round(processing_time, 2),
        )
        
    except Exception as e:
        logger.exception(f"Error en chat endpoint: {e}")
        processing_time = (time.time() - start_time) * 1000
        
        return ChatResponse(
            success=False,
            message="🔧 Ocurrió un error procesando tu consulta. Por favor intenta de nuevo.",
            data=None,
            intent=None,
            session_id=request.session_id or "",
            processing_time_ms=round(processing_time, 2),
        )


@router.get("/health", summary="Estado del agente")
async def chat_health():
    """Health check del agente."""
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


def get_router():
    """Función para obtener el router (compatibilidad)."""
    return router
