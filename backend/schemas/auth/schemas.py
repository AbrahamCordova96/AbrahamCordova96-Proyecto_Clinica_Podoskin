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
        from_attributes = True

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
        from_attributes = True

class AuditLogRead(BaseModel):
    id_log: int
    timestamp_accion: Optional[datetime] = None
    tabla_afectada: str
    registro_id: Optional[int] = None
    accion: str
    usuario_id: Optional[int] = None
    username: Optional[str] = None
    session_id: Optional[str] = None
    datos_anteriores: Optional[dict] = None
    datos_nuevos: Optional[dict] = None
    ip_address: Optional[str] = None
    method: Optional[str] = None
    endpoint: Optional[str] = None
    request_body: Optional[str] = None
    response_hash: Optional[str] = None
    source_refs: Optional[list] = None
    note: Optional[str] = None

    class Config:
        from_attributes = True


class VoiceTranscriptCreate(BaseModel):
    """Schema for creating voice transcript entries"""
    session_id: str
    user_text: str
    assistant_text: Optional[str] = None
    timestamp: str  # ISO-8601 format
    langgraph_job_id: Optional[str] = None


class VoiceTranscriptRead(BaseModel):
    """Schema for reading voice transcript entries"""
    id_transcript: int
    session_id: str
    user_id: int
    user_text: str
    assistant_text: Optional[str] = None
    timestamp: datetime
    langgraph_job_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# SCHEMAS PARA API KEY DE GEMINI
# ============================================================================

class GeminiKeyUpdate(BaseModel):
    """
    Request para actualizar la API Key de Gemini de un usuario.
    
    La API Key debe tener:
    - Mínimo 20 caracteres (las keys de Google suelen tener ~40)
    - Máximo 200 caracteres (por seguridad)
    - Formato: Comienza con "AIza" generalmente
    
    El backend validará la key contra la API de Google antes de guardarla.
    """
    api_key: str = Field(
        ..., 
        min_length=20, 
        max_length=200,
        description="API Key de Google Gemini"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "api_key": "AIzaSyC1234567890abcdefghijklmnopqrstuv"
            }
        }


class GeminiKeyStatus(BaseModel):
    """
    Response con el estado de la API Key de Gemini de un usuario.
    
    Campos:
    - has_key: Si el usuario tiene una API Key configurada
    - is_valid: Si la API Key es válida (null si no hay key)
    - last_updated: Cuándo se actualizó por última vez
    - last_validated: Cuándo se validó exitosamente por última vez
    
    Estados posibles:
    - has_key=False: Usuario nunca ha configurado una API Key
    - has_key=True, is_valid=True: API Key configurada y funcionando
    - has_key=True, is_valid=False: API Key configurada pero inválida/expirada
    """
    has_key: bool = Field(..., description="Si el usuario tiene API Key configurada")
    is_valid: Optional[bool] = Field(None, description="Si la API Key es válida (solo si has_key=True)")
    last_updated: Optional[datetime] = Field(None, description="Última actualización")
    last_validated: Optional[datetime] = Field(None, description="Última validación exitosa")
    
    class Config:
        json_schema_extra = {
            "example": {
                "has_key": True,
                "is_valid": True,
                "last_updated": "2024-12-12T10:30:00Z",
                "last_validated": "2024-12-12T10:30:00Z"
            }
        }