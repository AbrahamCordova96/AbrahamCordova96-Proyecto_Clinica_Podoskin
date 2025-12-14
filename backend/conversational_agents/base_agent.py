"""
Base Conversational Agent - Clase base para agentes conversacionales
====================================================================

Define la estructura común para agentes con criterio controlado.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid

from backend.middleware import PromptController, Guardrails, ObservabilityMiddleware

logger = logging.getLogger(__name__)


class AgentRole(str, Enum):
    """Roles de agentes conversacionales."""
    CLINICAL_ASSISTANT = "clinical_assistant"  # Asistente clínico
    GENERAL_ASSISTANT = "general_assistant"  # Asistente general
    EVOLUTION_ASSISTANT = "evolution_assistant"  # Asistente de evoluciones


class AgentResponse(BaseModel):
    """Respuesta de un agente conversacional."""
    success: bool = Field(..., description="Si la respuesta fue exitosa")
    message: str = Field(..., description="Mensaje para el usuario")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos estructurados")
    requires_human_review: bool = Field(False, description="Si requiere revisión humana")
    escalation_reason: Optional[str] = Field(None, description="Razón de escalamiento")
    conversation_id: str = Field(..., description="ID de conversación")
    trace_id: Optional[str] = Field(None, description="ID de trace para observabilidad")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "Encontré 5 citas para mañana.",
                "data": {"count": 5, "appointments": []},
                "requires_human_review": False,
                "escalation_reason": None,
                "conversation_id": "conv_123",
                "trace_id": "trace_456"
            }
        }


class ConversationalAgentBase:
    """
    Clase base para agentes conversacionales.
    
    Los agentes conversacionales:
    - Mantienen conversación natural
    - Toman decisiones dentro de guardrails
    - Escalan a humanos cuando es necesario
    - Son observables y auditables
    """
    
    def __init__(
        self,
        role: AgentRole,
        personality: str,
        user_id: int,
        user_role: str,
        conversation_id: Optional[str] = None
    ):
        """
        Inicializar agente conversacional.
        
        Args:
            role: Rol del agente
            personality: Descripción de la personalidad del agente
            user_id: ID del usuario
            user_role: Rol del usuario (Admin, Podologo, Recepcion)
            conversation_id: ID de conversación para continuidad
        """
        self.role = role
        self.personality = personality
        self.user_id = user_id
        self.user_role = user_role
        self.conversation_id = conversation_id or str(uuid.uuid4())  # ✅ Usar UUID para unicidad
        
        # Inicializar middlewares
        self.prompt_controller = PromptController()
        self.guardrails = Guardrails()
        self.observability = ObservabilityMiddleware()
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.conversation_history: List[Dict[str, str]] = []
    
    async def process(
        self,
        user_input: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Procesar input del usuario con todos los controles.
        
        Este es el método principal que orquesta:
        1. Validación de prompt
        2. Verificación de guardrails
        3. Procesamiento del agente
        4. Observabilidad
        
        Args:
            user_input: Input del usuario
            context: Contexto adicional
            
        Returns:
            AgentResponse con la respuesta del agente
        """
        start_ms = datetime.now().timestamp() * 1000
        
        try:
            # 1. Validar y sanitizar prompt
            validation = self.prompt_controller.validate_and_sanitize(
                user_input,
                self.user_role
            )
            
            if not validation.is_valid:
                return AgentResponse(
                    success=False,
                    message="Tu mensaje no pudo ser procesado. Por favor, reformúlalo.",
                    data={"errors": validation.warnings},
                    requires_human_review=False,
                    conversation_id=self.conversation_id
                )
            
            # 2. Verificar guardrails
            guardrail_decision = self.guardrails.check(
                validation.sanitized_prompt,
                self.user_role,
                context=context
            )
            
            if guardrail_decision.should_block:
                return AgentResponse(
                    success=False,
                    message=guardrail_decision.message,
                    requires_human_review=guardrail_decision.requires_human,
                    escalation_reason=guardrail_decision.escalation_notes,
                    conversation_id=self.conversation_id
                )
            
            # 3. Procesar con el agente específico
            response = await self._process_agent_logic(
                validation.sanitized_prompt,
                context
            )
            
            # 4. Agregar al historial
            self.conversation_history.append({
                "role": "user",
                "content": user_input,
                "timestamp": datetime.now().isoformat()
            })
            self.conversation_history.append({
                "role": "assistant",
                "content": response.message,
                "timestamp": datetime.now().isoformat()
            })
            
            # 5. Registrar en observabilidad
            execution_time = (datetime.now().timestamp() * 1000) - start_ms
            trace_id = self.observability.trace_interaction(
                user_id=self.user_id,
                user_role=self.user_role,
                user_input=user_input,
                agent_response=response.message,
                execution_time_ms=execution_time,
                metadata={
                    "agent_role": self.role.value,
                    "requires_review": response.requires_human_review
                }
            )
            response.trace_id = trace_id
            
            return response
            
        except Exception as e:
            self.logger.error(f"Error procesando input: {str(e)}", exc_info=True)
            
            # Registrar error
            self.observability.log_error(
                error_type="AGENT_PROCESSING_ERROR",
                error_message=str(e),
                user_id=self.user_id,
                context={"user_input": user_input}
            )
            
            return AgentResponse(
                success=False,
                message="Ocurrió un error procesando tu solicitud. Por favor, inténtalo de nuevo.",
                requires_human_review=True,
                escalation_reason=f"Error técnico: {str(e)}",
                conversation_id=self.conversation_id
            )
    
    async def _process_agent_logic(
        self,
        sanitized_input: str,
        context: Optional[Dict[str, Any]]
    ) -> AgentResponse:
        """
        Lógica específica del agente a implementar en subclases.
        
        Args:
            sanitized_input: Input sanitizado
            context: Contexto adicional
            
        Returns:
            AgentResponse
        """
        raise NotImplementedError("Subclases deben implementar _process_agent_logic")
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Obtener historial de conversación."""
        return self.conversation_history
    
    def clear_history(self) -> None:
        """Limpiar historial de conversación."""
        self.conversation_history = []
