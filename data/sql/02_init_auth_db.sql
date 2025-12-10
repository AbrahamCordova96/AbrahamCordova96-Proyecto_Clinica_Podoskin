-- =============================================================================
-- CLINICA_AUTH_DB: Base de datos de Seguridad y Auditoría
-- PodoSkin v4.0 - Auditoría PostgreSQL Avanzada
-- =============================================================================
-- Esta base contiene:
--   - Usuarios del sistema (sys_usuarios)
--   - Registro de auditoría particionado (audit_log)
--   - Catálogo de clínicas (para multi-tenant futuro)
-- =============================================================================

-- 1. EXTENSIONES REQUERIDAS
-- =============================================================================
-- btree_gist: Para constraints de exclusión (anti-solapamiento de citas)
-- pg_trgm: Para búsqueda fuzzy con trigramas
-- Nota: pgsodium requiere instalación especial, usamos pgcrypto como fallback
CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 2. SCHEMA AUTH
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS auth;

-- 3. TABLA DE CLÍNICAS (Multi-tenant preparado)
-- =============================================================================
-- Piensa en esto como el "registro de sucursales".
-- Aunque ahora solo tienes una clínica, la estructura está lista para crecer.
CREATE TABLE auth.clinicas (
    id_clinica BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre TEXT NOT NULL,
    rfc TEXT,
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE auth.clinicas IS 
    'Catálogo de clínicas/sucursales. Permite escalar a multi-tenant.';

-- Insertar clínica principal
INSERT INTO auth.clinicas (nombre, rfc) VALUES ('Clínica Principal', 'XAXX010101000');

-- 4. TABLA DE USUARIOS DEL SISTEMA
-- =============================================================================
-- Los usuarios que pueden hacer login en el sistema.
-- Usa IDENTITY en lugar de SERIAL por recomendación de auditoría PostgreSQL.
CREATE TABLE auth.sys_usuarios (
    id_usuario BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    
    -- Credenciales
    nombre_usuario TEXT NOT NULL UNIQUE 
        CHECK (char_length(nombre_usuario) BETWEEN 3 AND 50),
    password_hash TEXT NOT NULL,
    
    -- Rol: Define qué puede hacer este usuario
    rol TEXT NOT NULL CHECK (rol IN ('Admin', 'Podologo', 'Recepcion')),
    activo BOOLEAN DEFAULT TRUE,
    
    -- RELACIÓN FALTANTE CON CLÍNICA (Corrección)
    clinica_id BIGINT REFERENCES auth.clinicas(id_clinica),    
    
    -- Contacto
    email TEXT UNIQUE 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    
    -- Seguridad
    last_login TIMESTAMPTZ,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    
    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE auth.sys_usuarios IS 
    'Usuarios con acceso al sistema. Password hasheado con bcrypt via pgcrypto.';
COMMENT ON COLUMN auth.sys_usuarios.rol IS 
    'Admin=todo, Podologo=clínico, Recepcion=agenda y pacientes básico.';

-- 5. AUDIT_LOG PARTICIONADO
-- =============================================================================
-- Registro inmutable de TODOS los cambios en tablas sensibles.
-- Particionado por mes para:
--   - Performance: Consultas solo tocan la partición relevante
--   - Mantenimiento: DROP de particiones viejas es instantáneo
CREATE TABLE auth.audit_log (
    id_log BIGINT GENERATED ALWAYS AS IDENTITY,
    tabla_afectada TEXT NOT NULL,
    registro_id BIGINT NOT NULL,
    accion TEXT NOT NULL CHECK (accion IN (
        'INSERT', 'UPDATE', 'DELETE', 
        'LOGIN_EXITOSO', 'LOGIN_FALLIDO', 'LOGIN_USUARIO_INACTIVO', 
        'LOGOUT', 'PASSWORD_CHANGE'
    )),
    usuario_id BIGINT REFERENCES auth.sys_usuarios(id_usuario),
    timestamp_accion TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP NOT NULL,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_address INET,
    
    PRIMARY KEY (id_log, timestamp_accion)
) PARTITION BY RANGE (timestamp_accion);

COMMENT ON TABLE auth.audit_log IS 
    'Registro de auditoría particionado por mes. Inmutable para cumplimiento legal.';

-- Particiones: Diciembre 2024 a Diciembre 2025
CREATE TABLE auth.audit_log_2024_12 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
CREATE TABLE auth.audit_log_2025_01 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE auth.audit_log_2025_02 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE auth.audit_log_2025_03 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE auth.audit_log_2025_04 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE auth.audit_log_2025_05 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE auth.audit_log_2025_06 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE auth.audit_log_2025_07 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE auth.audit_log_2025_08 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE auth.audit_log_2025_09 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE auth.audit_log_2025_10 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE auth.audit_log_2025_11 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE auth.audit_log_2025_12 PARTITION OF auth.audit_log
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- Configuración de autovacuum: Aplicar a particiones individuales
-- PostgreSQL 17 no permite SET storage_parameters en la tabla padre particionada
-- Los parámetros se heredan de las particiones si se necesita tuning específico

-- 6. FUNCIONES DE UTILIDAD
-- =============================================================================

-- Función para actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION auth.actualizar_timestamp()
RETURNS TRIGGER AS $$
DECLARE
    current_user_id BIGINT;
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;

    -- Intenta leer el usuario de la sesión
    BEGIN
        current_user_id := nullif(current_setting('app.current_user_id', true), '')::BIGINT;
        IF current_user_id IS NOT NULL THEN
            NEW.updated_by := current_user_id;
        END IF;
    EXCEPTION WHEN OTHERS THEN
        NULL;
    END;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auth.actualizar_timestamp IS 
    'Actualiza updated_at y updated_by automáticamente. Usar en triggers BEFORE UPDATE.';

-- Función de auditoría genérica
CREATE OR REPLACE FUNCTION auth.audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    current_user_id BIGINT;
    record_id BIGINT;
    full_table_name TEXT;
BEGIN
    full_table_name := TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME;
    
    BEGIN
        current_user_id := nullif(current_setting('app.current_user_id', true), '')::BIGINT;
    EXCEPTION WHEN OTHERS THEN
        current_user_id := NULL;
    END;

    -- Determinar ID del registro según tabla
    CASE TG_TABLE_NAME
        WHEN 'pacientes' THEN record_id := COALESCE(NEW.id_paciente, OLD.id_paciente);
        WHEN 'tratamientos' THEN record_id := COALESCE(NEW.id_tratamiento, OLD.id_tratamiento);
        WHEN 'evoluciones_clinicas' THEN record_id := COALESCE(NEW.id_evolucion, OLD.id_evolucion);
        WHEN 'historial_medico_general' THEN record_id := COALESCE(NEW.id_historial, OLD.id_historial);
        WHEN 'historial_gineco' THEN record_id := COALESCE(NEW.id_gineco, OLD.id_gineco);
        WHEN 'citas' THEN record_id := COALESCE(NEW.id_cita, OLD.id_cita);
        WHEN 'podologos' THEN record_id := COALESCE(NEW.id_podologo, OLD.id_podologo);
        WHEN 'catalogo_servicios' THEN record_id := COALESCE(NEW.id_servicio, OLD.id_servicio);
        WHEN 'gastos' THEN record_id := COALESCE(NEW.id_gasto, OLD.id_gasto);
        WHEN 'categorias_gasto' THEN record_id := COALESCE(NEW.id_categoria, OLD.id_categoria);
        WHEN 'proveedores' THEN record_id := COALESCE(NEW.id_proveedor, OLD.id_proveedor);
        WHEN 'pagos' THEN record_id := COALESCE(NEW.id_pago, OLD.id_pago);
        ELSE record_id := 0;
    END CASE;

    IF (TG_OP = 'DELETE') THEN
        INSERT INTO auth.audit_log(tabla_afectada, registro_id, accion, usuario_id, datos_anteriores)
        VALUES (full_table_name, record_id, 'DELETE', current_user_id, row_to_json(OLD));
        RETURN OLD;
    ELSIF (TG_OP = 'UPDATE') THEN
        INSERT INTO auth.audit_log(tabla_afectada, registro_id, accion, usuario_id, datos_anteriores, datos_nuevos)
        VALUES (full_table_name, record_id, 'UPDATE', current_user_id, row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSIF (TG_OP = 'INSERT') THEN
        INSERT INTO auth.audit_log(tabla_afectada, registro_id, accion, usuario_id, datos_nuevos)
        VALUES (full_table_name, record_id, 'INSERT', current_user_id, row_to_json(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auth.audit_trigger_func IS 
    'Registra cambios en audit_log. Usar en triggers AFTER INSERT/UPDATE/DELETE.';

-- Función de verificación de password
CREATE OR REPLACE FUNCTION auth.verificar_password(
    p_usuario TEXT,
    p_password TEXT
) RETURNS BOOLEAN AS $$
DECLARE
    stored_hash TEXT;
BEGIN
    SELECT password_hash INTO stored_hash
    FROM auth.sys_usuarios
    WHERE nombre_usuario = p_usuario AND activo = TRUE;

    IF stored_hash IS NULL THEN
        -- Simular tiempo de procesamiento para evitar timing attacks
        PERFORM crypt('dummy_password', gen_salt('bf'));
        RETURN FALSE;
    END IF;
    
    RETURN crypt(p_password, stored_hash) = stored_hash;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

COMMENT ON FUNCTION auth.verificar_password IS 
    'Verifica credenciales de login. Uso: SELECT auth.verificar_password(''admin'', ''pass'')';

-- 7. ÍNDICES
-- =============================================================================
CREATE INDEX idx_audit_tabla_registro ON auth.audit_log(tabla_afectada, registro_id);
CREATE INDEX idx_audit_usuario ON auth.audit_log(usuario_id);
CREATE INDEX idx_audit_timestamp ON auth.audit_log(timestamp_accion DESC);

-- 8. USUARIO ADMIN INICIAL
-- =============================================================================
-- ⚠️ PASSWORD TEMPORAL: 'Admin2024!' - DEBE CAMBIARSE EN PRIMER LOGIN
INSERT INTO auth.sys_usuarios (nombre_usuario, password_hash, rol, activo, email, clinica_id)
VALUES (
    'admin',
    crypt('Admin2024!', gen_salt('bf')),
    'Admin',
    TRUE,
    'admin@podoskin.local',
    1 -- Asumiendo que la primera clínica creada tendrá ID 1
);

-- 9. CONFIGURAR TIMEOUT PARA PREVENIR BLOAT
-- =============================================================================
ALTER DATABASE clinica_auth_db SET idle_in_transaction_session_timeout = '5min';

-- =============================================================================
-- FIN DE CLINICA_AUTH_DB
-- =============================================================================
