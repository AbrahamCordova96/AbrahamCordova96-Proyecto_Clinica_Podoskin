"""
Observability Middleware - Integración con LangSmith
====================================================

Middleware para observabilidad y trazabilidad de interacciones del agente.
Integra con LangSmith para logging, métricas y debugging.

Basado en:
https://docs.langsmith.dev/observability
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ObservabilityMiddleware:
    """
    Middleware para observabilidad con LangSmith.
    
    Registra todas las interacciones del agente para:
    - Debugging
    - Análisis de rendimiento
    - Evaluaciones
    - Auditoría
    """
    
    def __init__(self, enabled: bool = True):
        """
        Inicializar middleware de observabilidad.
        
        Args:
            enabled: Si está habilitado (requiere LANGSMITH_API_KEY en env)
        """
        self.enabled = enabled and bool(os.getenv("LANGSMITH_API_KEY"))
        self.logger = logging.getLogger(f"{__name__}.ObservabilityMiddleware")
        
        if self.enabled:
            self.logger.info("✅ Observabilidad con LangSmith habilitada")
        else:
            self.logger.info("⚠️  Observabilidad deshabilitada (LANGSMITH_API_KEY no configurado)")
    
    def trace_interaction(
        self,
        user_id: int,
        user_role: str,
        user_input: str,
        agent_response: str,
        intent: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Registrar una interacción completa para trazabilidad.
        
        Args:
            user_id: ID del usuario
            user_role: Rol del usuario
            user_input: Input del usuario
            agent_response: Respuesta del agente
            intent: Intención clasificada
            execution_time_ms: Tiempo de ejecución
            metadata: Metadatos adicionales
            
        Returns:
            Trace ID para referencia
        """
        trace_id = str(uuid.uuid4())
        
        if not self.enabled:
            # Solo logging local si LangSmith no está disponible
            self.logger.info(
                f"TRACE {trace_id}: user={user_id}, role={user_role}, "
                f"intent={intent}, time={execution_time_ms}ms"
            )
            return trace_id
        
        # Aquí iría la integración real con LangSmith
        # Por ahora, solo logging estructurado
        log_entry = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "user_role": user_role,
            "user_input": user_input[:100],  # Truncar para logging
            "agent_response": agent_response[:100],  # Truncar
            "intent": intent,
            "execution_time_ms": execution_time_ms,
            "metadata": metadata or {}
        }
        
        self.logger.info(f"LANGSMITH_TRACE: {log_entry}")
        
        return trace_id
    
    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: int,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registrar un error para análisis.
        
        Args:
            error_type: Tipo de error
            error_message: Mensaje de error
            user_id: ID del usuario
            context: Contexto adicional
        """
        error_entry = {
            "error_type": error_type,
            "error_message": error_message,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.logger.error(f"LANGSMITH_ERROR: {error_entry}")
    
    def log_metric(
        self,
        metric_name: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registrar una métrica para monitoreo.
        
        Args:
            metric_name: Nombre de la métrica
            metric_value: Valor de la métrica
            metadata: Metadatos adicionales
        """
        metric_entry = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        self.logger.info(f"LANGSMITH_METRIC: {metric_entry}")
