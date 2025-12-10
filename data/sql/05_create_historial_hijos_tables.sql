-- =============================================================================
-- Migración: Crear tablas hijas para historial clínico
-- Fecha: 2025-12-08
-- Descripción: Agrega tablas normalizadas (3NF) para alergias, suplementos,
--              antecedentes no patológicos y conversaciones digitales
-- =============================================================================

-- Conectarse a clinica_core_db
\c clinica_core_db

-- =============================================================================
-- Tabla: alergias
-- =============================================================================
CREATE TABLE IF NOT EXISTS clinic.alergias (
    id_alergia BIGSERIAL PRIMARY KEY,
    id_historial BIGINT NOT NULL REFERENCES clinic.historial_medico_general(id_historial) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    tipo TEXT,  -- medicamento, alimento, látex, etc.
    observaciones TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_alergias_id_historial ON clinic.alergias(id_historial);
CREATE INDEX idx_alergias_nombre ON clinic.alergias(nombre);
CREATE INDEX idx_alergias_deleted_at ON clinic.alergias(deleted_at);

-- =============================================================================
-- Tabla: suplementos
-- =============================================================================
CREATE TABLE IF NOT EXISTS clinic.suplementos (
    id_suplemento BIGSERIAL PRIMARY KEY,
    id_historial BIGINT NOT NULL REFERENCES clinic.historial_medico_general(id_historial) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    dosis TEXT,  -- ej: 500mg
    frecuencia TEXT,  -- ej: dos veces al día
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_suplementos_id_historial ON clinic.suplementos(id_historial);
CREATE INDEX idx_suplementos_nombre ON clinic.suplementos(nombre);
CREATE INDEX idx_suplementos_deleted_at ON clinic.suplementos(deleted_at);

-- =============================================================================
-- Tabla: antecedentes_no_patologicos
-- =============================================================================
CREATE TABLE IF NOT EXISTS clinic.antecedentes_no_patologicos (
    id_antnp BIGSERIAL PRIMARY KEY,
    id_historial BIGINT NOT NULL REFERENCES clinic.historial_medico_general(id_historial) ON DELETE CASCADE,
    descripcion TEXT NOT NULL,
    tipo TEXT,  -- dieta, ejercicio, inmunizaciones, suplementos, etc.
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_antecedentes_no_patologicos_id_historial ON clinic.antecedentes_no_patologicos(id_historial);
CREATE INDEX idx_antecedentes_no_patologicos_tipo ON clinic.antecedentes_no_patologicos(tipo);
CREATE INDEX idx_antecedentes_no_patologicos_deleted_at ON clinic.antecedentes_no_patologicos(deleted_at);

-- =============================================================================
-- Tabla: conversaciones_digitales
-- =============================================================================
CREATE TABLE IF NOT EXISTS clinic.conversaciones_digitales (
    id_conversacion BIGSERIAL PRIMARY KEY,
    id_paciente BIGINT NOT NULL REFERENCES clinic.pacientes(id_paciente) ON DELETE CASCADE,
    canal TEXT NOT NULL,  -- whatsapp, web, email, llamada, etc.
    remitente TEXT,  -- nombre del que envía
    mensaje TEXT NOT NULL,
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    url_adjunto TEXT,  -- si hay archivo adjunto
    leido BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_conversaciones_digitales_id_paciente ON clinic.conversaciones_digitales(id_paciente);
CREATE INDEX idx_conversaciones_digitales_canal ON clinic.conversaciones_digitales(canal);
CREATE INDEX idx_conversaciones_digitales_leido ON clinic.conversaciones_digitales(leido);
CREATE INDEX idx_conversaciones_digitales_deleted_at ON clinic.conversaciones_digitales(deleted_at);
CREATE INDEX idx_conversaciones_digitales_fecha ON clinic.conversaciones_digitales(fecha DESC);

-- =============================================================================
-- Tabla: conversaciones_presenciales (transcripciones de IA)
-- =============================================================================
CREATE TABLE IF NOT EXISTS clinic.conversaciones_presenciales (
    id_conversacion BIGSERIAL PRIMARY KEY,
    id_paciente BIGINT NOT NULL REFERENCES clinic.pacientes(id_paciente) ON DELETE CASCADE,
    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    usuario TEXT,  -- nombre del profesional que transcribe
    mensaje TEXT NOT NULL,
    tipo TEXT,  -- transcripcion, nota, resumen, etc.
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ  -- Soft delete
);

CREATE INDEX idx_conversaciones_presenciales_id_paciente ON clinic.conversaciones_presenciales(id_paciente);
CREATE INDEX idx_conversaciones_presenciales_tipo ON clinic.conversaciones_presenciales(tipo);
CREATE INDEX idx_conversaciones_presenciales_deleted_at ON clinic.conversaciones_presenciales(deleted_at);
CREATE INDEX idx_conversaciones_presenciales_fecha ON clinic.conversaciones_presenciales(fecha DESC);

-- =============================================================================
-- Confirmación
-- =============================================================================
\echo 'Migración completada: Tablas hijas de historial clínico creadas'
\echo 'Tablas creadas:'
\echo '  - clinic.alergias'
\echo '  - clinic.suplementos'
\echo '  - clinic.antecedentes_no_patologicos'
\echo '  - clinic.conversaciones_digitales'
\echo '  - clinic.conversaciones_presenciales'
