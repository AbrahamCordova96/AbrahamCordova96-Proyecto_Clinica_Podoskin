# =============================================================================
# MÓDULO FINANCE: Modelos para clinica_ops_db (schema finance)
# =============================================================================
# Este módulo contiene los modelos SQLAlchemy para el schema "finance":
#   - Métodos de pago
#   - Servicios prestados
#   - Pagos y transacciones
#   - Categorías de gasto y proveedores
#   - Gastos
# =============================================================================

from backend.schemas.finance.models import (
    Base,
    MetodoPago,
    ServicioPrestado,
    Pago,
    PagoDetalle,
    Transaccion,
    CategoriaGasto,
    Proveedor,
    Gasto,
)

__all__ = [
    "Base",
    "MetodoPago",
    "ServicioPrestado",
    "Pago",
    "PagoDetalle",
    "Transaccion",
    "CategoriaGasto",
    "Proveedor",
    "Gasto",
]
