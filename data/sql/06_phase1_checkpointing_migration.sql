-- =============================================================================
-- Migration: Fase 1 - Memoria Episódica (Checkpointing)
-- Description: Crea tabla para almacenar checkpoints de LangGraph
-- Database: clinica_auth_db
-- Date: 2025-12-11
-- =============================================================================
-- 
-- NOTA IMPORTANTE:
-- Esta tabla será creada AUTOMÁTICAMENTE por LangGraph cuando se llame
-- a PostgresSaver.setup(). Este archivo es solo para documentación.
-- 
-- LangGraph creará la tabla con el siguiente esquema:
-- =============================================================================

BEGIN;

-- Tabla de checkpoints para memoria episódica de LangGraph
-- Esta tabla almacena el estado completo del grafo en cada punto de ejecución
CREATE TABLE IF NOT EXISTS public.checkpoints (
    thread_id VARCHAR NOT NULL,          -- Identificador único del hilo de conversación
    checkpoint_id VARCHAR NOT NULL,      -- ID del checkpoint específico
    parent_id VARCHAR,                   -- ID del checkpoint padre (para árbol de estados)
    checkpoint JSONB NOT NULL,           -- Estado completo del AgentState serializado
    metadata JSONB,                      -- Metadata adicional (timestamp, user_id, etc.)
    PRIMARY KEY (thread_id, checkpoint_id)
);

-- Índices para optimizar consultas
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread 
    ON public.checkpoints(thread_id);

CREATE INDEX IF NOT EXISTS idx_checkpoints_parent 
    ON public.checkpoints(parent_id);

-- Comentarios explicativos
COMMENT ON TABLE public.checkpoints IS 
    'Almacena checkpoints del grafo LangGraph para memoria episódica. Creada y gestionada por PostgresSaver.';

COMMENT ON COLUMN public.checkpoints.thread_id IS 
    'Identificador único del hilo de conversación. Formato: {user_id}_{origin}_{uuid}';

COMMENT ON COLUMN public.checkpoints.checkpoint_id IS 
    'Identificador único del checkpoint. Generado automáticamente por LangGraph.';

COMMENT ON COLUMN public.checkpoints.parent_id IS 
    'ID del checkpoint padre. Permite construir árbol de estados para branching.';

COMMENT ON COLUMN public.checkpoints.checkpoint IS 
    'Estado completo del AgentState serializado en formato JSONB. Incluye messages, intent, entities, etc.';

COMMENT ON COLUMN public.checkpoints.metadata IS 
    'Metadata adicional como timestamp, user_id, origin, etc.';

COMMIT;

-- =============================================================================
-- Verificación
-- =============================================================================

-- Verificar que la tabla existe
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public' 
    AND table_name = 'checkpoints';

-- Verificar índices
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public' 
    AND tablename = 'checkpoints'
ORDER BY indexname;

-- =============================================================================
-- Política de Retención (OPCIONAL)
-- =============================================================================

-- Función para limpiar checkpoints antiguos (ejecutar periódicamente)
-- Elimina checkpoints con más de 30 días de antigüedad

CREATE OR REPLACE FUNCTION cleanup_old_checkpoints(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    -- Eliminar checkpoints antiguos basándose en metadata
    WITH deleted AS (
        DELETE FROM public.checkpoints
        WHERE (metadata->>'timestamp')::TIMESTAMPTZ < (NOW() - (days_to_keep || ' days')::INTERVAL)
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_checkpoints IS 
    'Limpia checkpoints con más de N días de antigüedad. Ejecutar periódicamente con cron job.';

-- Ejemplo de uso:
-- SELECT cleanup_old_checkpoints(30);  -- Limpia checkpoints > 30 días

-- =============================================================================
-- Notas de Implementación
-- =============================================================================
/*
1. Esta tabla es gestionada por LangGraph mediante PostgresSaver
2. NO modificar manualmente los datos en esta tabla
3. Para limpiar datos antiguos, usar la función cleanup_old_checkpoints()
4. El formato de thread_id es: {user_id}_{origin}_{conversation_uuid}
   Ejemplo: "5_webapp_a1b2c3d4-e5f6-7890-g1h2-i3j4k5l6m7n8"
5. El checkpoint JSONB contiene el AgentState completo serializado
6. La política de retención por defecto es 30 días (ajustar según necesidad)
*/
