-- =====================================================
-- Script SQL para inicializar BD limpia con admin
-- Ejecutar: psql -U podoskin -d clinica_auth_db -f init_admin.sql
-- =====================================================

-- 1. CREAR CLÍNICA
INSERT INTO auth.clinicas (
    nombre_clinica,
    direccion,
    telefono,
    activo,
    created_at,
    updated_at
) VALUES (
    'Podoskin Libertad',
    'Pendiente',
    'Pendiente',
    true,
    NOW(),
    NOW()
) ON CONFLICT DO NOTHING;

-- 2. CREAR USUARIO ADMINISTRADOR
-- Password hash para "Ornelas2025!"
INSERT INTO auth.sys_usuarios (
    username,
    email,
    hashed_password,
    rol,
    nombre_completo,
    activo,
    clinica_id,
    employee_id,
    created_at,
    updated_at
) VALUES (
    'santiago.ornelas',
    'admin@podoskin.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5eoWs3PqhIhSS', -- Ornelas2025!
    'Admin',
    'Santiago de Jesus Ornelas Reynoso',
    true,
    1,
    'ASGO-' || TO_CHAR(NOW(), 'MMDD') || '-00001',
    NOW(),
    NOW()
) ON CONFLICT (username) DO NOTHING;

-- 3. VERIFICAR
SELECT 
    u.id_usuario,
    u.username,
    u.employee_id,
    u.rol,
    u.nombre_completo,
    c.nombre_clinica
FROM auth.sys_usuarios u
LEFT JOIN auth.clinicas c ON u.clinica_id = c.id_clinica
WHERE u.username = 'santiago.ornelas';
