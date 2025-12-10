-- =============================================================================
-- CLINICA_CORE_DB: Base de datos de Datos Clínicos
-- PodoSkin v4.0 - Auditoría PostgreSQL Avanzada
-- =============================================================================
-- Esta base contiene:
--   - Pacientes (expedientes clínicos)
--   - Historial médico general y ginecológico
--   - Tratamientos y evoluciones clínicas
--   - Evidencia fotográfica
--   - Sesiones de IA
-- =============================================================================

-- 1. EXTENSIONES
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Para búsqueda fuzzy

-- 2. SCHEMA CLINIC
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS clinic;

-- 3. TABLA DE PACIENTES
-- =============================================================================
-- El corazón del sistema: todos los expedientes clínicos.
-- Usa TEXT en lugar de VARCHAR(n) por recomendación de auditoría PostgreSQL.
CREATE TABLE clinic.pacientes (
    id_paciente BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,  -- FK a auth.clinicas (validar en app)
    
    -- Datos personales
    nombres TEXT NOT NULL CHECK (char_length(nombres) BETWEEN 2 AND 100),
    apellidos TEXT NOT NULL CHECK (char_length(apellidos) BETWEEN 2 AND 100),
    fecha_nacimiento DATE NOT NULL,
    sexo CHAR(1) CHECK (sexo IN ('M', 'F')),

    -- Sociodemográficos
    estado_civil TEXT,
    ocupacion TEXT,
    escolaridad TEXT,
    religion TEXT,
    domicilio TEXT,
    como_supo_de_nosotros TEXT,

    -- Contacto
    telefono TEXT NOT NULL CHECK (char_length(telefono) >= 10),
    email TEXT CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),

    -- Auditoría
    fecha_registro TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT DEFAULT 1,  -- FK a auth.sys_usuarios (validar en app)
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    -- Validaciones
    CONSTRAINT chk_fecha_nacimiento_logica CHECK (
        fecha_nacimiento <= CURRENT_DATE AND 
        fecha_nacimiento >= '1900-01-01'
    )
);

COMMENT ON TABLE clinic.pacientes IS 
    'Expedientes clínicos. Solo ingresan después de primera consulta.';
COMMENT ON COLUMN clinic.pacientes.deleted_at IS 
    'Soft delete. NULL = activo, NOT NULL = borrado lógico.';

-- 4. HISTORIAL MÉDICO GENERAL
-- =============================================================================
-- Antecedentes heredofamiliares y personales patológicos.
-- IMC se calcula automáticamente como COLUMNA GENERADA (no trigger).
CREATE TABLE clinic.historial_medico_general (
    id_historial BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    paciente_id BIGINT UNIQUE REFERENCES clinic.pacientes(id_paciente) ON DELETE CASCADE,
    
    -- Antropometría
    peso_kg DECIMAL(5,2) CHECK (peso_kg > 0 AND peso_kg < 300),
    talla_cm DECIMAL(5,2) CHECK (talla_cm > 0 AND talla_cm < 250),
    
    -- IMC calculado automáticamente (columna generada)
    -- Fórmula: peso / (talla en metros)²
    imc DECIMAL(5,2) GENERATED ALWAYS AS (
        CASE 
            WHEN peso_kg IS NOT NULL AND talla_cm IS NOT NULL AND talla_cm > 0
            THEN ROUND(peso_kg / POWER(talla_cm / 100.0, 2), 2)
            ELSE NULL
        END
    ) STORED,
    
    tipos_sangre TEXT CHECK (tipos_sangre IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),

    -- Antecedentes Heredofamiliares (AHF)
    ahf_diabetes BOOLEAN DEFAULT FALSE,
    ahf_hipertension BOOLEAN DEFAULT FALSE,
    ahf_cancer BOOLEAN DEFAULT FALSE,
    ahf_cardiacas BOOLEAN DEFAULT FALSE,
    ahf_detalles TEXT,

    -- Antecedentes Personales Patológicos (APP)
    app_diabetes BOOLEAN DEFAULT FALSE,
    app_diabetes_inicio DATE,
    app_hipertension BOOLEAN DEFAULT FALSE,
    app_otras_patologias TEXT,

    -- Alergias
    alergias_activas BOOLEAN DEFAULT FALSE,
    lista_alergias TEXT,

    -- Hábitos
    tabaquismo BOOLEAN DEFAULT FALSE,
    alcoholismo BOOLEAN DEFAULT FALSE,
    actividad_fisica TEXT,

    CONSTRAINT chk_imc_coherente CHECK (imc IS NULL OR (imc >= 10 AND imc <= 60))
);

COMMENT ON TABLE clinic.historial_medico_general IS 
    'Antecedentes médicos del paciente. IMC se calcula automáticamente.';
COMMENT ON COLUMN clinic.historial_medico_general.imc IS 
    'Índice de Masa Corporal. Calculado automáticamente: peso_kg / (talla_cm/100)²';

-- 5. HISTORIAL GINECOLÓGICO
-- =============================================================================
CREATE TABLE clinic.historial_gineco (
    id_gineco BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    paciente_id BIGINT UNIQUE REFERENCES clinic.pacientes(id_paciente) ON DELETE CASCADE,
    
    menarca_edad INT CHECK (menarca_edad BETWEEN 9 AND 18),
    ritmo_menstrual TEXT,
    fecha_ultima_menstruacion DATE,
    
    -- Fórmula obstétrica: G P C A
    gestas INT DEFAULT 0 CHECK (gestas >= 0),
    partos INT DEFAULT 0 CHECK (partos >= 0),
    cesareas INT DEFAULT 0 CHECK (cesareas >= 0),
    abortos INT DEFAULT 0 CHECK (abortos >= 0),
    embarazos_ectopicos INT DEFAULT 0 CHECK (embarazos_ectopicos >= 0),
    embarazos_multiples INT DEFAULT 0 CHECK (embarazos_multiples >= 0),
    
    anticonceptivos_actuales TEXT,
    
    -- Validación médica: gestas >= partos + cesáreas + abortos + ectópicos
    CONSTRAINT chk_gestas_coherente CHECK (
        gestas >= (
            COALESCE(partos, 0) +
            COALESCE(cesareas, 0) +
            COALESCE(abortos, 0) +
            COALESCE(embarazos_ectopicos, 0)
        )
    )
);

COMMENT ON TABLE clinic.historial_gineco IS 
    'Historial gineco-obstétrico. Solo para pacientes femeninas.';

-- 6. TRATAMIENTOS
-- =============================================================================
-- Una "carpeta" por problema del paciente.
-- Un paciente puede tener múltiples tratamientos simultáneos.
CREATE TABLE clinic.tratamientos (
    id_tratamiento BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    paciente_id BIGINT REFERENCES clinic.pacientes(id_paciente),
    
    motivo_consulta_principal TEXT NOT NULL,
    diagnostico_inicial TEXT,
    fecha_inicio DATE DEFAULT CURRENT_DATE,
    estado_tratamiento TEXT DEFAULT 'En Curso'
        CHECK (estado_tratamiento IN ('En Curso', 'Alta', 'Pausado', 'Abandonado')),
    plan_general TEXT,

    -- Auditoría
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

COMMENT ON TABLE clinic.tratamientos IS 
    'Carpetas de tratamiento por problema. Un paciente puede tener varios simultáneos.';

-- 7. EVOLUCIONES CLÍNICAS (NOTAS SOAP)
-- =============================================================================
CREATE TABLE clinic.evoluciones_clinicas (
    id_evolucion BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    tratamiento_id BIGINT REFERENCES clinic.tratamientos(id_tratamiento),
    cita_id BIGINT,       -- FK a ops.citas (validar en app)
    podologo_id BIGINT,   -- FK a ops.podologos (validar en app)

    fecha_visita TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,

    -- Notas SOAP
    nota_subjetiva TEXT,    -- S: Lo que el paciente dice
    nota_objetiva TEXT,     -- O: Lo que el podólogo observa
    analisis_texto TEXT,    -- A: Análisis/diagnóstico
    plan_texto TEXT,        -- P: Plan de tratamiento

    -- Signos vitales en JSON flexible
    signos_vitales_visita JSONB,
    created_by BIGINT,
    
    -- Validaciones JSONB para signos vitales
    CONSTRAINT chk_signos_frecuencia CHECK (
        signos_vitales_visita IS NULL OR
        NOT (signos_vitales_visita ? 'frecuencia_cardiaca') OR
        (
            (signos_vitales_visita->>'frecuencia_cardiaca')::NUMERIC >= 40 AND
            (signos_vitales_visita->>'frecuencia_cardiaca')::NUMERIC <= 200
        )
    ),
    CONSTRAINT chk_signos_temperatura CHECK (
        signos_vitales_visita IS NULL OR
        NOT (signos_vitales_visita ? 'temperatura') OR
        (
            (signos_vitales_visita->>'temperatura')::NUMERIC >= 35 AND
            (signos_vitales_visita->>'temperatura')::NUMERIC <= 42
        )
    ),
    CONSTRAINT chk_signos_glucosa CHECK (
        signos_vitales_visita IS NULL OR
        NOT (signos_vitales_visita ? 'glucosa') OR
        (
            (signos_vitales_visita->>'glucosa')::NUMERIC >= 50 AND
            (signos_vitales_visita->>'glucosa')::NUMERIC <= 400
        )
    )
);

COMMENT ON TABLE clinic.evoluciones_clinicas IS 
    'Notas SOAP por visita. Vinculadas a un tratamiento específico.';
COMMENT ON COLUMN clinic.evoluciones_clinicas.signos_vitales_visita IS 
    'JSON: {presion_arterial: "120/80", frecuencia_cardiaca: 40-200, temperatura: 35-42, glucosa: 50-400}';

-- 8. EVIDENCIA FOTOGRÁFICA
-- =============================================================================
CREATE TABLE clinic.evidencia_fotografica (
    id_evidencia BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    evolucion_id BIGINT REFERENCES clinic.evoluciones_clinicas(id_evolucion),
    
    tipo_archivo TEXT,
    etapa_tratamiento TEXT,
    url_archivo TEXT NOT NULL,
    analisis_visual_ia JSONB,
    comentarios_medico TEXT,
    fecha_captura TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE clinic.evidencia_fotografica IS 
    'Fotos de antes/durante/después del tratamiento.';

-- 9. SESIONES IA
-- =============================================================================
CREATE TABLE clinic.sesiones_ia_conversacion (
    id_sesion_ia BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    cita_id BIGINT,  -- FK a ops.citas
    
    url_audio_full TEXT,
    duracion_segundos INT CHECK (duracion_segundos > 0),
    transcripcion_estructurada JSONB,
    resumen_generado TEXT,
    sentimiento_paciente TEXT CHECK (sentimiento_paciente IN ('Positivo', 'Neutral', 'Negativo', 'Mixto', 'Urgente')),
    puntos_clave_detectados TEXT[],
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE clinic.sesiones_ia_conversacion IS 
    'Transcripciones de consultas procesadas por IA.';

-- 10. ÍNDICES DE RENDIMIENTO
-- =============================================================================

-- Búsqueda por nombre
CREATE INDEX idx_pacientes_nombre ON clinic.pacientes(apellidos, nombres);
CREATE INDEX idx_pacientes_telefono ON clinic.pacientes(telefono);
CREATE INDEX idx_pacientes_email ON clinic.pacientes(email) WHERE email IS NOT NULL;

-- Multi-tenant
CREATE INDEX idx_pacientes_clinica ON clinic.pacientes(id_clinica);

-- Búsqueda fuzzy con trigramas
CREATE INDEX idx_pacientes_apellidos_trgm ON clinic.pacientes USING GIN (apellidos gin_trgm_ops);
CREATE INDEX idx_pacientes_nombres_trgm ON clinic.pacientes USING GIN (nombres gin_trgm_ops);
CREATE INDEX idx_pacientes_telefono_trgm ON clinic.pacientes USING GIN (telefono gin_trgm_ops);

-- Tratamientos activos
CREATE INDEX idx_tratamientos_paciente ON clinic.tratamientos(paciente_id);
CREATE INDEX idx_tratamientos_en_curso ON clinic.tratamientos(paciente_id)
    WHERE estado_tratamiento = 'En Curso' AND deleted_at IS NULL;

-- Evoluciones
CREATE INDEX idx_evoluciones_tratamiento ON clinic.evoluciones_clinicas(tratamiento_id);
CREATE INDEX idx_evoluciones_fecha ON clinic.evoluciones_clinicas(fecha_visita DESC);

-- JSONB
CREATE INDEX idx_signos_gin ON clinic.evoluciones_clinicas USING GIN (signos_vitales_visita);
CREATE INDEX idx_transcripcion_gin ON clinic.sesiones_ia_conversacion USING GIN (transcripcion_estructurada);

-- Pacientes diabéticos (para alertas)
CREATE INDEX idx_pacientes_diabeticos ON clinic.historial_medico_general(paciente_id)
    WHERE app_diabetes = TRUE;

-- 11. FUNCIÓN DE BÚSQUEDA FUZZY
-- =============================================================================
CREATE OR REPLACE FUNCTION clinic.buscar_pacientes_fuzzy(
    p_termino TEXT,
    p_limite INT DEFAULT 20
) RETURNS TABLE (
    id_paciente BIGINT,
    nombre_completo TEXT,
    telefono TEXT,
    email TEXT,
    similitud REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id_paciente,
        (p.nombres || ' ' || p.apellidos)::TEXT AS nombre_completo,
        p.telefono,
        p.email,
        GREATEST(
            similarity(p.nombres, p_termino),
            similarity(p.apellidos, p_termino),
            similarity(p.telefono, p_termino)
        ) AS similitud
    FROM clinic.pacientes p
    WHERE p.deleted_at IS NULL
      AND (
          p.nombres % p_termino OR
          p.apellidos % p_termino OR
          p.telefono % p_termino OR
          p.nombres ILIKE '%' || p_termino || '%' OR
          p.apellidos ILIKE '%' || p_termino || '%' OR
          p.telefono ILIKE '%' || p_termino || '%'
      )
    ORDER BY similitud DESC
    LIMIT p_limite;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION clinic.buscar_pacientes_fuzzy IS 
    'Búsqueda fuzzy de pacientes. Uso: SELECT * FROM clinic.buscar_pacientes_fuzzy(''garcia'')';

-- 12. VISTAS
-- =============================================================================
CREATE OR REPLACE VIEW clinic.v_pacientes_activos AS
SELECT 
    id_paciente, nombres, apellidos, fecha_nacimiento, sexo,
    estado_civil, ocupacion, telefono, email, fecha_registro
FROM clinic.pacientes
WHERE deleted_at IS NULL;

COMMENT ON VIEW clinic.v_pacientes_activos IS 
    'Pacientes activos (no borrados). Usar para operaciones normales.';

CREATE OR REPLACE VIEW clinic.v_tratamientos_activos AS
SELECT 
    id_tratamiento, paciente_id, motivo_consulta_principal, diagnostico_inicial,
    fecha_inicio, estado_tratamiento, plan_general
FROM clinic.tratamientos
WHERE deleted_at IS NULL;

COMMENT ON VIEW clinic.v_tratamientos_activos IS 
    'Tratamientos activos (no borrados).';

-- 13. CONFIGURAR TIMEOUT
-- =============================================================================
ALTER DATABASE clinica_core_db SET idle_in_transaction_session_timeout = '5min';

-- =============================================================================
-- FIN DE CLINICA_CORE_DB
-- =============================================================================
