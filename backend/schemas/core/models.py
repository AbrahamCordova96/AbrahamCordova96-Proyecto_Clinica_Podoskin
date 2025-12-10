# =============================================================================
# backend/schemas/core/models.py
# CLINICA_CORE_DB: Modelos SQLAlchemy para el schema "clinic"
# =============================================================================
# Este archivo mapea las tablas de la base de datos clinica_core_db:
#   - pacientes: Expedientes clínicos de los pacientes
#   - historial_medico_general: Antecedentes médicos (peso, talla, IMC, alergias, etc.)
#   - historial_gineco: Historial gineco-obstétrico
#   - tratamientos: "Carpetas" por problema del paciente
#   - evoluciones_clinicas: Notas SOAP de cada visita
#   - evidencia_fotografica: Fotos de tratamientos
#   - sesiones_ia_conversacion: Transcripciones de IA
#
# ANALOGÍA: Piensa en esto como el "expediente médico digital" del paciente.
# Cada modelo es como una sección diferente del expediente físico.
# =============================================================================

from decimal import Decimal
from sqlalchemy import (
    Column, BigInteger, String, Boolean, ForeignKey, Date, Text,
    Integer, Numeric, CheckConstraint, Computed
)
# TIMESTAMP viene del dialecto PostgreSQL porque TIMESTAMPTZ no existe en el módulo principal
# Usamos TIMESTAMP(timezone=True) que es equivalente a TIMESTAMPTZ en PostgreSQL
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# =============================================================================
# BASE DECLARATIVA
# =============================================================================
# Cada base de datos tiene su propia Base. Esto permite que SQLAlchemy
# sepa que estas tablas pertenecen a clinica_core_db, no a clinica_auth_db.
Base = declarative_base()


# =============================================================================
# MODELO: PACIENTE
# =============================================================================
# Tabla principal: clinic.pacientes
# Es el "corazón" del sistema. Todo gira alrededor del paciente.
class Paciente(Base):
    """
    Expediente clínico del paciente.
    
    Contiene datos personales, demográficos y de contacto.
    Es la tabla central a la que se conectan historiales, tratamientos, citas, etc.
    
    Analogía: Es la "portada" del expediente médico físico.
    """
    __tablename__ = "pacientes"
    __table_args__ = {"schema": "clinic"}
    
    # ---------- Identificador ----------
    id_paciente = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)  # Multi-tenant: a qué clínica pertenece
    
    # ---------- Datos Personales ----------
    # Nombres y apellidos separados para búsquedas más precisas
    nombres = Column(Text, nullable=False)
    apellidos = Column(Text, nullable=False)
    fecha_nacimiento = Column(Date, nullable=False)
    sexo = Column(String(1))  # 'M' o 'F'
    
    # ---------- Datos Sociodemográficos ----------
    # Estos campos son opcionales pero útiles para estadísticas
    estado_civil = Column(Text)
    ocupacion = Column(Text)
    escolaridad = Column(Text)
    religion = Column(Text)
    domicilio = Column(Text)
    como_supo_de_nosotros = Column(Text)  # Marketing: ¿cómo nos encontró?
    
    # ---------- Contacto ----------
    telefono = Column(Text, nullable=False)  # Mínimo 10 caracteres (validado en SQL)
    email = Column(Text)  # Validación de formato en SQL con regex
    
    # ---------- Auditoría ----------
    # Estos campos rastrean quién creó/modificó y cuándo
    fecha_registro = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger, default=1)  # FK a auth.sys_usuarios (validar en app)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete: NULL = activo
    
    # ---------- Relaciones ----------
    # Un paciente tiene UN historial médico general (1:1)
    historial_medico = relationship("HistorialMedicoGeneral", back_populates="paciente", uselist=False)
    # Un paciente tiene UN historial ginecológico (1:1, solo mujeres)
    historial_gineco = relationship("HistorialGineco", back_populates="paciente", uselist=False)
    # Un paciente puede tener MUCHOS tratamientos (1:N)
    tratamientos = relationship("Tratamiento", back_populates="paciente")


# =============================================================================
# MODELO: HISTORIAL MÉDICO GENERAL
# =============================================================================
# Tabla: clinic.historial_medico_general
# Antecedentes heredofamiliares, personales patológicos, alergias, hábitos.
class HistorialMedicoGeneral(Base):
    """
    Antecedentes médicos del paciente.
    
    Contiene:
    - Antropometría (peso, talla, IMC calculado automáticamente)
    - Tipo de sangre
    - Antecedentes heredofamiliares (AHF): diabetes, hipertensión, etc.
    - Antecedentes personales patológicos (APP)
    - Alergias
    - Hábitos (tabaco, alcohol, ejercicio)
    
    Analogía: Es la hoja de "antecedentes" del expediente físico.
    
    NOTA IMPORTANTE: La columna 'imc' es GENERADA AUTOMÁTICAMENTE por PostgreSQL.
    No intentes escribir en ella, solo leerla.
    """
    __tablename__ = "historial_medico_general"
    __table_args__ = {"schema": "clinic"}
    
    id_historial = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK a paciente (relación 1:1 gracias a UNIQUE en SQL)
    paciente_id = Column(BigInteger, ForeignKey("clinic.pacientes.id_paciente", ondelete="CASCADE"), unique=True)
    
    # ---------- Antropometría ----------
    peso_kg = Column(Numeric(5, 2))  # Ej: 75.50 kg
    talla_cm = Column(Numeric(5, 2))  # Ej: 170.00 cm
    
    # IMC: Columna GENERADA por PostgreSQL (read-only desde Python)
    # Fórmula: peso / (talla en metros)²
    # NO incluir en INSERTs, PostgreSQL lo calcula solo
    imc = Column(Numeric(5, 2), Computed("CASE WHEN peso_kg IS NOT NULL AND talla_cm IS NOT NULL AND talla_cm > 0 THEN ROUND(peso_kg / POWER(talla_cm / 100.0, 2), 2) ELSE NULL END"))
    
    tipos_sangre = Column(Text)  # A+, A-, B+, B-, AB+, AB-, O+, O-
    
    # ---------- Antecedentes Heredofamiliares (AHF) ----------
    # ¿Familiares directos con estas condiciones?
    ahf_diabetes = Column(Boolean, default=False)
    ahf_hipertension = Column(Boolean, default=False)
    ahf_cancer = Column(Boolean, default=False)
    ahf_cardiacas = Column(Boolean, default=False)
    ahf_detalles = Column(Text)  # Descripción libre
    
    # ---------- Antecedentes Personales Patológicos (APP) ----------
    # ¿El paciente tiene estas condiciones?
    app_diabetes = Column(Boolean, default=False)
    app_diabetes_inicio = Column(Date)  # ¿Desde cuándo es diabético?
    app_hipertension = Column(Boolean, default=False)
    app_otras_patologias = Column(Text)
    
    # ---------- Alergias ----------
    alergias_activas = Column(Boolean, default=False)
    lista_alergias = Column(Text)  # Lista de alergias conocidas
    
    # ---------- Hábitos ----------
    tabaquismo = Column(Boolean, default=False)
    alcoholismo = Column(Boolean, default=False)
    actividad_fisica = Column(Text)  # Descripción: sedentario, moderado, activo
    
    # ---------- Relación ----------
    paciente = relationship("Paciente", back_populates="historial_medico")


# =============================================================================
# MODELO: HISTORIAL GINECOLÓGICO
# =============================================================================
# Tabla: clinic.historial_gineco
# Solo aplica para pacientes femeninas.
class HistorialGineco(Base):
    """
    Historial gineco-obstétrico para pacientes mujeres.
    
    Contiene:
    - Datos menstruales (menarca, ritmo, FUM)
    - Fórmula obstétrica (G P C A)
    - Métodos anticonceptivos
    
    Analogía: La sección de "ginecología" en el formato de historia clínica.
    
    NOTA: Solo se crea para pacientes con sexo='F'.
    """
    __tablename__ = "historial_gineco"
    __table_args__ = {"schema": "clinic"}
    
    id_gineco = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK a paciente (1:1)
    paciente_id = Column(BigInteger, ForeignKey("clinic.pacientes.id_paciente", ondelete="CASCADE"), unique=True)
    
    # ---------- Datos Menstruales ----------
    menarca_edad = Column(Integer)  # Edad de primera menstruación (9-18 años)
    ritmo_menstrual = Column(Text)  # Ej: "28x5" (cada 28 días, dura 5)
    fecha_ultima_menstruacion = Column(Date)  # FUM
    
    # ---------- Fórmula Obstétrica: G P C A ----------
    # G = Gestas (embarazos totales)
    # P = Partos naturales
    # C = Cesáreas
    # A = Abortos
    gestas = Column(Integer, default=0)
    partos = Column(Integer, default=0)
    cesareas = Column(Integer, default=0)
    abortos = Column(Integer, default=0)
    embarazos_ectopicos = Column(Integer, default=0)
    embarazos_multiples = Column(Integer, default=0)
    
    anticonceptivos_actuales = Column(Text)  # Método anticonceptivo actual
    
    # ---------- Relación ----------
    paciente = relationship("Paciente", back_populates="historial_gineco")


# =============================================================================
# MODELO: TRATAMIENTO
# =============================================================================
# Tabla: clinic.tratamientos
# Una "carpeta" por problema del paciente. Un paciente puede tener varios.
class Tratamiento(Base):
    """
    Carpeta de tratamiento por problema específico.
    
    Un paciente puede tener MÚLTIPLES tratamientos simultáneos.
    Ejemplo: Un paciente viene por onicomicosis en pie derecho (tratamiento 1)
    y después desarrolla un problema en pie izquierdo (tratamiento 2).
    
    Cada tratamiento agrupa sus propias evoluciones clínicas.
    
    Analogía: Es como tener una "sub-carpeta" dentro del expediente
    para cada problema que tratamos.
    """
    __tablename__ = "tratamientos"
    __table_args__ = {"schema": "clinic"}
    
    id_tratamiento = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK a paciente
    paciente_id = Column(BigInteger, ForeignKey("clinic.pacientes.id_paciente"))
    
    # ---------- Datos del Tratamiento ----------
    motivo_consulta_principal = Column(Text, nullable=False)  # ¿Por qué vino?
    diagnostico_inicial = Column(Text)  # Diagnóstico del podólogo
    fecha_inicio = Column(Date, server_default=func.current_date())
    
    # Estados posibles del tratamiento
    # 'En Curso': Activo, el paciente sigue viniendo
    # 'Alta': Terminado exitosamente
    # 'Pausado': Temporalmente detenido
    # 'Abandonado': El paciente dejó de venir
    estado_tratamiento = Column(Text, default='En Curso')
    plan_general = Column(Text)  # Plan de tratamiento a seguir
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relaciones ----------
    paciente = relationship("Paciente", back_populates="tratamientos")
    evoluciones = relationship("EvolucionClinica", back_populates="tratamiento")


# =============================================================================
# MODELO: EVOLUCIÓN CLÍNICA (NOTAS SOAP)
# =============================================================================
# Tabla: clinic.evoluciones_clinicas
# Registro de cada visita/consulta dentro de un tratamiento.
class EvolucionClinica(Base):
    """
    Nota clínica de cada visita usando formato SOAP.
    
    SOAP significa:
    - S (Subjetivo): Lo que el paciente dice ("me duele el pie")
    - O (Objetivo): Lo que el podólogo observa (eritema, inflamación)
    - A (Análisis): Diagnóstico/interpretación
    - P (Plan): Qué se va a hacer (próxima cita, medicamentos)
    
    Los signos vitales se guardan en JSONB para flexibilidad.
    
    Analogía: Cada hoja de "nota de evolución" en el expediente físico.
    """
    __tablename__ = "evoluciones_clinicas"
    __table_args__ = {"schema": "clinic"}
    
    id_evolucion = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK a tratamiento (muchas evoluciones por tratamiento)
    tratamiento_id = Column(BigInteger, ForeignKey("clinic.tratamientos.id_tratamiento"))
    
    # Referencias a otras BDs (validar en app, no hay FK real cross-database)
    cita_id = Column(BigInteger)      # FK virtual a ops.citas
    podologo_id = Column(BigInteger)  # FK virtual a ops.podologos
    
    fecha_visita = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # ---------- Notas SOAP ----------
    nota_subjetiva = Column(Text)   # S: Lo que el paciente reporta
    nota_objetiva = Column(Text)    # O: Examen físico, observaciones
    analisis_texto = Column(Text)   # A: Análisis/diagnóstico
    plan_texto = Column(Text)       # P: Plan de tratamiento
    
    # ---------- Signos Vitales (JSONB) ----------
    # Estructura esperada:
    # {
    #   "presion_arterial": "120/80",
    #   "frecuencia_cardiaca": 75,    // 40-200 bpm
    #   "temperatura": 36.5,          // 35-42 °C
    #   "glucosa": 95                  // 50-400 mg/dL
    # }
    signos_vitales_visita = Column(JSONB)
    
    created_by = Column(BigInteger)  # FK virtual a auth.sys_usuarios
    
    # ---------- Relaciones ----------
    tratamiento = relationship("Tratamiento", back_populates="evoluciones")
    evidencias = relationship("EvidenciaFotografica", back_populates="evolucion")


# =============================================================================
# MODELO: EVIDENCIA FOTOGRÁFICA
# =============================================================================
# Tabla: clinic.evidencia_fotografica
# Fotos de antes/durante/después del tratamiento.
class EvidenciaFotografica(Base):
    """
    Fotografías clínicas asociadas a una evolución.
    
    Permite documentar visualmente el progreso del tratamiento:
    - Fotos iniciales (antes)
    - Fotos de seguimiento (durante)
    - Fotos finales (después/alta)
    
    También puede incluir análisis de IA (detección de lesiones, etc.)
    
    Analogía: Las fotos polaroid que se pegan en el expediente físico.
    """
    __tablename__ = "evidencia_fotografica"
    __table_args__ = {"schema": "clinic"}
    
    id_evidencia = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK a evolución clínica
    evolucion_id = Column(BigInteger, ForeignKey("clinic.evoluciones_clinicas.id_evolucion"))
    
    tipo_archivo = Column(Text)        # 'imagen/jpeg', 'imagen/png', etc.
    etapa_tratamiento = Column(Text)   # 'Inicial', 'Seguimiento', 'Final'
    url_archivo = Column(Text, nullable=False)  # Ruta al archivo
    
    # Resultados de análisis de IA (opcional)
    # Puede contener: predicciones, confianza, áreas detectadas, etc.
    analisis_visual_ia = Column(JSONB)
    
    comentarios_medico = Column(Text)  # Notas del podólogo sobre la imagen
    fecha_captura = Column(TIMESTAMP(timezone=True), server_default=func.now())
    
    # ---------- Relación ----------
    evolucion = relationship("EvolucionClinica", back_populates="evidencias")


# =============================================================================
# MODELO: SESIÓN IA CONVERSACIÓN
# =============================================================================
# Tabla: clinic.sesiones_ia_conversacion
# Transcripciones de consultas procesadas por IA.
class SesionIAConversacion(Base):
    """
    Transcripción de una consulta procesada por inteligencia artificial.
    
    Cuando se graba una consulta, la IA puede:
    - Transcribir el audio a texto
    - Estructurar la información (síntomas, diagnóstico, plan)
    - Generar un resumen
    - Detectar el sentimiento del paciente
    - Extraer puntos clave
    
    Esto ayuda al podólogo a documentar más rápido.
    
    Analogía: Un asistente que toma notas durante la consulta.
    """
    __tablename__ = "sesiones_ia_conversacion"
    __table_args__ = {"schema": "clinic"}
    
    id_sesion_ia = Column(BigInteger, primary_key=True, autoincrement=True)
    id_clinica = Column(BigInteger, default=1)
    
    # FK virtual a ops.citas (validar en app)
    cita_id = Column(BigInteger)
    
    url_audio_full = Column(Text)           # Ruta al archivo de audio
    duracion_segundos = Column(Integer)     # Duración de la grabación
    
    # Estructura de la transcripción (JSONB para flexibilidad)
    # Puede contener: speakers, timestamps, texto segmentado, etc.
    transcripcion_estructurada = Column(JSONB)
    
    resumen_generado = Column(Text)  # Resumen automático de la consulta
    
    # Análisis de sentimiento: ¿Cómo se siente el paciente?
    # Valores: 'Positivo', 'Neutral', 'Negativo', 'Mixto', 'Urgente'
    sentimiento_paciente = Column(Text)
    
    # Puntos clave detectados (array de strings)
    # Ej: ["dolor crónico", "mejora visible", "requiere seguimiento"]
    puntos_clave_detectados = Column(ARRAY(Text))
    
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


# =============================================================================
# MODELO: ALERGIA
# =============================================================================
# Tabla: clinic.alergias
# Tabla hija de historial_medico_general para normalización 3NF
class Alergia(Base):
    """
    Alergias del paciente (medicamentos, alimentos, látex, etc.)
    Tabla hija de HistorialMedicoGeneral (relación 1:N)
    """
    __tablename__ = "alergias"
    __table_args__ = {"schema": "clinic"}
    
    id_alergia = Column(BigInteger, primary_key=True, autoincrement=True)
    id_historial = Column(BigInteger, ForeignKey("clinic.historial_medico_general.id_historial", ondelete="CASCADE"))
    nombre = Column(Text, nullable=False)
    tipo = Column(Text)  # medicamento, alimento, látex, etc.
    observaciones = Column(Text)
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relación ----------
    historial = relationship("HistorialMedicoGeneral", backref="alergias")


# =============================================================================
# MODELO: SUPLEMENTO
# =============================================================================
# Tabla: clinic.suplementos
# Tabla hija de historial_medico_general para normalización 3NF
class Suplemento(Base):
    """
    Suplementos y vitaminas del paciente
    Tabla hija de HistorialMedicoGeneral (relación 1:N)
    """
    __tablename__ = "suplementos"
    __table_args__ = {"schema": "clinic"}
    
    id_suplemento = Column(BigInteger, primary_key=True, autoincrement=True)
    id_historial = Column(BigInteger, ForeignKey("clinic.historial_medico_general.id_historial", ondelete="CASCADE"))
    nombre = Column(Text, nullable=False)
    dosis = Column(Text)
    frecuencia = Column(Text)
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relación ----------
    historial = relationship("HistorialMedicoGeneral", backref="suplementos")


# =============================================================================
# MODELO: ANTECEDENTE NO PATOLÓGICO
# =============================================================================
# Tabla: clinic.antecedentes_no_patologicos
# Tabla hija de historial_medico_general para normalización 3NF
class AntecedenteNoPatologico(Base):
    """
    Antecedentes no patológicos (dieta, ejercicio, inmunizaciones, etc.)
    Tabla hija de HistorialMedicoGeneral (relación 1:N)
    """
    __tablename__ = "antecedentes_no_patologicos"
    __table_args__ = {"schema": "clinic"}
    
    id_antnp = Column(BigInteger, primary_key=True, autoincrement=True)
    id_historial = Column(BigInteger, ForeignKey("clinic.historial_medico_general.id_historial", ondelete="CASCADE"))
    descripcion = Column(Text, nullable=False)
    tipo = Column(Text)  # dieta, ejercicio, inmunizaciones, etc.
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relación ----------
    historial = relationship("HistorialMedicoGeneral", backref="antecedentes_no_patologicos")


# =============================================================================
# MODELO: CONVERSACIÓN PRESENCIAL
# =============================================================================
# Tabla: clinic.conversaciones_presenciales
# Transcripciones y notas de IA durante consultas presenciales
class ConversacionPresencial(Base):
    """
    Conversaciones presenciales (transcripciones de IA durante consultas)
    Tabla hija de Paciente (relación 1:N)
    """
    __tablename__ = "conversaciones_presenciales"
    __table_args__ = {"schema": "clinic"}
    
    id_conversacion = Column(BigInteger, primary_key=True, autoincrement=True)
    id_paciente = Column(BigInteger, ForeignKey("clinic.pacientes.id_paciente", ondelete="CASCADE"))
    fecha = Column(TIMESTAMP(timezone=True), server_default=func.now())
    usuario = Column(Text)  # nombre del profesional que transcribe
    mensaje = Column(Text, nullable=False)
    tipo = Column(Text)  # transcripcion, nota, etc.
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relación ----------
    paciente = relationship("Paciente", backref="conversaciones_presenciales")


# =============================================================================
# Tabla: clinic.conversaciones_digitales
# Mensajes por canales digitales: WhatsApp, web, chat, llamadas, etc.
class ConversacionDigital(Base):
    """
    Conversaciones digitales con pacientes.
    
    Contiene mensajes de:
    - WhatsApp
    - Chat de la página web
    - Email
    - Llamadas telefónicas (notas)
    - Redes sociales
    
    Analogía: Es como el historial de mensajes en WhatsApp,
    pero centralizado en la BD para auditoría y contexto clínico.
    """
    __tablename__ = "conversaciones_digitales"
    __table_args__ = {"schema": "clinic"}
    
    id_conversacion = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # FK a paciente
    id_paciente = Column(BigInteger, ForeignKey("clinic.pacientes.id_paciente", ondelete="CASCADE"))
    
    # ---------- Contenido del Mensaje ----------
    canal = Column(Text, nullable=False)  # whatsapp, web, email, llamada, etc.
    remitente = Column(Text)  # nombre o id del usuario que envia (ej: podologo, paciente, sistema)
    mensaje = Column(Text, nullable=False)  # contenido del mensaje
    
    # ---------- Metadata ----------
    fecha = Column(TIMESTAMP(timezone=True), server_default=func.now())
    url_adjunto = Column(Text)  # Si hay archivo (foto, documento, etc.)
    leido = Column(Boolean, default=False)  # ¿Ya fue leído por el profesional?
    
    # ---------- Auditoría ----------
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    created_by = Column(BigInteger)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(BigInteger)
    deleted_at = Column(TIMESTAMP(timezone=True))  # Soft delete
    
    # ---------- Relación ----------
    paciente = relationship("Paciente", backref="conversaciones_digitales")
