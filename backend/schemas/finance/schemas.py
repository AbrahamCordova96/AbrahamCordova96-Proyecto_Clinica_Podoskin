from __future__ import annotations
from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict


class MetodoPagoCreate(BaseModel):
    nombre: str = Field(..., min_length=2)


class MetodoPagoResponse(BaseModel):
    id_metodo: int
    nombre: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class PagoCreate(BaseModel):
    paciente_id: int = Field(..., gt=0)
    total_facturado: Decimal = Field(..., ge=0)
    notas: str | None = None


class PagoResponse(BaseModel):
    id_pago: int
    paciente_id: int
    total_facturado: Decimal
    monto_pagado: Decimal
    saldo_pendiente: Decimal
    status_pago: str
    fecha_emision: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TransaccionCreate(BaseModel):
    # Nota: pago_id NO se incluye aquí porque viene en la URL
    monto: Decimal = Field(..., gt=0)
    metodo_pago_id: int = Field(..., gt=0)
    notas: str | None = None


class TransaccionResponse(BaseModel):
    id_transaccion: int
    pago_id: int
    monto: Decimal
    metodo_pago_id: int
    fecha: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
