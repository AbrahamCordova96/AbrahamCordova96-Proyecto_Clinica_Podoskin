# =============================================================================
# MÓDULO CORE: Modelos para clinica_core_db
# =============================================================================
# Este módulo contiene los modelos SQLAlchemy para el schema "clinic":
#   - Pacientes (expedientes clínicos)
#   - Historial médico general y ginecológico
#   - Tratamientos y evoluciones clínicas
#   - Evidencia fotográfica
#   - Sesiones de IA
# =============================================================================

from backend.schemas.core.models import (
    Base,
    Paciente,
    HistorialMedicoGeneral,
    HistorialGineco,
    Tratamiento,
    EvolucionClinica,
    EvidenciaFotografica,
    SesionIAConversacion,
)

__all__ = [
    "Base",
    "Paciente",
    "HistorialMedicoGeneral",
    "HistorialGineco",
    "Tratamiento",
    "EvolucionClinica",
    "EvidenciaFotografica",
    "SesionIAConversacion",
]
