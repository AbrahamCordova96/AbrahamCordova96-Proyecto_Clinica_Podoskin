# =============================================================================
# backend/schemas/core/schemas.py
# Schemas Pydantic para validación de datos de entrada/salida (API)
# =============================================================================
# Los schemas Pydantic son diferentes de los modelos SQLAlchemy:
#   - SQLAlchemy models: definen cómo se GUARDAN los datos en la BD
#   - Pydantic schemas: definen cómo se VALIDAN los datos en la API
#
# Analogía: SQLAlchemy es el formato del expediente físico en el archivo.
#           Pydantic es la recepcionista que verifica que el formulario
#           esté bien llenado ANTES de guardarlo.
# =============================================================================

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, Field, EmailStr, field_validator, ConfigDict


# =============================================================================
# SCHEMAS DE ALERGIA
# =============================================================================

class AlergiaBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre de la alergia")
    tipo: Optional[str] = None
    observaciones: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AlergiaCreate(AlergiaBase):
    id_historial: int

class AlergiaUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo: Optional[str] = None
    observaciones: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AlergiaResponse(AlergiaBase):
    id_alergia: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SCHEMAS DE SUPLEMENTO
# =============================================================================

class SuplementoBase(BaseModel):
    nombre: str = Field(..., min_length=1, description="Nombre del suplemento")
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SuplementoCreate(SuplementoBase):
    id_historial: int

class SuplementoUpdate(BaseModel):
    nombre: Optional[str] = None
    dosis: Optional[str] = None
    frecuencia: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class SuplementoResponse(SuplementoBase):
    id_suplemento: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SCHEMAS DE ANTECEDENTE NO PATOLÓGICO
# =============================================================================

class AntecedenteNoPatologicoBase(BaseModel):
    descripcion: str = Field(..., min_length=1, description="Descripción del antecedente")
    tipo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AntecedenteNoPatologicoCreate(AntecedenteNoPatologicoBase):
    id_historial: int

class AntecedenteNoPatologicoUpdate(BaseModel):
    descripcion: Optional[str] = None
    tipo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class AntecedenteNoPatologicoResponse(AntecedenteNoPatologicoBase):
    id_antnp: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SCHEMAS DE CONVERSACIÓN PRESENCIAL
# =============================================================================

class ConversacionPresencialBase(BaseModel):
    fecha: Optional[datetime] = None
    usuario: Optional[str] = None
    mensaje: str = Field(..., min_length=1, description="Contenido de la conversación")
    tipo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ConversacionPresencialCreate(ConversacionPresencialBase):
    id_paciente: int

class ConversacionPresencialUpdate(BaseModel):
    mensaje: Optional[str] = None
    tipo: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class ConversacionPresencialResponse(ConversacionPresencialBase):
    id_conversacion: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SCHEMAS DE CONVERSACIÓN DIGITAL
# =============================================================================

class ConversacionDigitalBase(BaseModel):
    canal: str = Field(..., description="Canal: whatsapp, web, email, llamada, etc.")
    remitente: Optional[str] = None
    mensaje: str = Field(..., min_length=1, description="Contenido del mensaje")
    url_adjunto: Optional[str] = None
    leido: bool = False
    model_config = ConfigDict(from_attributes=True)

class ConversacionDigitalCreate(ConversacionDigitalBase):
    id_paciente: int

class ConversacionDigitalUpdate(BaseModel):
    mensaje: Optional[str] = None
    leido: Optional[bool] = None
    model_config = ConfigDict(from_attributes=True)

class ConversacionDigitalResponse(ConversacionDigitalBase):
    id_conversacion: int
    fecha: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# =============================================================================
# SCHEMAS DE PACIENTE
# =============================================================================

class PacienteBase(BaseModel):
    """
    Campos base compartidos entre crear y leer pacientes.
    """
    nombres: str = Field(..., min_length=2, max_length=100, description="Nombre(s) del paciente")
    apellidos: str = Field(..., min_length=2, max_length=100, description="Apellido(s) del paciente")
    fecha_nacimiento: date = Field(..., description="Fecha de nacimiento")
    sexo: Optional[str] = Field(None, pattern="^[MF]$", description="Sexo: M o F")
    
    # Sociodemográficos (opcionales)
    estado_civil: Optional[str] = None
    ocupacion: Optional[str] = None
    escolaridad: Optional[str] = None
    religion: Optional[str] = None
    domicilio: Optional[str] = None
    como_supo_de_nosotros: Optional[str] = None
    
    # Contacto
    telefono: str = Field(..., min_length=10, description="Teléfono (mínimo 10 dígitos)")
    email: Optional[EmailStr] = None


class PacienteCreate(PacienteBase):
    """
    Schema para CREAR un paciente nuevo.
    Solo incluye campos que el usuario proporciona.
    """
    pass


class PacienteUpdate(BaseModel):
    """
    Schema para ACTUALIZAR un paciente.
    Todos los campos son opcionales (solo se actualizan los enviados).
    """
    nombres: Optional[str] = Field(None, min_length=2, max_length=100)
    apellidos: Optional[str] = Field(None, min_length=2, max_length=100)
    fecha_nacimiento: Optional[date] = None
    sexo: Optional[str] = Field(None, pattern="^[MF]$")
    estado_civil: Optional[str] = None
    ocupacion: Optional[str] = None
    escolaridad: Optional[str] = None
    religion: Optional[str] = None
    domicilio: Optional[str] = None
    como_supo_de_nosotros: Optional[str] = None
    telefono: Optional[str] = Field(None, min_length=10)
    email: Optional[EmailStr] = None


class PacienteRead(PacienteBase):
    """
    Schema para LEER un paciente (respuesta de API).
    Incluye campos generados por la BD.
    """
    id_paciente: int
    id_clinica: int = 1
    fecha_registro: datetime
    created_by: Optional[int] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Permite crear desde objetos SQLAlchemy


# =============================================================================
# SCHEMAS DE HISTORIAL MÉDICO GENERAL
# =============================================================================

class HistorialMedicoBase(BaseModel):
    """
    Antecedentes médicos del paciente.
    """
    peso_kg: Optional[Decimal] = Field(None, gt=0, lt=300, description="Peso en kg")
    talla_cm: Optional[Decimal] = Field(None, gt=0, lt=250, description="Talla en cm")
    tipos_sangre: Optional[str] = Field(None, pattern="^(A|B|AB|O)[+-]$")
    
    # Antecedentes heredofamiliares
    ahf_diabetes: bool = False
    ahf_hipertension: bool = False
    ahf_cancer: bool = False
    ahf_cardiacas: bool = False
    ahf_detalles: Optional[str] = None
    
    # Antecedentes personales
    app_diabetes: bool = False
    app_diabetes_inicio: Optional[date] = None
    app_hipertension: bool = False
    app_otras_patologias: Optional[str] = None
    
    # Alergias
    alergias_activas: bool = False
    lista_alergias: Optional[str] = None
    
    # Hábitos
    tabaquismo: bool = False
    alcoholismo: bool = False
    actividad_fisica: Optional[str] = None


class HistorialMedicoCreate(HistorialMedicoBase):
    """Para crear historial médico."""
    paciente_id: int


class HistorialMedicoRead(HistorialMedicoBase):
    """
    Para leer historial médico.
    Incluye IMC calculado (read-only desde BD).
    """
    id_historial: int
    paciente_id: int
    imc: Optional[Decimal] = None  # Calculado por PostgreSQL
    
    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE HISTORIAL GINECOLÓGICO
# =============================================================================

class HistorialGinecoBase(BaseModel):
    """Historial gineco-obstétrico."""
    menarca_edad: Optional[int] = Field(None, ge=9, le=18)
    ritmo_menstrual: Optional[str] = None
    fecha_ultima_menstruacion: Optional[date] = None
    
    # Fórmula obstétrica
    gestas: int = 0
    partos: int = 0
    cesareas: int = 0
    abortos: int = 0
    embarazos_ectopicos: int = 0
    embarazos_multiples: int = 0
    
    anticonceptivos_actuales: Optional[str] = None


class HistorialGinecoCreate(HistorialGinecoBase):
    paciente_id: int


class HistorialGinecoRead(HistorialGinecoBase):
    id_gineco: int
    paciente_id: int
    
    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE TRATAMIENTO
# =============================================================================

class TratamientoBase(BaseModel):
    """Carpeta de tratamiento."""
    motivo_consulta_principal: str = Field(..., min_length=3)
    diagnostico_inicial: Optional[str] = None
    fecha_inicio: Optional[date] = None
    estado_tratamiento: str = Field(
        default="En Curso",
        pattern="^(En Curso|Alta|Pausado|Abandonado)$"
    )
    plan_general: Optional[str] = None


class TratamientoCreate(TratamientoBase):
    paciente_id: int


class TratamientoUpdate(BaseModel):
    motivo_consulta_principal: Optional[str] = None
    diagnostico_inicial: Optional[str] = None
    estado_tratamiento: Optional[str] = Field(
        None, pattern="^(En Curso|Alta|Pausado|Abandonado)$"
    )
    plan_general: Optional[str] = None


class TratamientoRead(TratamientoBase):
    id_tratamiento: int
    paciente_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE EVOLUCIÓN CLÍNICA (NOTAS SOAP)
# =============================================================================

class SignosVitales(BaseModel):
    """
    Estructura de signos vitales dentro de evolución.
    Validamos rangos fisiológicos normales.
    """
    presion_arterial: Optional[str] = Field(None, pattern=r"^\d{2,3}/\d{2,3}$")
    frecuencia_cardiaca: Optional[int] = Field(None, ge=40, le=200)
    temperatura: Optional[Decimal] = Field(None, ge=35, le=42)
    glucosa: Optional[int] = Field(None, ge=50, le=400)


class EvolucionClinicaBase(BaseModel):
    """Nota SOAP de una visita."""
    nota_subjetiva: Optional[str] = None
    nota_objetiva: Optional[str] = None
    analisis_texto: Optional[str] = None
    plan_texto: Optional[str] = None
    signos_vitales_visita: Optional[SignosVitales] = None


class EvolucionClinicaCreate(EvolucionClinicaBase):
    tratamiento_id: int
    cita_id: Optional[int] = None
    podologo_id: Optional[int] = None


class EvolucionClinicaRead(EvolucionClinicaBase):
    id_evolucion: int
    tratamiento_id: int
    cita_id: Optional[int] = None
    podologo_id: Optional[int] = None
    fecha_visita: datetime
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE EVIDENCIA FOTOGRÁFICA
# =============================================================================

class EvidenciaFotograficaBase(BaseModel):
    """Foto clínica."""
    tipo_archivo: Optional[str] = None
    etapa_tratamiento: Optional[str] = Field(
        None, pattern="^(Inicial|Seguimiento|Final)$"
    )
    url_archivo: str
    analisis_visual_ia: Optional[dict] = None
    comentarios_medico: Optional[str] = None


class EvidenciaFotograficaCreate(EvidenciaFotograficaBase):
    evolucion_id: int


class EvidenciaFotograficaRead(EvidenciaFotograficaBase):
    id_evidencia: int
    evolucion_id: int
    fecha_captura: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# SCHEMAS DE SESIÓN IA
# =============================================================================

class SesionIABase(BaseModel):
    """Transcripción de consulta por IA."""
    url_audio_full: Optional[str] = None
    duracion_segundos: Optional[int] = Field(None, gt=0)
    transcripcion_estructurada: Optional[dict] = None
    resumen_generado: Optional[str] = None
    sentimiento_paciente: Optional[str] = Field(
        None, pattern="^(Positivo|Neutral|Negativo|Mixto|Urgente)$"
    )
    puntos_clave_detectados: Optional[List[str]] = None


class SesionIACreate(SesionIABase):
    cita_id: Optional[int] = None


class SesionIARead(SesionIABase):
    id_sesion_ia: int
    cita_id: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
