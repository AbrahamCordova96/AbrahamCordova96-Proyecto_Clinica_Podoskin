"""
Guardrails - Reglas de Seguridad y Escalamiento a Humano
========================================================

Sistema de guardrails para decisiones clínicas y acciones sensibles.
Determina cuándo escalar a un humano para revisión.

Basado en las mejores prácticas de LangGraph para agentes médicos.
"""

import logging
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class GuardrailReason(str, Enum):
    """Razones para activar guardrails."""
    CLINICAL_DIAGNOSIS = "clinical_diagnosis"  # Diagnóstico clínico
    TREATMENT_RECOMMENDATION = "treatment_recommendation"  # Recomendación de tratamiento
    MEDICATION_CHANGE = "medication_change"  # Cambio de medicación
    SENSITIVE_DATA = "sensitive_data"  # Datos sensibles
    PERMISSION_ESCALATION = "permission_escalation"  # Escalamiento de permisos
    UNUSUAL_REQUEST = "unusual_request"  # Solicitud inusual
    HIGH_RISK_ACTION = "high_risk_action"  # Acción de alto riesgo


class GuardrailDecision(BaseModel):
    """Decisión del sistema de guardrails."""
    should_block: bool = Field(..., description="Si debe bloquearse la acción")
    requires_human: bool = Field(..., description="Si requiere revisión humana")
    reason: GuardrailReason = Field(..., description="Razón del guardrail")
    message: str = Field(..., description="Mensaje para el usuario")
    escalation_notes: Optional[str] = Field(None, description="Notas para el revisor humano")
    
    class Config:
        json_schema_extra = {
            "example": {
                "should_block": True,
                "requires_human": True,
                "reason": "clinical_diagnosis",
                "message": "Esta consulta requiere revisión de un profesional médico",
                "escalation_notes": "Paciente preguntando sobre diagnóstico específico"
            }
        }


class Guardrails:
    """
    Sistema de guardrails para agentes conversacionales en contexto clínico.
    
    Los guardrails protegen contra:
    - Diagnósticos médicos no supervisados
    - Recomendaciones de tratamiento sin validación
    - Acceso a datos sensibles sin permisos
    - Acciones de alto riesgo
    """
    
    # Keywords que requieren escalamiento
    CLINICAL_KEYWORDS = [
        "diagnóstico",
        "diagnostico",
        "diagnosis",
        "prescribir",
        "prescribe",
        "medicamento",
        "medication",
        "cirugía",
        "surgery",
        "tratamiento farmacológico",
        "pharmaceutical treatment",
    ]
    
    SENSITIVE_KEYWORDS = [
        "contraseña",
        "password",
        "api_key",
        "secret",
        "credit_card",
        "tarjeta de crédito",
    ]
    
    def __init__(self):
        """Inicializar sistema de guardrails."""
        self.logger = logging.getLogger(f"{__name__}.Guardrails")
    
    def check(
        self,
        user_input: str,
        user_role: str,
        intent: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> GuardrailDecision:
        """
        Verificar si una solicitud debe bloquearse o escalar a humano.
        
        Args:
            user_input: Input del usuario
            user_role: Rol del usuario (Admin, Podologo, Recepcion)
            intent: Intención clasificada (opcional)
            context: Contexto adicional
            
        Returns:
            GuardrailDecision con la decisión del guardrail
        """
        user_input_lower = user_input.lower()
        
        # 1. Verificar keywords clínicas
        for keyword in self.CLINICAL_KEYWORDS:
            if keyword in user_input_lower:
                # Solo Admins y Podólogos pueden hacer consultas clínicas
                if user_role not in ["Admin", "Podologo"]:
                    return GuardrailDecision(
                        should_block=True,
                        requires_human=True,
                        reason=GuardrailReason.PERMISSION_ESCALATION,
                        message="Esta consulta clínica requiere un profesional autorizado.",
                        escalation_notes=f"Usuario con rol {user_role} intentó consulta clínica"
                    )
                
                # Incluso para profesionales, ciertas acciones requieren confirmación
                if any(word in user_input_lower for word in ["prescribir", "prescribe", "diagnosticar"]):
                    return GuardrailDecision(
                        should_block=False,
                        requires_human=True,
                        reason=GuardrailReason.CLINICAL_DIAGNOSIS,
                        message="Esta acción requiere confirmación de un profesional médico. ¿Desea continuar?",
                        escalation_notes="Solicitud de diagnóstico/prescripción"
                    )
        
        # 2. Verificar keywords sensibles
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in user_input_lower:
                self.logger.warning(f"Keyword sensible detectada: {keyword}")
                return GuardrailDecision(
                    should_block=True,
                    requires_human=False,
                    reason=GuardrailReason.SENSITIVE_DATA,
                    message="No puedo procesar consultas sobre información sensible como contraseñas.",
                    escalation_notes=f"Intento de acceso a dato sensible: {keyword}"
                )
        
        # 3. Verificar intención si está disponible
        if intent:
            if intent in ["write", "delete", "modify"]:
                # Acciones de escritura siempre requieren confirmación
                if user_role == "Recepcion":
                    return GuardrailDecision(
                        should_block=True,
                        requires_human=True,
                        reason=GuardrailReason.PERMISSION_ESCALATION,
                        message="No tienes permisos para realizar esta acción.",
                        escalation_notes=f"Recepcionista intentó acción de {intent}"
                    )
        
        # 4. Pasar todas las validaciones
        return GuardrailDecision(
            should_block=False,
            requires_human=False,
            reason=GuardrailReason.CLINICAL_DIAGNOSIS,  # placeholder
            message="Solicitud válida",
            escalation_notes=None
        )
    
    def check_tool_call(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        user_role: str
    ) -> GuardrailDecision:
        """
        Verificar si una llamada a tool debe permitirse.
        
        Args:
            tool_name: Nombre de la herramienta
            tool_args: Argumentos de la herramienta
            user_role: Rol del usuario
            
        Returns:
            GuardrailDecision
        """
        # Tools de escritura/eliminación requieren permisos especiales
        write_tools = ["create_patient", "update_patient", "delete_patient", "create_treatment"]
        
        if tool_name in write_tools and user_role == "Recepcion":
            return GuardrailDecision(
                should_block=True,
                requires_human=True,
                reason=GuardrailReason.PERMISSION_ESCALATION,
                message=f"No tienes permisos para ejecutar la herramienta: {tool_name}",
                escalation_notes=f"Recepcionista intentó usar tool de escritura: {tool_name}"
            )
        
        # Tool call válido
        return GuardrailDecision(
            should_block=False,
            requires_human=False,
            reason=GuardrailReason.CLINICAL_DIAGNOSIS,  # placeholder
            message="Tool call válido",
            escalation_notes=None
        )
