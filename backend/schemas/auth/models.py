# backend/schemas/auth/models.py
from sqlalchemy import (
    Column, BigInteger, String, Boolean, ForeignKey
)
# TIMESTAMP viene del dialecto PostgreSQL porque TIMESTAMPTZ no existe en el módulo principal
# Usamos TIMESTAMP(timezone=True) que es equivalente a TIMESTAMPTZ en PostgreSQL
from sqlalchemy.dialects.postgresql import JSONB, INET, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Clinica(Base):
    __tablename__ = "clinicas"
    __table_args__ = {"schema": "auth"}

    id_clinica = Column(BigInteger, primary_key=True, autoincrement=True)
    nombre = Column(String, nullable=False)
    rfc = Column(String)
    activa = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # NOM-024 Compliance: Interoperability field
    # CLUES: Clave Única de Establecimientos de Salud
    # Format: 12 alphanumeric characters assigned by DGIS
    # Opcional ahora, será obligatorio para certificación
    clues = Column(String(12), nullable=True, unique=True, comment="Clave Única de Establecimiento de Salud - Opcional ahora, obligatorio para certificación NOM-024")

    usuarios = relationship("SysUsuario", back_populates="clinica")


class SysUsuario(Base):
    __tablename__ = "sys_usuarios"
    __table_args__ = {"schema": "auth"}

    id_usuario = Column(BigInteger, primary_key=True, autoincrement=True)

    nombre_usuario = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String, nullable=False)

    rol = Column(String, nullable=False)
    activo = Column(Boolean, default=True)
    email = Column(String, unique=True)

    last_login = Column(TIMESTAMP(timezone=True))
    failed_login_attempts = Column(BigInteger, default=0)
    locked_until = Column(TIMESTAMP(timezone=True))

    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # FK a Clinica (opcional al inicio, pero usado para multi-tenant)
    clinica_id = Column(BigInteger, ForeignKey("auth.clinicas.id_clinica"), nullable=True)
    clinica = relationship("Clinica", back_populates="usuarios")
    
    # ======== NUEVO: Campos para API Key de Gemini ========
    # Almacena la API Key de Google Gemini encriptada con Fernet
    # La encriptación se realiza usando el servicio backend/api/core/encryption.py
    gemini_api_key_encrypted = Column(String(500), nullable=True, comment="API Key de Gemini encriptada con Fernet")
    # Timestamp de la última vez que el usuario actualizó su API Key
    gemini_api_key_updated_at = Column(TIMESTAMP(timezone=True), nullable=True, comment="Última actualización de la API Key")
    # Timestamp de la última validación exitosa contra la API de Gemini
    gemini_api_key_last_validated = Column(TIMESTAMP(timezone=True), nullable=True, comment="Última validación exitosa de la API Key")
    # ======================================================


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "auth"}

    id_log = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp_accion = Column(TIMESTAMP(timezone=True), server_default=func.now())
    tabla_afectada = Column(String, nullable=False)
    registro_id = Column(BigInteger, nullable=True)
    accion = Column(String, nullable=False)

    usuario_id = Column(BigInteger, ForeignKey("auth.sys_usuarios.id_usuario"), nullable=True)
    username = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    datos_anteriores = Column(JSONB)
    datos_nuevos = Column(JSONB)
    ip_address = Column(INET)
    
    # New fields for integration with LangGraph/Gemini
    method = Column(String, nullable=True)  # HTTP method (GET, POST, etc.)
    endpoint = Column(String, nullable=True)  # API endpoint path
    request_body = Column(String, nullable=True)  # Masked request body
    response_hash = Column(String, nullable=True)  # SHA-256 of response
    source_refs = Column(JSONB, nullable=True)  # Provenance references
    note = Column(String, nullable=True)  # Additional notes

    usuario = relationship("SysUsuario")


class VoiceTranscript(Base):
    """Store voice conversation transcripts for audit and history"""
    __tablename__ = "voice_transcripts"
    __table_args__ = {"schema": "auth"}

    id_transcript = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("auth.sys_usuarios.id_usuario"), nullable=False)
    user_text = Column(String, nullable=False)
    assistant_text = Column(String, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    langgraph_job_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    usuario = relationship("SysUsuario")


# =============================================================================
# NOM-024 COMPLIANCE: Immutable Audit Log
# =============================================================================
class AuditLogInmutable(Base):
    """
    Immutable audit log for NOM-024 compliance.
    
    This table is append-only and protected by PostgreSQL triggers.
    No UPDATE or DELETE operations are allowed.
    
    Stores complete state BEFORE and AFTER every change to critical data.
    Required for regulatory compliance and forensic analysis.
    
    NOM-024 Requirement: Healthcare records must have immutable audit trails
    that capture who, what, when, and why changes were made.
    """
    __tablename__ = "audit_logs_inmutable"
    __table_args__ = {"schema": "auth"}
    
    # Primary key - auto-increment only, never updated
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Timestamp - automatically set, immutable
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # User who performed the action
    user_id = Column(BigInteger, nullable=False)
    
    # Snapshot of username at the time of action (in case user is deleted/renamed)
    username_snapshot = Column(String(50), nullable=False)
    
    # Which table was affected
    tabla_afectada = Column(String(100), nullable=False)
    
    # ID of the record that was changed
    registro_id = Column(BigInteger, nullable=False)
    
    # Action type: INSERT, UPDATE, DELETE
    accion = Column(String(20), nullable=False)
    
    # Complete state BEFORE the change (NULL for INSERT)
    # Stores full JSON representation of the record
    datos_antes = Column(JSONB, nullable=True)
    
    # Complete state AFTER the change (NULL for DELETE)
    # Stores full JSON representation of the record
    datos_despues = Column(JSONB, nullable=True)
    
    # IP address of the client making the change
    ip_address = Column(INET, nullable=True)
    
    # Optional: reason for the change (for manual overrides)
    razon_cambio = Column(String(500), nullable=True)
    
    # No relationship to SysUsuario to avoid cascade issues
    # This is intentional - audit must survive user deletion


# =============================================================================
# NOM-024 COMPLIANCE: Access Logs (Read Operations)
# =============================================================================
class AccessLog(Base):
    """
    Log of read/access operations to sensitive data.
    
    Complements AuditLog (which tracks modifications) by tracking
    who accessed what data and when.
    
    Required for HIPAA-like compliance and NOM-024 security requirements.
    Healthcare data access must be auditable even for read-only operations.
    """
    __tablename__ = "access_logs"
    __table_args__ = {"schema": "auth"}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # When was the access
    timestamp = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    
    # Who accessed
    user_id = Column(BigInteger, nullable=False)
    username_snapshot = Column(String(50), nullable=False)
    
    # What action (consultar_expediente, ver_citas, etc.)
    accion = Column(String(100), nullable=False)
    
    # What resource (paciente_123, tratamiento_456, etc.)
    recurso = Column(String(200), nullable=False)
    
    # Client IP address
    ip_address = Column(INET, nullable=True)
    
    # HTTP method (GET, POST, etc.)
    metodo_http = Column(String(10), nullable=True)
    
    # API endpoint path
    endpoint = Column(String(200), nullable=True)
    
    # No relationship to avoid cascade issues


# =============================================================================
# NOM-024 COMPLIANCE: Granular Permissions (Preparation)
# =============================================================================
# Future: Implementar permisos granulares más allá de roles simples
# Por ahora el sistema usa solo 3 roles (Admin, Podologo, Recepcion)
# Estas tablas preparan la estructura para permisos más finos
# =============================================================================

class Permiso(Base):
    """
    Catálogo de permisos del sistema.
    
    Preparación para RBAC granular. Ejemplos de permisos:
    - leer_expediente
    - modificar_expediente
    - eliminar_paciente
    - ver_finanzas
    - crear_usuario
    - exportar_datos
    
    Por ahora no se usa (el sistema usa solo roles simples),
    pero la estructura está lista para cuando se necesite.
    """
    __tablename__ = "permisos"
    __table_args__ = {"schema": "auth"}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Nombre único del permiso (snake_case)
    nombre = Column(String(100), unique=True, nullable=False)
    
    # Descripción legible del permiso
    descripcion = Column(String(200), nullable=True)
    
    # Módulo/categoría (opcional: "pacientes", "finanzas", "admin", etc.)
    modulo = Column(String(50), nullable=True)
    
    activo = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class RolPermiso(Base):
    """
    Relación muchos-a-muchos entre roles y permisos.
    
    Define qué permisos tiene cada rol.
    
    Ejemplo:
    - Rol "Admin" tiene todos los permisos
    - Rol "Podologo" tiene permisos clínicos pero no financieros
    - Rol "Recepcion" tiene solo permisos de agenda y contacto
    
    Por ahora comentado/no usado, pero estructura preparada.
    """
    __tablename__ = "rol_permisos"
    __table_args__ = {"schema": "auth"}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # Rol (valores: Admin, Podologo, Recepcion)
    # En el futuro podría ser FK a tabla de roles
    rol = Column(String(50), nullable=False)
    
    # FK a permiso
    permiso_id = Column(BigInteger, ForeignKey("auth.permisos.id"), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # Relación
    permiso = relationship("Permiso")