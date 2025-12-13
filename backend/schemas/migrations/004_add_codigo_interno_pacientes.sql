-- ============================================================================
-- MIGRACIÓN 004: Agregar campo codigo_interno a pacientes
-- Fecha: 13 de diciembre de 2024
-- Descripción: Agrega el campo codigo_interno a la tabla pacientes para 
--              completar el sistema de IDs estructurados en todos los módulos
-- ============================================================================

-- Conectar a la base de datos clinica_core_db
\c clinica_core_db

-- Agregar columna codigo_interno a pacientes
ALTER TABLE clinic.pacientes 
ADD COLUMN IF NOT EXISTS codigo_interno VARCHAR(20) UNIQUE;

-- Crear índice para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_pacientes_codigo_interno 
ON clinic.pacientes(codigo_interno) 
WHERE codigo_interno IS NOT NULL;

-- Agregar comentario descriptivo
COMMENT ON COLUMN clinic.pacientes.codigo_interno IS 'Código interno estructurado: [2 letras apellido][2 letras nombre]-[MMDD]-[contador]. Ejemplo: RENO-1213-00001';

-- Verificar que la columna se haya agregado correctamente
SELECT 
    column_name, 
    data_type, 
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'clinic' 
    AND table_name = 'pacientes'
    AND column_name = 'codigo_interno';

\echo 'Migración 004 completada: codigo_interno agregado a clinic.pacientes';
