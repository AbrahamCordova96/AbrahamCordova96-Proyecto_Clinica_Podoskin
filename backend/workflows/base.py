"""
Base Workflow - Clase base para todos los workflows
===================================================

Define la estructura común para workflows determinísticos.
"""

from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Estados posibles de un workflow."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"
    CANCELLED = "cancelled"


class WorkflowContext(BaseModel):
    """Contexto de ejecución de un workflow."""
    user_id: int = Field(..., description="ID del usuario que ejecuta el workflow")
    user_role: str = Field(..., description="Rol del usuario (Admin, Podologo, Recepcion)")
    clinica_id: int = Field(..., description="ID de la clínica")
    session_id: Optional[str] = Field(None, description="ID de sesión para tracking")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")


class WorkflowResult(BaseModel):
    """Resultado de la ejecución de un workflow."""
    status: WorkflowStatus = Field(..., description="Estado final del workflow")
    success: bool = Field(..., description="Si el workflow se completó exitosamente")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    data: Optional[Dict[str, Any]] = Field(None, description="Datos resultantes")
    errors: List[str] = Field(default_factory=list, description="Lista de errores encontrados")
    warnings: List[str] = Field(default_factory=list, description="Lista de advertencias")
    execution_time_ms: float = Field(..., description="Tiempo de ejecución en milisegundos")
    requires_human_approval: bool = Field(False, description="Si requiere aprobación humana")
    approval_reason: Optional[str] = Field(None, description="Razón de aprobación requerida")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "success": True,
                "message": "Paciente creado exitosamente",
                "data": {"id_paciente": 123, "codigo_interno": "EZJU-1213-00123"},
                "errors": [],
                "warnings": ["El paciente tiene un teléfono similar a otro registro"],
                "execution_time_ms": 245.3,
                "requires_human_approval": False
            }
        }


class WorkflowBase:
    """
    Clase base para todos los workflows.
    
    Los workflows son procesos determinísticos que ejecutan pasos
    predecibles y repetibles. A diferencia de los agentes, los workflows
    no toman decisiones autónomas sino que siguen reglas definidas.
    """
    
    def __init__(self, context: WorkflowContext):
        """
        Inicializar workflow con contexto.
        
        Args:
            context: Contexto de ejecución con información del usuario y sesión
        """
        self.context = context
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.start_time = datetime.now()
    
    async def validate_permissions(self) -> bool:
        """
        Validar que el usuario tenga permisos para ejecutar este workflow.
        
        Returns:
            True si tiene permisos, False si no
        """
        # Implementar en subclases
        return True
    
    async def validate_input(self, **kwargs) -> tuple[bool, List[str]]:
        """
        Validar datos de entrada del workflow.
        
        Args:
            **kwargs: Parámetros de entrada del workflow
            
        Returns:
            Tuple de (es_válido, lista_de_errores)
        """
        # Implementar en subclases
        return True, []
    
    async def execute(self, **kwargs) -> WorkflowResult:
        """
        Ejecutar el workflow completo.
        
        Este es el método principal que orquesta todos los pasos.
        
        Args:
            **kwargs: Parámetros de entrada del workflow
            
        Returns:
            WorkflowResult con el resultado de la ejecución
        """
        start_ms = datetime.now().timestamp() * 1000
        
        try:
            # 1. Validar permisos
            if not await self.validate_permissions():
                return WorkflowResult(
                    status=WorkflowStatus.FAILED,
                    success=False,
                    message="Permisos insuficientes para ejecutar este workflow",
                    errors=["PERMISSION_DENIED"],
                    execution_time_ms=(datetime.now().timestamp() * 1000) - start_ms
                )
            
            # 2. Validar entrada
            is_valid, errors = await self.validate_input(**kwargs)
            if not is_valid:
                return WorkflowResult(
                    status=WorkflowStatus.FAILED,
                    success=False,
                    message="Datos de entrada inválidos",
                    errors=errors,
                    execution_time_ms=(datetime.now().timestamp() * 1000) - start_ms
                )
            
            # 3. Ejecutar lógica específica del workflow
            result = await self._execute_workflow(**kwargs)
            
            # 4. Calcular tiempo de ejecución
            result.execution_time_ms = (datetime.now().timestamp() * 1000) - start_ms
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error ejecutando workflow: {str(e)}", exc_info=True)
            return WorkflowResult(
                status=WorkflowStatus.FAILED,
                success=False,
                message=f"Error inesperado: {str(e)}",
                errors=[str(e)],
                execution_time_ms=(datetime.now().timestamp() * 1000) - start_ms
            )
    
    async def _execute_workflow(self, **kwargs) -> WorkflowResult:
        """
        Lógica específica del workflow a implementar en subclases.
        
        Args:
            **kwargs: Parámetros de entrada del workflow
            
        Returns:
            WorkflowResult con el resultado
        """
        raise NotImplementedError("Subclases deben implementar _execute_workflow")
    
    async def rollback(self, **kwargs) -> bool:
        """
        Revertir cambios en caso de error.
        
        Args:
            **kwargs: Parámetros necesarios para el rollback
            
        Returns:
            True si el rollback fue exitoso, False si no
        """
        # Implementar en subclases si es necesario
        return True
    
    def log_audit(self, action: str, details: Dict[str, Any]) -> None:
        """
        Registrar acción en el log de auditoría.
        
        Args:
            action: Acción realizada
            details: Detalles de la acción
        """
        self.logger.info(
            f"AUDIT: {action}",
            extra={
                "user_id": self.context.user_id,
                "user_role": self.context.user_role,
                "clinica_id": self.context.clinica_id,
                "session_id": self.context.session_id,
                "action": action,
                "details": details,
            }
        )
