-- backend/schemas/migrations/002_add_gemini_api_key.sql
-- Migración: Agregar campos para API Key de Gemini en el modelo SysUsuario
-- Fecha: 2024-12-12
-- Autor: Agente Backend
-- Descripción: Permite que cada usuario del sistema almacene su propia API Key
--              de Google Gemini de forma segura (encriptada con Fernet)

-- Agregar las tres columnas nuevas al modelo SysUsuario
-- NOTA sobre VARCHAR(500):
-- - Fernet tokens para una API Key de ~40 caracteres generan ~180 caracteres encriptados
-- - Se usa VARCHAR(500) para tener margen de seguridad (2.7x el tamaño esperado)
-- - Esto permite API Keys más largas en el futuro sin necesidad de migración
-- - Alternativa: usar TEXT si se prefiere sin límite de tamaño
ALTER TABLE auth.sys_usuarios
ADD COLUMN IF NOT EXISTS gemini_api_key_encrypted VARCHAR(500),
ADD COLUMN IF NOT EXISTS gemini_api_key_updated_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS gemini_api_key_last_validated TIMESTAMPTZ;

-- Agregar comentarios a las columnas para documentación
COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_encrypted IS 'API Key de Gemini encriptada con Fernet - nunca se almacena en texto plano';
COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_updated_at IS 'Timestamp de la última actualización de la API Key por el usuario';
COMMENT ON COLUMN auth.sys_usuarios.gemini_api_key_last_validated IS 'Timestamp de la última validación exitosa contra la API de Google Gemini';

-- Crear índice parcial para optimizar búsquedas de usuarios con API Key configurada
-- El índice parcial solo incluye filas donde la API Key no es NULL, ahorrando espacio
CREATE INDEX IF NOT EXISTS idx_usuarios_gemini_key 
ON auth.sys_usuarios(id_usuario) 
WHERE gemini_api_key_encrypted IS NOT NULL;

-- Verificar que las columnas se hayan agregado correctamente
-- Comentar la siguiente línea si se ejecuta desde un script automatizado
-- \d auth.sys_usuarios
