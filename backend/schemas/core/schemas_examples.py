from __future__ import annotations
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


class PacienteCreate(BaseModel):
    nombres: str = Field(..., min_length=2, description="Nombres del paciente")
    apellidos: str = Field(..., min_length=2, description="Apellidos del paciente")
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento (debe ser anterior a hoy)")
    sexo: str | None = Field(None, description="'M' o 'F'")
    telefono: str = Field(..., min_length=7, description="Teléfono de contacto")
    email: EmailStr | None = Field(None, description="Email opcional")

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_nacimiento_past(cls, v: date) -> date:
        from datetime import date as _date
        if v >= _date.today():
            raise ValueError("fecha_nacimiento debe ser anterior a la fecha actual")
        return v


class PacienteUpdate(BaseModel):
    nombres: str | None = Field(None, min_length=2)
    apellidos: str | None = Field(None, min_length=2)
    telefono: str | None = Field(None, min_length=7)
    email: EmailStr | None = None
    domicilio: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PacienteResponse(BaseModel):
    id_paciente: int
    nombres: str
    apellidos: str
    fecha_nacimiento: date
    telefono: str | None = None
    email: EmailStr | None = None

    model_config = ConfigDict(from_attributes=True)


class TratamientoCreate(BaseModel):
    paciente_id: int = Field(..., gt=0)
    motivo_consulta_principal: str = Field(..., min_length=3)
    fecha_inicio: date | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fecha_inicio")
    @classmethod
    def fecha_inicio_not_future(cls, v: date | None) -> date | None:
        from datetime import date as _date
        if v is None:
            return v
        if v > _date.today():
            raise ValueError("fecha_inicio no puede ser en el futuro")
        return v
