"""
Workflows - Procesos Determinísticos de PodoSkin
================================================

Este módulo contiene workflows para procesos administrativos y operativos
que siguen flujos predecibles y repetibles.

Workflows disponibles:
- pacientes: CRUD, verificación de duplicados, exportación
- citas: Reserva, disponibilidad, cancelación
- tratamientos: Inicio, actualización, cierre
- evoluciones: Creación de notas SOAP, validación
- finanzas: Procesamiento de pagos, transacciones
- autenticacion: Login, sesiones, permisos
"""

from .base import WorkflowBase, WorkflowResult, WorkflowContext, WorkflowStatus

__all__ = [
    "WorkflowBase",
    "WorkflowResult",
    "WorkflowContext",
    "WorkflowStatus",
]
