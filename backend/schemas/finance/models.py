# =============================================================================
# backend/schemas/finance/models.py
# CLINICA_OPS_DB: Modelos SQLAlchemy para el schema "finance"
# =============================================================================
# Este archivo mapea las tablas financieras de la clínica:
#   - metodos_pago: Formas de pago aceptadas
#   - servicios_prestados: Servicios realizados en cada cita
#   - pagos: Cabecera de factura/recibo
#   - pago_detalles: Qué servicios cubre cada pago
#   - transacciones: Movimientos de caja (entrada de dinero)
#   - categorias_gasto: Tipos de gasto para clasificación
#   - proveedores: Catálogo de proveedores
#   - gastos: Registro de egresos
#
# ANALOGÍA: Si Core es el "expediente médico" y Ops es la "agenda",
# Finance es la "caja registradora y libro de contabilidad".
# =============================================================================

from sqlalchemy import (
    Column, BigInteger, String, Boolean, ForeignKey, Date, Text,
    Integer, Numeric, Computed
)
# TIMESTAMP viene del dialecto PostgreSQL porque TIMESTAMPTZ no existe en el módulo principal
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# =============================================================================
# BASE DECLARATIVA
# =============================================================================
# Finance usa la misma Base que Ops porque están en la misma BD (clinica_ops_db)
# pero en schema diferente (finance vs ops)
Base = declarative_base()


# =============================================================================
# MODELO: MÉTODO DE PAGO
# =============================================================================
# Tabla: finance.metodos_pago
class MetodoPago(Base):
    """
    Catálogo de formas de pago aceptadas.
    
    Ejemplos: Efectivo, Tarjeta Débito, Tarjeta Crédito, Transferencia, Depósito
    
    Analogía: La lista de íconos de pago que ves en la caja de un negocio.
    """
    __tablename__ = "metodos_pago"
    __table_args__ = {"schema": "finance"}
    
    id_metodo = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(Text, nullable=False, unique=True)
    activo = Column(Boolean, default=True)
    
    # ---------- Relaciones ----------
    transacciones = relationship("Transaccion", back_populates="metodo_pago")
    gastos = relationship("Gasto", back_populates="metodo_pago")


# =============================================================================
# MODELO: SERVICIO PRESTADO
# =============================================================================
# Tabla: finance.servicios_prestados
class ServicioPrestado(Base):
    """
    Servicio realizado en una cita específica.
    
    Una cita puede tener MÚLTIPLES servicios prestados.
    Ejemplo: En una cita se hace consulta + limpieza + venta de plantillas.
    
    El subtotal se CALCULA AUTOMÁTICAMENTE por PostgreSQL:
    subtotal = (precio_aplicado × cantidad) - descuento
    
    Analogía: Cada línea del ticket de compra.
    """
    __tablename__ = "servicios_prestados"
    __table_args__ = {"schema": "finance"}
    
    id_servicio_prestado = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # ---------- Referencias ----------
    cita_id = Column(BigInteger)  # FK virtual a ops.citas
    servicio_id = Column(BigInteger)  # FK virtual a ops.catalogo_servicios
    tratamiento_id = Column(BigInteger)  # FK virtual a clinic.tratamientos
    
    # ---------- Datos del servicio ----------
    cantidad = Column(Integer, default=1)
    precio_aplicado = Column(Numeric(10, 2), nullable=False)  # Precio al momento del servicio
    descuento = Column(Numeric(10, 2), default=0)
    
    # Subtotal: columna GENERADA por PostgreSQL (read-only)
    subtotal = Column(Numeric(10, 2), Computed("(precio_aplicado * cantidad) - descuento"))
    
    # Si hay descuento, ¿quién lo autorizó?
    descuento_autorizado_por = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    motivo_descuento = Column(Text)
    
    # Auditoría
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    
    # ---------- Relaciones ----------
    detalles_pago = relationship("PagoDetalle", back_populates="servicio_prestado")


# =============================================================================
# MODELO: PAGO
# =============================================================================
# Tabla: finance.pagos
class Pago(Base):
    """
    Cabecera de factura/recibo.
    
    Representa "el paciente debe X pesos" por servicios recibidos.
    Puede tener múltiples transacciones (pagos parciales/abonos).
    
    Estados:
    - 'Pendiente': Adeudo total, no ha pagado nada
    - 'Parcial': Ha hecho abonos pero no liquida
    - 'Pagado': Liquidado completamente
    - 'Cancelado': Anulado (error, devolución, etc.)
    
    Analogía: La factura o recibo que le das al paciente.
    """
    __tablename__ = "pagos"
    __table_args__ = {"schema": "finance"}
    
    id_pago = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    paciente_id = Column(BigInteger, nullable=False)  # FK virtual a clinic.pacientes
    
    fecha_emision = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Montos
    total_facturado = Column(Numeric(10, 2), nullable=False, default=0)
    monto_pagado = Column(Numeric(10, 2), default=0)
    saldo_pendiente = Column(Numeric(10, 2), default=0)
    
    status_pago = Column(Text, default='Pendiente')
    notas = Column(Text)
    
    # Auditoría
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True))
    
    # ---------- Relaciones ----------
    detalles = relationship("PagoDetalle", back_populates="pago")
    transacciones = relationship("Transaccion", back_populates="pago")


# =============================================================================
# MODELO: PAGO DETALLE
# =============================================================================
# Tabla: finance.pago_detalles
class PagoDetalle(Base):
    """
    Detalle de qué servicios cubre cada pago.
    
    Permite pagos parciales: un pago puede cubrir solo algunos servicios
    de los prestados, y otro pago cubrir el resto.
    
    Analogía: "Este pago de $500 cubre la consulta ($300) y parte de limpieza ($200)"
    """
    __tablename__ = "pago_detalles"
    __table_args__ = {"schema": "finance"}
    
    id_detalle = Column(BigInteger, primary_key=True, autoincrement=True)
    
    pago_id = Column(BigInteger, ForeignKey("finance.pagos.id_pago", ondelete="CASCADE"), nullable=False)
    servicio_prestado_id = Column(BigInteger, ForeignKey("finance.servicios_prestados.id_servicio_prestado"), nullable=False)
    
    monto_aplicado = Column(Numeric(10, 2), nullable=False)  # Cuánto de este pago va a este servicio
    
    # ---------- Relaciones ----------
    pago = relationship("Pago", back_populates="detalles")
    servicio_prestado = relationship("ServicioPrestado", back_populates="detalles_pago")


# =============================================================================
# MODELO: TRANSACCIÓN
# =============================================================================
# Tabla: finance.transacciones
class Transaccion(Base):
    """
    Movimiento real de dinero (entrada de efectivo/transferencia).
    
    Un pago puede tener múltiples transacciones:
    - Paciente debe $1000
    - Abona $500 en efectivo (transacción 1)
    - Abona $500 con tarjeta (transacción 2)
    - Pago liquidado
    
    Analogía: Cada vez que la caja registra entrada de dinero.
    """
    __tablename__ = "transacciones"
    __table_args__ = {"schema": "finance"}
    
    id_transaccion = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    pago_id = Column(BigInteger, ForeignKey("finance.pagos.id_pago"), nullable=False)
    
    monto = Column(Numeric(10, 2), nullable=False)
    metodo_pago_id = Column(BigInteger, ForeignKey("finance.metodos_pago.id_metodo"), nullable=False)
    
    fecha = Column(TIMESTAMP(timezone=True), server_default=func.now())
    recibido_por = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    notas = Column(Text)
    
    fecha_corte = Column(Date, server_default=func.current_date())  # Para cortes de caja
    
    # ---------- Relaciones ----------
    pago = relationship("Pago", back_populates="transacciones")
    metodo_pago = relationship("MetodoPago", back_populates="transacciones")


# =============================================================================
# MODELO: CATEGORÍA DE GASTO
# =============================================================================
# Tabla: finance.categorias_gasto
class CategoriaGasto(Base):
    """
    Tipos de gasto para clasificación y reportes.
    
    Permite categorizar los egresos para saber en qué se gasta:
    Renta, Servicios, Sueldos, Insumos, etc.
    
    También puede indicar si el gasto es recurrente (renta mensual)
    para alertas y proyecciones.
    
    Analogía: Las "pestañas" o "columnas" en un libro contable de gastos.
    """
    __tablename__ = "categorias_gasto"
    __table_args__ = {"schema": "finance"}
    
    id_categoria = Column(BigInteger, primary_key=True, autoincrement=True)
    
    nombre = Column(Text, nullable=False, unique=True)
    descripcion = Column(Text)
    color_hex = Column(Text, default='#6B7280')  # Para gráficas
    
    es_recurrente = Column(Boolean, default=False)
    frecuencia_dias = Column(Integer)  # Cada cuántos días (30=mensual, 15=quincenal)
    
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # ---------- Relaciones ----------
    gastos = relationship("Gasto", back_populates="categoria")
    proveedores = relationship("Proveedor", back_populates="categoria_principal_rel")


# =============================================================================
# MODELO: PROVEEDOR
# =============================================================================
# Tabla: finance.proveedores
class Proveedor(Base):
    """
    Catálogo de proveedores para gastos.
    
    Permite rastrear a quién se le paga y por qué tipo de cosas.
    Útil para negociar mejores precios con proveedores frecuentes.
    
    Analogía: El "directorio telefónico" de a quién le compramos.
    """
    __tablename__ = "proveedores"
    __table_args__ = {"schema": "finance"}
    
    id_proveedor = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    nombre = Column(Text, nullable=False)
    nombre_corto = Column(Text)  # Alias para mostrar en listas
    rfc = Column(Text)
    telefono = Column(Text)
    email = Column(Text)
    direccion = Column(Text)
    
    categoria_principal = Column(BigInteger, ForeignKey("finance.categorias_gasto.id_categoria"))
    notas = Column(Text)
    
    activo = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # ---------- Relaciones ----------
    categoria_principal_rel = relationship("CategoriaGasto", back_populates="proveedores")
    gastos = relationship("Gasto", back_populates="proveedor")


# =============================================================================
# MODELO: GASTO
# =============================================================================
# Tabla: finance.gastos
class Gasto(Base):
    """
    Registro de egresos (salida de dinero).
    
    Complementa el módulo de ingresos (pagos/transacciones).
    Juntos permiten calcular la rentabilidad real de la clínica.
    
    El monto_total se CALCULA AUTOMÁTICAMENTE por PostgreSQL:
    monto_total = monto + iva
    
    Analogía: Cada factura o ticket de compra que la clínica PAGA.
    """
    __tablename__ = "gastos"
    __table_args__ = {"schema": "finance"}
    
    id_gasto = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # Clasificación
    categoria_id = Column(BigInteger, ForeignKey("finance.categorias_gasto.id_categoria"), nullable=False)
    proveedor_id = Column(BigInteger, ForeignKey("finance.proveedores.id_proveedor"))
    
    # Montos
    monto = Column(Numeric(12, 2), nullable=False)
    iva = Column(Numeric(12, 2), default=0)
    
    # Monto total: columna GENERADA por PostgreSQL (read-only)
    monto_total = Column(Numeric(12, 2), Computed("monto + COALESCE(iva, 0)"))
    
    # Forma de pago
    metodo_pago_id = Column(BigInteger, ForeignKey("finance.metodos_pago.id_metodo"))
    referencia_pago = Column(Text)  # Número de transferencia, folio, etc.
    
    # Descripción
    concepto = Column(Text, nullable=False)
    notas = Column(Text)
    comprobante_url = Column(Text)  # Ruta a foto de ticket/factura
    numero_factura = Column(Text)
    
    # Fechas
    fecha_gasto = Column(Date, nullable=False, server_default=func.current_date())
    fecha_pago = Column(Date)  # Puede ser diferente si se paga después
    
    # Recurrencia
    es_pago_recurrente = Column(Boolean, default=False)
    gasto_origen_id = Column(BigInteger, ForeignKey("finance.gastos.id_gasto"))  # Si es copia de otro
    
    status = Column(Text, default='Pagado')  # Pendiente, Pagado, Cancelado
    
    # Auditoría
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))
    
    # ---------- Relaciones ----------
    categoria = relationship("CategoriaGasto", back_populates="gastos")
    proveedor = relationship("Proveedor", back_populates="gastos")
    metodo_pago = relationship("MetodoPago", back_populates="gastos")
