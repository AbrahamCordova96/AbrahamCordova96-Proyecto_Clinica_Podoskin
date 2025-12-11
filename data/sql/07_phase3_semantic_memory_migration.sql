-- =============================================================================
-- Migration: Fase 3 - Memoria Semántica con pgvector
-- Description: Crea tabla para almacenar conversaciones con embeddings vectoriales
-- Database: clinica_auth_db
-- Date: 2025-12-11
-- =============================================================================

BEGIN;

-- Instalar extension pgvector si no existe
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla de memoria semántica para conversaciones
CREATE TABLE IF NOT EXISTS auth.conversation_memory (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    thread_id VARCHAR NOT NULL,
    origin VARCHAR(50) NOT NULL CHECK (origin IN ('webapp', 'whatsapp_paciente', 'whatsapp_user')),
    conversation_summary TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2 produces 384-dim vectors
    interaction_date TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    
    -- FK a sys_usuarios (puede ser NULL si es paciente)
    CONSTRAINT fk_conversation_user 
        FOREIGN KEY (user_id) 
        REFERENCES auth.sys_usuarios(id_usuario) 
        ON DELETE CASCADE
);

-- Índices para optimizar búsquedas
CREATE INDEX IF NOT EXISTS idx_conversation_memory_user 
    ON auth.conversation_memory(user_id);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_thread 
    ON auth.conversation_memory(thread_id);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_origin 
    ON auth.conversation_memory(origin);

CREATE INDEX IF NOT EXISTS idx_conversation_memory_date 
    ON auth.conversation_memory(interaction_date DESC);

-- Índice vectorial para búsqueda por similitud
-- Usando IVFFlat con 100 listas (ajustar según volumen de datos)
CREATE INDEX IF NOT EXISTS idx_conversation_memory_embedding 
    ON auth.conversation_memory 
    USING ivfflat (embedding vector_cosine_ops) 
    WITH (lists = 100);

-- Comentarios explicativos
COMMENT ON TABLE auth.conversation_memory IS 
    'Almacena resúmenes de conversaciones con embeddings para búsqueda semántica (Fase 3).';

COMMENT ON COLUMN auth.conversation_memory.user_id IS 
    'ID del usuario (sys_usuarios) o paciente. Puede ser NULL si es paciente no registrado.';

COMMENT ON COLUMN auth.conversation_memory.thread_id IS 
    'Thread ID de la conversación. Formato: {user_id}_{origin}_{uuid}';

COMMENT ON COLUMN auth.conversation_memory.origin IS 
    'Origen de la conversación: webapp, whatsapp_paciente, whatsapp_user';

COMMENT ON COLUMN auth.conversation_memory.conversation_summary IS 
    'Resumen generado de la conversación para embedding y búsqueda.';

COMMENT ON COLUMN auth.conversation_memory.embedding IS 
    'Vector de 384 dimensiones generado con sentence-transformers/all-MiniLM-L6-v2';

COMMENT ON COLUMN auth.conversation_memory.metadata IS 
    'Metadata adicional: intent, entities, topics, etc.';

COMMIT;

-- =============================================================================
-- Funciones de Utilidad
-- =============================================================================

-- Función para buscar conversaciones similares
CREATE OR REPLACE FUNCTION auth.search_similar_conversations(
    p_user_id BIGINT,
    p_query_embedding vector(384),
    p_limit INTEGER DEFAULT 5,
    p_similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    conversation_id BIGINT,
    thread_id VARCHAR,
    conversation_summary TEXT,
    similarity_score FLOAT,
    interaction_date TIMESTAMPTZ,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        cm.id,
        cm.thread_id,
        cm.conversation_summary,
        1 - (cm.embedding <=> p_query_embedding) AS similarity_score,
        cm.interaction_date,
        cm.metadata
    FROM auth.conversation_memory cm
    WHERE cm.user_id = p_user_id
        AND (1 - (cm.embedding <=> p_query_embedding)) >= p_similarity_threshold
    ORDER BY cm.embedding <=> p_query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auth.search_similar_conversations IS 
    'Busca las conversaciones más similares al query embedding dado. Retorna solo resultados con similitud >= threshold.';

-- Función para limpiar conversaciones antiguas
CREATE OR REPLACE FUNCTION auth.cleanup_old_conversations(days_to_keep INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    WITH deleted AS (
        DELETE FROM auth.conversation_memory
        WHERE interaction_date < (NOW() - (days_to_keep || ' days')::INTERVAL)
        RETURNING 1
    )
    SELECT COUNT(*) INTO deleted_count FROM deleted;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION auth.cleanup_old_conversations IS 
    'Limpia conversaciones con más de N días de antigüedad. Default: 90 días.';

-- =============================================================================
-- Verificación
-- =============================================================================

-- Verificar que la extensión está instalada
SELECT extname, extversion 
FROM pg_extension 
WHERE extname = 'vector';

-- Verificar que la tabla existe
SELECT 
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'auth' 
    AND table_name = 'conversation_memory';

-- Verificar índices
SELECT 
    indexname,
    tablename,
    indexdef
FROM pg_indexes
WHERE schemaname = 'auth' 
    AND tablename = 'conversation_memory'
ORDER BY indexname;

-- =============================================================================
-- Datos de Ejemplo (OPCIONAL - solo para testing)
-- =============================================================================

-- Insertar conversación de ejemplo
-- INSERT INTO auth.conversation_memory (
--     user_id,
--     thread_id,
--     origin,
--     conversation_summary,
--     embedding,
--     metadata
-- ) VALUES (
--     1,  -- Admin user
--     '1_webapp_test123',
--     'webapp',
--     'Usuario preguntó sobre pacientes diabéticos. Se mostró lista de 3 pacientes con tratamiento activo.',
--     '[0.1, 0.2, 0.3, ...]'::vector(384),  -- Replace with real embedding
--     '{"intent": "query_read", "entities": ["diabetes"], "patient_count": 3}'::jsonb
-- );

-- =============================================================================
-- Notas de Implementación
-- =============================================================================
/*
1. pgvector extension debe estar instalada en PostgreSQL (versión 11+)
2. El índice IVFFlat requiere que haya datos antes de ser efectivo
   - Con pocos datos (<1000 rows), usar búsqueda lineal es más rápido
   - Ajustar 'lists' parameter según volumen: lists ≈ sqrt(num_rows)
3. Embeddings se generan con sentence-transformers/all-MiniLM-L6-v2:
   - Modelo: 384 dimensiones
   - Idioma: Español funciona bien
   - Velocidad: ~400 textos/segundo en CPU
4. Similarity scoring:
   - Cosine distance: 0 = idéntico, 2 = opuesto
   - Similarity = 1 - distance
   - Threshold 0.7 es un buen punto de partida
5. Retention policy: 90 días por defecto (ajustar según necesidad)
6. Para pacientes, user_id puede ser NULL o usar ID de paciente
   (depende de la implementación de lookup_user_by_phone)
*/
