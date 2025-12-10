# backend/schemas/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class ClinicaRead(BaseModel):
    id_clinica: int
    nombre: str
    rfc: Optional[str] = None
    activa: Optional[bool] = True
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class ClinicaCreate(BaseModel):
    nombre: str
    rfc: Optional[str] = None
    activa: Optional[bool] = True

class SysUsuarioCreate(BaseModel):
    nombre_usuario: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    rol: str
    email: Optional[EmailStr] = None
    clinica_id: int  # obligatorio para enlazar a clínica

class SysUsuarioRead(BaseModel):
    id_usuario: int
    nombre_usuario: str
    email: Optional[EmailStr] = None
    rol: str
    activo: bool
    clinica_id: int
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class AuditLogRead(BaseModel):
    id_log: int
    timestamp_accion: Optional[datetime] = None
    tabla_afectada: str
    registro_id: int
    accion: str
    usuario_id: Optional[int] = None
    datos_anteriores: Optional[dict] = None
    datos_nuevos: Optional[dict] = None
    ip_address: Optional[str] = None

    class Config:
        orm_mode = True