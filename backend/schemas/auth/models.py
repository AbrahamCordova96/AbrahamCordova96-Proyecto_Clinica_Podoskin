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


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = {"schema": "auth"}

    id_log = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp_accion = Column(TIMESTAMP(timezone=True), server_default=func.now(), primary_key=True)
    tabla_afectada = Column(String, nullable=False)
    registro_id = Column(BigInteger, nullable=False)
    accion = Column(String, nullable=False)

    usuario_id = Column(BigInteger, ForeignKey("auth.sys_usuarios.id_usuario"), nullable=True)
    datos_anteriores = Column(JSONB)
    datos_nuevos = Column(JSONB)
    ip_address = Column(INET)

    usuario = relationship("SysUsuario")