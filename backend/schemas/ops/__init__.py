# =============================================================================
# MÓDULO OPS: Modelos para clinica_ops_db (schema ops)
# =============================================================================
# Este módulo contiene los modelos SQLAlchemy para el schema "ops":
#   - Podólogos (profesionales)
#   - Catálogo de servicios
#   - Solicitudes de prospectos
#   - Citas (agenda)
# =============================================================================

from backend.schemas.ops.models import (
    Base,
    Podologo,
    CatalogoServicio,
    SolicitudProspecto,
    Cita,
)

__all__ = [
    "Base",
    "Podologo",
    "CatalogoServicio",
    "SolicitudProspecto",
    "Cita",
]
