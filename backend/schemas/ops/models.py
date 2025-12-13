# =============================================================================
# backend/schemas/ops/models.py
# CLINICA_OPS_DB: Modelos SQLAlchemy para el schema "ops"
# =============================================================================
# Este archivo mapea las tablas operativas de la clínica:
#   - podologos: Profesionales que atienden pacientes
#   - catalogo_servicios: Servicios que ofrece la clínica
#   - solicitudes_prospectos: Leads/prospectos antes de ser pacientes
#   - citas: Agenda de la clínica
#
# ANALOGÍA: Si Core es el "expediente médico", Ops es la "agenda y recepción".
# Aquí se gestiona TODO lo relacionado con agendar y atender pacientes.
# =============================================================================

from sqlalchemy import (
    Column, BigInteger, String, Boolean, ForeignKey, Date, Text,
    Integer, Numeric, Time
)
# TIMESTAMP viene del dialecto PostgreSQL porque TIMESTAMPTZ no existe en el módulo principal
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# =============================================================================
# BASE DECLARATIVA
# =============================================================================
# Base separada para clinica_ops_db
Base = declarative_base()


# =============================================================================
# MODELO: PODÓLOGO
# =============================================================================
# Tabla: ops.podologos
# Los profesionales que atienden en la clínica.
class Podologo(Base):
    """
    Profesional de la clínica que atiende pacientes.
    
    Un podólogo puede estar vinculado a un usuario del sistema (para login)
    o puede ser solo un registro para la agenda.
    
    Analogía: Es la "ficha de empleado" del personal médico.
    """
    __tablename__ = "podologos"
    __table_args__ = {"schema": "ops"}
    
    id_podologo = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # Vinculación con usuario del sistema (opcional)
    # Permite que el podólogo haga login
    usuario_sistema_id = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    
    # ---------- Datos Profesionales ----------
    nombre_completo = Column(Text, nullable=False)
    cedula_profesional = Column(Text, unique=True)  # Cédula única
    especialidad = Column(Text, default='Podología General')
    activo = Column(Boolean, default=True)
    
    # NOM-024 Compliance: Professional identification
    # Opcionales ahora, serán obligatorios para reportes oficiales
    institucion_titulo = Column(String(200), nullable=True, comment="Institución que otorgó el título profesional - NOM-024")
    # cedula_profesional ya existe arriba, pero aseguramos que sea para NOM-024
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relaciones ----------
    citas = relationship("Cita", back_populates="podologo")


# =============================================================================
# MODELO: CATÁLOGO DE SERVICIOS
# =============================================================================
# Tabla: ops.catalogo_servicios
# Los servicios que ofrece la clínica con sus precios.
class CatalogoServicio(Base):
    """
    Catálogo de servicios ofrecidos por la clínica.
    
    Define qué servicios se pueden agendar y cobrar,
    con precio base y duración estimada.
    
    Analogía: Es el "menú" de la clínica con precios.
    """
    __tablename__ = "catalogo_servicios"
    __table_args__ = {"schema": "ops"}
    
    id_servicio = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    nombre_servicio = Column(Text, nullable=False)
    descripcion = Column(Text)
    
    # Precio en pesos mexicanos
    precio_base = Column(Numeric(10, 2), nullable=False)
    
    # Duración estimada en minutos (para calcular hora_fin)
    duracion_minutos = Column(Integer, nullable=False, default=30)
    
    # ¿Este servicio típicamente requiere citas de seguimiento?
    requiere_seguimiento = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)
    
    # ---------- Relaciones ----------
    citas = relationship("Cita", back_populates="servicio")


# =============================================================================
# MODELO: SOLICITUD DE PROSPECTO
# =============================================================================
# Tabla: ops.solicitudes_prospectos
# "Staging area" para leads que aún no son pacientes.
class SolicitudProspecto(Base):
    """
    Lead o prospecto que ha contactado a la clínica.
    
    Flujo típico:
    1. Persona llama/escribe preguntando por servicios
    2. Recepción crea una solicitud de prospecto
    3. Se agenda una cita de primera vez
    4. Si asiste, se convierte en paciente
    5. Si no asiste, queda como "No Show"
    
    Esto permite dar seguimiento a leads sin "ensuciar" la tabla de pacientes.
    
    Analogía: Es la "lista de espera" antes de abrir expediente.
    """
    __tablename__ = "solicitudes_prospectos"
    __table_args__ = {"schema": "ops"}
    
    id_solicitud = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # Datos básicos del prospecto (sin crear expediente completo)
    nombre_prospecto = Column(Text)
    telefono_contacto = Column(Text)
    motivo_visita_inicial = Column(Text)
    origen_contacto = Column(Text)  # ¿Cómo nos encontró? Redes, recomendación, etc.
    
    fecha_solicitud = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Estados del prospecto:
    # 'Pendiente': Acaba de llamar, sin agendar
    # 'Agendado': Ya tiene cita programada
    # 'Convertido': Ya es paciente (asistió a primera cita)
    # 'Cancelado': Canceló la cita o ya no le interesa
    # 'No Show': No asistió a la cita programada
    estado_prospecto = Column(Text, default='Pendiente')
    
    # Si se convirtió en paciente, aquí guardamos la referencia
    id_paciente_convertido = Column(BigInteger)  # FK virtual a clinic.pacientes
    created_by = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    
    # ---------- Relaciones ----------
    citas = relationship("Cita", back_populates="solicitud")


# =============================================================================
# MODELO: CITA
# =============================================================================
# Tabla: ops.citas
# La agenda de la clínica.
class Cita(Base):
    """
    Cita agendada en la clínica.
    
    Una cita puede ser para:
    - Un PACIENTE existente (tiene expediente)
    - Un PROSPECTO (primera vez, aún sin expediente)
    
    REGLA IMPORTANTE: Una cita tiene O paciente O prospecto, nunca ambos.
    
    El sistema SQL tiene un EXCLUDE constraint que previene que un podólogo
    tenga dos citas al mismo tiempo (anti-solapamiento).
    
    Analogía: Es la "agenda física" de la recepción digitalizada.
    """
    __tablename__ = "citas"
    __table_args__ = {"schema": "ops"}
    
    id_cita = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # ---------- ¿Para quién es la cita? ----------
    # Una cita es para UN paciente O UN prospecto (nunca ambos)
    paciente_id = Column(BigInteger)  # FK virtual a clinic.pacientes
    solicitud_id = Column(BigInteger, ForeignKey("ops.solicitudes_prospectos.id_solicitud"))
    
    # ---------- ¿Quién atiende y qué servicio? ----------
    podologo_id = Column(BigInteger, ForeignKey("ops.podologos.id_podologo"))
    servicio_id = Column(BigInteger, ForeignKey("ops.catalogo_servicios.id_servicio"))
    
    # ---------- Fecha y hora ----------
    fecha_cita = Column(Date, nullable=False)
    hora_inicio = Column(Time, nullable=False)
    hora_fin = Column(Time, nullable=False)
    
    # ---------- Estado de la cita ----------
    # Flujo normal: Pendiente → Confirmada → En Sala → Realizada
    # Flujos alternativos: Cancelada, No Asistió
    status = Column(Text, default='Confirmada')
    
    notas_agendamiento = Column(Text)  # Notas de recepción
    
    # ---------- Auditoría ----------
    created_by = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relaciones ----------
    podologo = relationship("Podologo", back_populates="citas")
    servicio = relationship("CatalogoServicio", back_populates="citas")
    solicitud = relationship("SolicitudProspecto", back_populates="citas")
