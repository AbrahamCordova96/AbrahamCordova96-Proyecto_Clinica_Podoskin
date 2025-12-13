-- Migración manual: Agregar campos NOM-024 a tablas existentes
-- Ejecutar: docker exec -i podoskin-db psql -U podoskin -d clinica_auth_db < migrate_add_nom024_fields.sql

-- 1. Agregar codigo_interno y clues a clinicas
ALTER TABLE auth.clinicas 
ADD COLUMN IF NOT EXISTS codigo_interno VARCHAR(20) UNIQUE,
ADD COLUMN IF NOT EXISTS clues VARCHAR(12) UNIQUE;

COMMENT ON COLUMN auth.clinicas.clues IS 'Clave Única de Establecimiento de Salud - Opcional ahora, obligatorio para certificación NOM-024';

-- 2. Agregar codigo_interno a sys_usuarios
ALTER TABLE auth.sys_usuarios 
ADD COLUMN IF NOT EXISTS codigo_interno VARCHAR(20) UNIQUE;

-- 3. Agregar campos de Gemini API Key a sys_usuarios
ALTER TABLE auth.sys_usuarios
ADD COLUMN IF NOT EXISTS gemini_api_key_encrypted VARCHAR(500),
ADD COLUMN IF NOT EXISTS gemini_api_key_updated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS gemini_api_key_last_validated TIMESTAMPTZ;

COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_encrypted IS 'API Key de Gemini encriptada con Fernet';
COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_updated_at IS 'Última actualización de la API Key';
COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_last_validated IS 'Última validación exitosa de la API Key';

-- 4. Crear tabla audit_logs_inmutable
CREATE TABLE IF NOT EXISTS auth.audit_logs_inmutable (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id BIGINT NOT NULL,
    username_snapshot VARCHAR(50) NOT NULL,
    tabla_afectada VARCHAR(100) NOT NULL,
    registro_id BIGINT NOT NULL,
    accion VARCHAR(20) NOT NULL,
    datos_antes JSONB,
    datos_despues JSONB,
    ip_address INET,
    razon_cambio VARCHAR(500)
);

COMMENT ON TABLE auth.audit_logs_inmutable IS 'Immutable audit log for NOM-024 compliance - append-only';

-- 5. Crear tabla access_logs
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

COMMENT ON TABLE auth.access_logs IS 'Log of read/access operations for NOM-024 compliance';

-- 6. Crear tabla permisos (preparación)
CREATE TABLE IF NOT EXISTS auth.permisos (
    id BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    descripcion VARCHAR(200),
    modulo VARCHAR(50),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 7. Crear tabla rol_permisos (preparación)
CREATE TABLE IF NOT EXISTS auth.rol_permisos (
    id BIGSERIAL PRIMARY KEY,
    rol VARCHAR(50) NOT NULL,
    permiso_id BIGINT REFERENCES auth.permisos(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. Crear tabla voice_transcripts
CREATE TABLE IF NOT EXISTS auth.voice_transcripts (
    id_transcript BIGSERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    user_id BIGINT REFERENCES auth.sys_usuarios(id_usuario) NOT NULL,
    user_text VARCHAR NOT NULL,
    assistant_text VARCHAR,
    timestamp TIMESTAMPTZ NOT NULL,
    langgraph_job_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_voice_transcripts_session ON auth.voice_transcripts(session_id);

-- 9. Trigger para hacer audit_logs_inmutable realmente inmutable
CREATE OR REPLACE FUNCTION auth.prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs_inmutable es append-only. No se permiten UPDATE ni DELETE';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS prevent_update_audit_log ON auth.audit_logs_inmutable;
CREATE TRIGGER prevent_update_audit_log
BEFORE UPDATE ON auth.audit_logs_inmutable
FOR EACH ROW EXECUTE FUNCTION auth.prevent_audit_log_modification();

DROP TRIGGER IF EXISTS prevent_delete_audit_log ON auth.audit_logs_inmutable;
CREATE TRIGGER prevent_delete_audit_log
BEFORE DELETE ON auth.audit_logs_inmutable
FOR EACH ROW EXECUTE FUNCTION auth.prevent_audit_log_modification();

-- 10. Actualizar clinica existente con código interno (si existe ya una clínica)
UPDATE auth.clinicas 
SET codigo_interno = 'PODO-1213-00001' 
WHERE id_clinica = 1 AND codigo_interno IS NULL;

COMMENT ON COLUMN auth.clinicas.codigo_interno IS 'Código interno estructurado: [4 letras nombre]-[MMDD]-[contador]';
COMMENT ON COLUMN auth.sys_usuarios.codigo_interno IS 'Código interno estructurado: [2 letras apellido][2 letras nombre]-[MMDD]-[contador]';

\echo 'Migración completada exitosamente';
