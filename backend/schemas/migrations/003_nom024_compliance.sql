-- ============================================================================
-- Migration: 003_nom024_compliance.sql
-- Description: Add NOM-024 compliance models and fields
-- Date: 2025-12-13
-- Author: GitHub Copilot Agent
-- ============================================================================
-- This migration adds:
-- 1. Immutable audit log table (audit_logs_inmutable)
-- 2. Access log table (access_logs)
-- 3. Permission tables (permisos, rol_permisos)
-- 4. NOM-024 fields to pacientes table
-- 5. Interoperability field to clinicas table (CLUES)
-- 6. Electronic signature fields to tratamientos and evoluciones_clinicas
-- 7. Professional identification fields to podologos
-- 8. Catalog tables (cat_diagnosticos, cat_procedimientos, cat_medicamentos)
-- ============================================================================

-- ============================================================================
-- CLINICA_AUTH_DB: Auth Schema Changes
-- ============================================================================

\c clinica_auth_db

-- ----------------------------------------------------------------------------
-- 1. Immutable Audit Log (NOM-024 Critical)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.audit_logs_inmutable (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    username_snapshot VARCHAR(50) NOT NULL,
    tabla_afectada VARCHAR(100) NOT NULL,
    registro_id BIGINT NOT NULL,
    accion VARCHAR(20) NOT NULL CHECK (accion IN ('INSERT', 'UPDATE', 'DELETE')),
    datos_antes JSONB,
    datos_despues JSONB,
    ip_address INET,
    razon_cambio VARCHAR(500)
);

COMMENT ON TABLE auth.audit_logs_inmutable IS 'NOM-024 Immutable audit log - append-only, protected by trigger';
COMMENT ON COLUMN auth.audit_logs_inmutable.id IS 'Primary key - never modified';
COMMENT ON COLUMN auth.audit_logs_inmutable.username_snapshot IS 'Username snapshot - survives user deletion';
COMMENT ON COLUMN auth.audit_logs_inmutable.datos_antes IS 'Complete state BEFORE change (NULL for INSERT)';
COMMENT ON COLUMN auth.audit_logs_inmutable.datos_despues IS 'Complete state AFTER change (NULL for DELETE)';

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_audit_inmutable_timestamp ON auth.audit_logs_inmutable(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_inmutable_user ON auth.audit_logs_inmutable(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_inmutable_tabla ON auth.audit_logs_inmutable(tabla_afectada, registro_id);

-- Create trigger function to prevent modifications
CREATE OR REPLACE FUNCTION auth.prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs_inmutable is append-only. UPDATE and DELETE operations are not allowed. This table is protected for NOM-024 compliance.';
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to protect immutability
DROP TRIGGER IF EXISTS protect_audit_log ON auth.audit_logs_inmutable;
CREATE TRIGGER protect_audit_log
    BEFORE UPDATE OR DELETE ON auth.audit_logs_inmutable
    FOR EACH ROW
    EXECUTE FUNCTION auth.prevent_audit_modification();

-- ----------------------------------------------------------------------------
-- 2. Access Log (NOM-024 Read Operations)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.access_logs (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    username_snapshot VARCHAR(50) NOT NULL,
    accion VARCHAR(100) NOT NULL,
    recurso VARCHAR(200) NOT NULL,
    ip_address INET,
    metodo_http VARCHAR(10),
    endpoint VARCHAR(200)
);

COMMENT ON TABLE auth.access_logs IS 'NOM-024 Access log for read operations on sensitive data';
COMMENT ON COLUMN auth.access_logs.accion IS 'Action performed (e.g., consultar_expediente, ver_citas)';
COMMENT ON COLUMN auth.access_logs.recurso IS 'Resource accessed (e.g., paciente_123, tratamiento_456)';

CREATE INDEX IF NOT EXISTS idx_access_timestamp ON auth.access_logs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_access_user ON auth.access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_access_recurso ON auth.access_logs(recurso);

-- ----------------------------------------------------------------------------
-- 3. Permission Tables (NOM-024 RBAC Preparation)
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth.permisos (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion VARCHAR(200),
    modulo VARCHAR(50),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE auth.permisos IS 'NOM-024 Permission catalog for granular RBAC (future use)';
COMMENT ON COLUMN auth.permisos.nombre IS 'Unique permission name in snake_case (e.g., leer_expediente)';
COMMENT ON COLUMN auth.permisos.modulo IS 'Module category (e.g., pacientes, finanzas, admin)';

CREATE TABLE IF NOT EXISTS auth.rol_permisos (
    id BIGSERIAL PRIMARY KEY,
    rol VARCHAR(50) NOT NULL,
    permiso_id BIGINT NOT NULL REFERENCES auth.permisos(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(rol, permiso_id)
);

COMMENT ON TABLE auth.rol_permisos IS 'NOM-024 Role-Permission mapping for granular RBAC (future use)';
COMMENT ON COLUMN auth.rol_permisos.rol IS 'Role name: Admin, Podologo, Recepcion';

CREATE INDEX IF NOT EXISTS idx_rol_permisos_rol ON auth.rol_permisos(rol);
CREATE INDEX IF NOT EXISTS idx_rol_permisos_permiso ON auth.rol_permisos(permiso_id);

-- ----------------------------------------------------------------------------
-- 4. Add CLUES field to clinicas (NOM-024 Interoperability)
-- ----------------------------------------------------------------------------
ALTER TABLE auth.clinicas 
    ADD COLUMN IF NOT EXISTS clues VARCHAR(12) UNIQUE;

COMMENT ON COLUMN auth.clinicas.clues IS 'NOM-024: Clave Única de Establecimiento de Salud - Optional now, mandatory for certification';

CREATE INDEX IF NOT EXISTS idx_clinicas_clues ON auth.clinicas(clues) WHERE clues IS NOT NULL;

-- ============================================================================
-- CLINICA_CORE_DB: Core Schema Changes
-- ============================================================================

\c clinica_core_db

-- ----------------------------------------------------------------------------
-- 5. Add NOM-024 fields to pacientes
-- ----------------------------------------------------------------------------
ALTER TABLE clinic.pacientes
    ADD COLUMN IF NOT EXISTS curp VARCHAR(18),
    ADD COLUMN IF NOT EXISTS segundo_apellido VARCHAR(50),
    ADD COLUMN IF NOT EXISTS estado_nacimiento VARCHAR(2),
    ADD COLUMN IF NOT EXISTS nacionalidad VARCHAR(3) DEFAULT 'MEX',
    ADD COLUMN IF NOT EXISTS estado_residencia VARCHAR(2),
    ADD COLUMN IF NOT EXISTS municipio_residencia VARCHAR(3),
    ADD COLUMN IF NOT EXISTS localidad_residencia VARCHAR(4),
    ADD COLUMN IF NOT EXISTS consentimiento_intercambio BOOLEAN DEFAULT FALSE NOT NULL,
    ADD COLUMN IF NOT EXISTS fecha_consentimiento DATE;

-- Add comments
COMMENT ON COLUMN clinic.pacientes.curp IS 'NOM-024 Tabla 1: CURP - Optional now, mandatory for certification';
COMMENT ON COLUMN clinic.pacientes.segundo_apellido IS 'NOM-024 Tabla 1: Segundo apellido (materno)';
COMMENT ON COLUMN clinic.pacientes.estado_nacimiento IS 'NOM-024: Código INEGI del estado de nacimiento';
COMMENT ON COLUMN clinic.pacientes.nacionalidad IS 'NOM-024: Código ISO 3166-1 alpha-3 de nacionalidad';
COMMENT ON COLUMN clinic.pacientes.estado_residencia IS 'NOM-024: Código INEGI del estado de residencia';
COMMENT ON COLUMN clinic.pacientes.municipio_residencia IS 'NOM-024: Código INEGI del municipio de residencia';
COMMENT ON COLUMN clinic.pacientes.localidad_residencia IS 'NOM-024: Código INEGI de la localidad de residencia';
COMMENT ON COLUMN clinic.pacientes.consentimiento_intercambio IS 'NOM-024: Consiente el intercambio de información con otras instituciones';
COMMENT ON COLUMN clinic.pacientes.fecha_consentimiento IS 'NOM-024: Fecha del consentimiento informado';

-- Add index on CURP for faster lookups
CREATE INDEX IF NOT EXISTS idx_pacientes_curp ON clinic.pacientes(curp) WHERE curp IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 6. Add electronic signature fields to tratamientos
-- ----------------------------------------------------------------------------
ALTER TABLE clinic.tratamientos
    ADD COLUMN IF NOT EXISTS firma_electronica TEXT,
    ADD COLUMN IF NOT EXISTS firma_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS firma_tipo VARCHAR(50);

COMMENT ON COLUMN clinic.tratamientos.firma_electronica IS 'NOM-024: Hash de firma electrónica - Preparation for FIEL/e.firma';
COMMENT ON COLUMN clinic.tratamientos.firma_timestamp IS 'NOM-024: Timestamp de la firma electrónica';
COMMENT ON COLUMN clinic.tratamientos.firma_tipo IS 'NOM-024: Tipo de firma (FIEL, e.firma, simple, etc.)';

-- ----------------------------------------------------------------------------
-- 7. Add electronic signature fields to evoluciones_clinicas
-- ----------------------------------------------------------------------------
ALTER TABLE clinic.evoluciones_clinicas
    ADD COLUMN IF NOT EXISTS firma_electronica TEXT,
    ADD COLUMN IF NOT EXISTS firma_timestamp TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS firma_tipo VARCHAR(50);

COMMENT ON COLUMN clinic.evoluciones_clinicas.firma_electronica IS 'NOM-024: Hash de firma electrónica del podólogo';
COMMENT ON COLUMN clinic.evoluciones_clinicas.firma_timestamp IS 'NOM-024: Timestamp de la firma';
COMMENT ON COLUMN clinic.evoluciones_clinicas.firma_tipo IS 'NOM-024: Tipo de firma electrónica';

-- ----------------------------------------------------------------------------
-- 8. Catalog Tables (NOM-024 Preparation)
-- ----------------------------------------------------------------------------

-- Diagnoses catalog (CIE-10)
CREATE TABLE IF NOT EXISTS clinic.cat_diagnosticos (
    id BIGSERIAL PRIMARY KEY,
    codigo_cie10 VARCHAR(10) UNIQUE NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    categoria VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clinic.cat_diagnosticos IS 'NOM-024: Catálogo de diagnósticos CIE-10 - Structure ready for official data';
COMMENT ON COLUMN clinic.cat_diagnosticos.codigo_cie10 IS 'CIE-10 code (e.g., B35.1 for nail fungus)';

CREATE INDEX IF NOT EXISTS idx_cat_diagnosticos_codigo ON clinic.cat_diagnosticos(codigo_cie10);
CREATE INDEX IF NOT EXISTS idx_cat_diagnosticos_activo ON clinic.cat_diagnosticos(activo) WHERE activo = TRUE;

-- Procedures catalog
CREATE TABLE IF NOT EXISTS clinic.cat_procedimientos (
    id BIGSERIAL PRIMARY KEY,
    codigo VARCHAR(20) UNIQUE NOT NULL,
    descripcion VARCHAR(500) NOT NULL,
    duracion_estimada_min INTEGER,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clinic.cat_procedimientos IS 'NOM-024: Catálogo de procedimientos médicos - Structure ready';
COMMENT ON COLUMN clinic.cat_procedimientos.duracion_estimada_min IS 'Estimated duration in minutes for scheduling';

CREATE INDEX IF NOT EXISTS idx_cat_procedimientos_codigo ON clinic.cat_procedimientos(codigo);
CREATE INDEX IF NOT EXISTS idx_cat_procedimientos_activo ON clinic.cat_procedimientos(activo) WHERE activo = TRUE;

-- Medications catalog (Cuadro Básico)
CREATE TABLE IF NOT EXISTS clinic.cat_medicamentos (
    id BIGSERIAL PRIMARY KEY,
    clave_cuadro_basico VARCHAR(20) UNIQUE,
    nombre_generico VARCHAR(200) NOT NULL,
    nombre_comercial VARCHAR(200),
    presentacion VARCHAR(100),
    concentracion VARCHAR(50),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE clinic.cat_medicamentos IS 'NOM-024: Catálogo de medicamentos según Cuadro Básico - Structure ready';
COMMENT ON COLUMN clinic.cat_medicamentos.clave_cuadro_basico IS 'Official Cuadro Básico key (when available)';
COMMENT ON COLUMN clinic.cat_medicamentos.nombre_generico IS 'Generic name (required)';

CREATE INDEX IF NOT EXISTS idx_cat_medicamentos_clave ON clinic.cat_medicamentos(clave_cuadro_basico) WHERE clave_cuadro_basico IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cat_medicamentos_activo ON clinic.cat_medicamentos(activo) WHERE activo = TRUE;

-- ============================================================================
-- CLINICA_OPS_DB: Operations Schema Changes
-- ============================================================================

\c clinica_ops_db

-- ----------------------------------------------------------------------------
-- 9. Add professional identification field to podologos
-- ----------------------------------------------------------------------------
ALTER TABLE ops.podologos
    ADD COLUMN IF NOT EXISTS institucion_titulo VARCHAR(200);

COMMENT ON COLUMN ops.podologos.institucion_titulo IS 'NOM-024: Institución que otorgó el título profesional - Optional now, mandatory for official reports';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================
-- Run these queries to verify the migration succeeded

\c clinica_auth_db
SELECT 
    'auth.audit_logs_inmutable' as table_name,
    COUNT(*) as count
FROM auth.audit_logs_inmutable
UNION ALL
SELECT 
    'auth.access_logs',
    COUNT(*)
FROM auth.access_logs
UNION ALL
SELECT 
    'auth.permisos',
    COUNT(*)
FROM auth.permisos;

\c clinica_core_db
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'clinic' 
    AND table_name = 'pacientes'
    AND column_name IN ('curp', 'segundo_apellido', 'consentimiento_intercambio')
ORDER BY column_name;

SELECT 
    'clinic.cat_diagnosticos' as table_name,
    COUNT(*) as count
FROM clinic.cat_diagnosticos
UNION ALL
SELECT 
    'clinic.cat_procedimientos',
    COUNT(*)
FROM clinic.cat_procedimientos
UNION ALL
SELECT 
    'clinic.cat_medicamentos',
    COUNT(*)
FROM clinic.cat_medicamentos;

\c clinica_ops_db
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'podologos'
    AND column_name = 'institucion_titulo';

-- ============================================================================
-- ROLLBACK (if needed)
-- ============================================================================
-- Uncomment and run this section to rollback changes

/*
\c clinica_auth_db
DROP TRIGGER IF EXISTS protect_audit_log ON auth.audit_logs_inmutable;
DROP FUNCTION IF EXISTS auth.prevent_audit_modification();
DROP TABLE IF EXISTS auth.audit_logs_inmutable CASCADE;
DROP TABLE IF EXISTS auth.access_logs CASCADE;
DROP TABLE IF EXISTS auth.rol_permisos CASCADE;
DROP TABLE IF EXISTS auth.permisos CASCADE;
ALTER TABLE auth.clinicas DROP COLUMN IF EXISTS clues;

\c clinica_core_db
ALTER TABLE clinic.pacientes 
    DROP COLUMN IF EXISTS curp,
    DROP COLUMN IF EXISTS segundo_apellido,
    DROP COLUMN IF EXISTS estado_nacimiento,
    DROP COLUMN IF EXISTS nacionalidad,
    DROP COLUMN IF EXISTS estado_residencia,
    DROP COLUMN IF EXISTS municipio_residencia,
    DROP COLUMN IF EXISTS localidad_residencia,
    DROP COLUMN IF EXISTS consentimiento_intercambio,
    DROP COLUMN IF EXISTS fecha_consentimiento;

ALTER TABLE clinic.tratamientos
    DROP COLUMN IF EXISTS firma_electronica,
    DROP COLUMN IF EXISTS firma_timestamp,
    DROP COLUMN IF EXISTS firma_tipo;

ALTER TABLE clinic.evoluciones_clinicas
    DROP COLUMN IF EXISTS firma_electronica,
    DROP COLUMN IF EXISTS firma_timestamp,
    DROP COLUMN IF EXISTS firma_tipo;

DROP TABLE IF EXISTS clinic.cat_diagnosticos CASCADE;
DROP TABLE IF EXISTS clinic.cat_procedimientos CASCADE;
DROP TABLE IF EXISTS clinic.cat_medicamentos CASCADE;

\c clinica_ops_db
ALTER TABLE ops.podologos DROP COLUMN IF EXISTS institucion_titulo;
*/

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
