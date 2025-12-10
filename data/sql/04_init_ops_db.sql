-- =============================================================================
-- CLINICA_OPS_DB: Base de datos de Operaciones y Finanzas
-- PodoSkin v4.0 - Auditoría PostgreSQL Avanzada
-- =============================================================================
-- Esta base contiene:
--   Schema ops:
--     - Podólogos (profesionales)
--     - Catálogo de servicios
--     - Solicitudes de prospectos
--     - Citas (con EXCLUDE constraint anti-solapamiento)
--   Schema finance:
--     - Métodos de pago
--     - Pagos y transacciones
--     - Categorías de gasto
--     - Proveedores
--     - Gastos
-- =============================================================================

-- 1. EXTENSIONES
-- =============================================================================
CREATE EXTENSION IF NOT EXISTS btree_gist;  -- Para EXCLUDE constraint en citas

-- 2. SCHEMAS
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS finance;

-- =============================================================================
-- SCHEMA OPS: OPERACIONES Y AGENDA
-- =============================================================================

-- 3. PODÓLOGOS
-- =============================================================================
CREATE TABLE ops.podologos (
    id_podologo BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    usuario_sistema_id BIGINT,  -- FK a auth.sys_usuarios (validar en app)
    
    nombre_completo TEXT NOT NULL CHECK (char_length(nombre_completo) BETWEEN 3 AND 150),
    cedula_profesional TEXT UNIQUE CHECK (char_length(cedula_profesional) <= 50),
    especialidad TEXT DEFAULT 'Podología General',
    activo BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

COMMENT ON TABLE ops.podologos IS 
    'Profesionales que atienden pacientes. Vinculados a usuarios del sistema.';

-- 4. CATÁLOGO DE SERVICIOS
-- =============================================================================
CREATE TABLE ops.catalogo_servicios (
    id_servicio BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    
    nombre_servicio TEXT NOT NULL CHECK (char_length(nombre_servicio) BETWEEN 3 AND 100),
    descripcion TEXT,
    precio_base DECIMAL(10,2) NOT NULL CHECK (precio_base >= 0),
    duracion_minutos INT NOT NULL DEFAULT 30 CHECK (duracion_minutos > 0),
    requiere_seguimiento BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE ops.catalogo_servicios IS 
    'Catálogo de servicios que ofrece la clínica con precios base.';

-- 5. SOLICITUDES DE PROSPECTOS
-- =============================================================================
-- "Staging area" para leads que aún no son pacientes.
CREATE TABLE ops.solicitudes_prospectos (
    id_solicitud BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    
    nombre_prospecto TEXT CHECK (char_length(nombre_prospecto) <= 150),
    telefono_contacto TEXT CHECK (char_length(telefono_contacto) >= 10),
    motivo_visita_inicial TEXT,
    origen_contacto TEXT,

    fecha_solicitud TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    estado_prospecto TEXT DEFAULT 'Pendiente'
        CHECK (estado_prospecto IN ('Pendiente', 'Agendado', 'Convertido', 'Cancelado', 'No Show')),

    id_paciente_convertido BIGINT,  -- FK a clinic.pacientes (validar en app)
    created_by BIGINT               -- FK a auth.sys_usuarios (validar en app)
);

COMMENT ON TABLE ops.solicitudes_prospectos IS 
    'Leads/prospectos. Se convierten a pacientes tras primera cita realizada.';

-- 6. CITAS
-- =============================================================================
-- La agenda de la clínica. Usa EXCLUDE constraint para prevenir double-booking.
CREATE TABLE ops.citas (
    id_cita BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,

    paciente_id BIGINT,     -- FK a clinic.pacientes (validar en app)
    solicitud_id BIGINT REFERENCES ops.solicitudes_prospectos(id_solicitud),

    podologo_id BIGINT REFERENCES ops.podologos(id_podologo),
    servicio_id BIGINT REFERENCES ops.catalogo_servicios(id_servicio),

    fecha_cita DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,

    status TEXT DEFAULT 'Confirmada'
        CHECK (status IN ('Pendiente', 'Confirmada', 'En Sala', 'Realizada', 'Cancelada', 'No Asistió')),
    notas_agendamiento TEXT,

    created_by BIGINT,  -- FK a auth.sys_usuarios
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    -- Una cita debe tener O paciente O prospecto, no ambos
    CONSTRAINT chk_identidad_cita CHECK (
        (paciente_id IS NOT NULL)::INT + (solicitud_id IS NOT NULL)::INT = 1
    ),
    CONSTRAINT chk_duracion_valida CHECK (hora_fin > hora_inicio),
    CONSTRAINT chk_fecha_cita_valida CHECK (
        fecha_cita >= CURRENT_DATE - INTERVAL '2 years' AND
        fecha_cita <= CURRENT_DATE + INTERVAL '5 years'
    )
);

COMMENT ON TABLE ops.citas IS 
    'Agenda de citas. EXCLUDE constraint previene solapamientos.';
COMMENT ON COLUMN ops.citas.status IS 
    'Flujo: Pendiente → Confirmada → En Sala → Realizada. O: Cancelada/No Asistió';

-- EXCLUDE CONSTRAINT: Previene que un podólogo tenga 2 citas al mismo tiempo
-- Solo aplica a citas activas (no canceladas ni borradas)
ALTER TABLE ops.citas ADD CONSTRAINT exclude_solapamiento_citas
    EXCLUDE USING gist (
        podologo_id WITH =,
        fecha_cita WITH =,
        tsrange(
            (fecha_cita + hora_inicio)::timestamp,
            (fecha_cita + hora_fin)::timestamp
        ) WITH &&
    )
    WHERE (status NOT IN ('Cancelada', 'No Asistió') AND deleted_at IS NULL);

-- =============================================================================
-- SCHEMA FINANCE: FINANZAS Y GASTOS
-- =============================================================================

-- 7. MÉTODOS DE PAGO
-- =============================================================================
CREATE TABLE finance.metodos_pago (
    id_metodo BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    nombre TEXT NOT NULL UNIQUE,
    activo BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE finance.metodos_pago IS 
    'Catálogo de formas de pago aceptadas.';

-- Datos iniciales
INSERT INTO finance.metodos_pago (nombre) VALUES
('Efectivo'), ('Tarjeta Débito'), ('Tarjeta Crédito'),
('Transferencia'), ('Depósito');

-- 8. SERVICIOS PRESTADOS
-- =============================================================================
-- Relación N:M entre citas y servicios del catálogo.
-- Una cita puede tener múltiples servicios (consulta + limpieza + plantillas).
CREATE TABLE finance.servicios_prestados (
    id_servicio_prestado BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    
    cita_id BIGINT,              -- FK a ops.citas
    servicio_id BIGINT REFERENCES ops.catalogo_servicios(id_servicio) NOT NULL,
    tratamiento_id BIGINT,       -- FK a clinic.tratamientos (validar en app)

    cantidad INT DEFAULT 1 CHECK (cantidad > 0),
    precio_aplicado DECIMAL(10,2) NOT NULL CHECK (precio_aplicado >= 0),
    descuento DECIMAL(10,2) DEFAULT 0 CHECK (descuento >= 0),
    
    -- Subtotal calculado automáticamente (columna generada)
    subtotal DECIMAL(10,2) GENERATED ALWAYS AS (
        (precio_aplicado * cantidad) - descuento
    ) STORED,

    descuento_autorizado_por BIGINT,  -- FK a auth.sys_usuarios
    motivo_descuento TEXT,

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,

    CONSTRAINT chk_descuento_autorizado CHECK (
        descuento = 0 OR
        (descuento > 0 AND descuento_autorizado_por IS NOT NULL)
    ),
    CONSTRAINT chk_descuento_no_excede CHECK (
        descuento <= (precio_aplicado * cantidad)
    )
);

COMMENT ON TABLE finance.servicios_prestados IS 
    'Servicios realizados en cada cita. Precio al momento del servicio.';
COMMENT ON COLUMN finance.servicios_prestados.descuento_autorizado_por IS 
    'Quién autorizó el descuento. Requerido si descuento > 0.';

-- 9. PAGOS
-- =============================================================================
CREATE TABLE finance.pagos (
    id_pago BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    paciente_id BIGINT NOT NULL,  -- FK a clinic.pacientes

    fecha_emision TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    total_facturado DECIMAL(10,2) NOT NULL DEFAULT 0 CHECK (total_facturado >= 0),
    monto_pagado DECIMAL(10,2) DEFAULT 0 CHECK (monto_pagado >= 0),
    saldo_pendiente DECIMAL(10,2) DEFAULT 0 CHECK (saldo_pendiente >= 0),

    status_pago TEXT DEFAULT 'Pendiente' CHECK (
        status_pago IN ('Pendiente', 'Parcial', 'Pagado', 'Cancelado')
    ),
    notas TEXT,

    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ DEFAULT NULL
);

COMMENT ON TABLE finance.pagos IS 
    'Cabecera de factura/recibo. "El paciente debe X pesos".';
COMMENT ON COLUMN finance.pagos.status_pago IS 
    'Pendiente=adeudo total, Parcial=abonos, Pagado=liquidado, Cancelado=anulado.';

-- 10. DETALLES DE PAGO
-- =============================================================================
CREATE TABLE finance.pago_detalles (
    id_detalle BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    pago_id BIGINT REFERENCES finance.pagos(id_pago) ON DELETE CASCADE NOT NULL,
    servicio_prestado_id BIGINT REFERENCES finance.servicios_prestados(id_servicio_prestado) NOT NULL,
    monto_aplicado DECIMAL(10,2) NOT NULL CHECK (monto_aplicado > 0)
);

COMMENT ON TABLE finance.pago_detalles IS 
    'Qué servicios cubre cada pago. Permite pagos parciales.';

-- 11. TRANSACCIONES
-- =============================================================================
-- Movimientos reales de dinero (entrada de efectivo/transferencia).
CREATE TABLE finance.transacciones (
    id_transaccion BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    pago_id BIGINT REFERENCES finance.pagos(id_pago) NOT NULL,

    monto DECIMAL(10,2) NOT NULL CHECK (monto > 0),
    metodo_pago_id BIGINT REFERENCES finance.metodos_pago(id_metodo) NOT NULL,

    fecha TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    recibido_por BIGINT,  -- FK a auth.sys_usuarios
    notas TEXT,

    fecha_corte DATE DEFAULT CURRENT_DATE
);

COMMENT ON TABLE finance.transacciones IS 
    'Movimientos de caja. Cada entrada de dinero físico/electrónico.';

-- 12. CATEGORÍAS DE GASTO
-- =============================================================================
CREATE TABLE finance.categorias_gasto (
    id_categoria BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    
    nombre TEXT NOT NULL UNIQUE CHECK (char_length(nombre) BETWEEN 3 AND 100),
    descripcion TEXT,
    color_hex TEXT DEFAULT '#6B7280' CHECK (color_hex ~* '^#[0-9A-F]{6}$'),
    es_recurrente BOOLEAN DEFAULT FALSE,
    frecuencia_dias INT CHECK (frecuencia_dias > 0),
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE finance.categorias_gasto IS 
    'Tipos de gasto para clasificación y reportes.';

-- Datos iniciales
INSERT INTO finance.categorias_gasto (nombre, descripcion, color_hex, es_recurrente, frecuencia_dias) VALUES
('Renta', 'Alquiler del local de la clínica', '#EF4444', TRUE, 30),
('Servicios', 'Luz, agua, internet, teléfono, gas', '#F59E0B', TRUE, 30),
('Sueldos', 'Nómina y pagos a empleados', '#10B981', TRUE, 15),
('Insumos Médicos', 'Gasas, cremas, utensilios desechables', '#3B82F6', FALSE, NULL),
('Instrumentos', 'Herramientas y equipo médico', '#8B5CF6', FALSE, NULL),
('Comisiones', 'Pagos por comisión a colaboradores', '#EC4899', FALSE, NULL),
('Mantenimiento', 'Reparaciones y mantenimiento del local', '#6366F1', FALSE, NULL),
('Marketing', 'Publicidad, redes sociales, impresos', '#14B8A6', FALSE, NULL),
('Impuestos', 'ISR, IVA, contribuciones', '#F43F5E', TRUE, 30),
('Otros', 'Gastos no clasificados', '#6B7280', FALSE, NULL);

-- 13. PROVEEDORES
-- =============================================================================
CREATE TABLE finance.proveedores (
    id_proveedor BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,
    
    nombre TEXT NOT NULL CHECK (char_length(nombre) BETWEEN 3 AND 150),
    nombre_corto TEXT CHECK (char_length(nombre_corto) <= 50),
    rfc TEXT CHECK (rfc IS NULL OR char_length(rfc) BETWEEN 12 AND 13),
    telefono TEXT CHECK (telefono IS NULL OR char_length(telefono) >= 10),
    email TEXT CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    direccion TEXT,
    categoria_principal BIGINT REFERENCES finance.categorias_gasto(id_categoria),
    notas TEXT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE finance.proveedores IS 
    'Catálogo de proveedores para gastos. Útil para reportes.';

-- Datos iniciales
INSERT INTO finance.proveedores (nombre, nombre_corto, categoria_principal) VALUES
('Arrendador Local', 'Renta', 1),
('CFE Comisión Federal de Electricidad', 'CFE', 2),
('JAPAC / Agua', 'Agua', 2),
('Telmex / Internet', 'Internet', 2);

-- 14. GASTOS
-- =============================================================================
CREATE TABLE finance.gastos (
    id_gasto BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    id_clinica BIGINT DEFAULT 1,

    categoria_id BIGINT NOT NULL REFERENCES finance.categorias_gasto(id_categoria),
    proveedor_id BIGINT REFERENCES finance.proveedores(id_proveedor),

    monto DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    iva DECIMAL(12,2) DEFAULT 0 CHECK (iva >= 0),
    
    -- Monto total calculado automáticamente
    monto_total DECIMAL(12,2) GENERATED ALWAYS AS (
        monto + COALESCE(iva, 0)
    ) STORED,

    metodo_pago_id BIGINT REFERENCES finance.metodos_pago(id_metodo),
    referencia_pago TEXT,

    concepto TEXT NOT NULL,
    notas TEXT,
    comprobante_url TEXT,
    numero_factura TEXT,

    fecha_gasto DATE NOT NULL DEFAULT CURRENT_DATE,
    fecha_pago DATE,

    es_pago_recurrente BOOLEAN DEFAULT FALSE,
    gasto_origen_id BIGINT REFERENCES finance.gastos(id_gasto),

    status TEXT DEFAULT 'Pagado' CHECK (
        status IN ('Pendiente', 'Pagado', 'Cancelado')
    ),

    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_by BIGINT,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_by BIGINT,
    deleted_at TIMESTAMPTZ DEFAULT NULL,

    CONSTRAINT chk_iva_no_mayor CHECK (iva <= monto),
    CONSTRAINT chk_fecha_logica CHECK (fecha_pago IS NULL OR fecha_pago >= fecha_gasto)
);

COMMENT ON TABLE finance.gastos IS 
    'Registro de egresos. Complementa el módulo de ingresos.';
COMMENT ON COLUMN finance.gastos.monto_total IS 
    'Monto + IVA. Calculado automáticamente.';

-- 15. SERVICIOS BÁSICOS DEL CATÁLOGO
-- =============================================================================
INSERT INTO ops.catalogo_servicios (nombre_servicio, precio_base, duracion_minutos) VALUES
('Consulta Primera Vez', 400.00, 45),
('Consulta Seguimiento', 300.00, 30),
('Limpieza Profunda', 250.00, 45),
('Tratamiento Onicomicosis', 600.00, 60),
('Plantillas Ortopédicas', 1200.00, 90);

-- 16. ÍNDICES DE RENDIMIENTO
-- =============================================================================

-- Agenda
CREATE INDEX idx_citas_fecha ON ops.citas(fecha_cita);
CREATE INDEX idx_citas_podologo ON ops.citas(podologo_id);
CREATE INDEX idx_citas_paciente ON ops.citas(paciente_id);
CREATE INDEX idx_citas_clinica ON ops.citas(id_clinica);
CREATE INDEX idx_agenda_podologo_hoy ON ops.citas(podologo_id, fecha_cita)
    WHERE status IN ('Confirmada', 'En Sala') AND deleted_at IS NULL;

-- Finanzas
CREATE INDEX idx_pagos_paciente ON finance.pagos(paciente_id);
CREATE INDEX idx_pagos_fecha ON finance.pagos(fecha_emision);
CREATE INDEX idx_pagos_clinica ON finance.pagos(id_clinica);
CREATE INDEX idx_pagos_pendientes ON finance.pagos(paciente_id)
    WHERE saldo_pendiente > 0 AND deleted_at IS NULL;
CREATE INDEX idx_transacciones_pago ON finance.transacciones(pago_id);
CREATE INDEX idx_transacciones_fecha ON finance.transacciones(fecha);

-- Gastos
CREATE INDEX idx_gastos_categoria ON finance.gastos(categoria_id);
CREATE INDEX idx_gastos_proveedor ON finance.gastos(proveedor_id);
CREATE INDEX idx_gastos_fecha ON finance.gastos(fecha_gasto DESC);
CREATE INDEX idx_gastos_mes ON finance.gastos(DATE_TRUNC('month', fecha_gasto));
CREATE INDEX idx_gastos_pendientes ON finance.gastos(fecha_gasto)
    WHERE status = 'Pendiente' AND deleted_at IS NULL;

-- 17. VISTAS
-- =============================================================================

-- Citas activas (para agenda)
CREATE OR REPLACE VIEW ops.v_citas_activas AS
SELECT 
    id_cita, paciente_id, solicitud_id, podologo_id, servicio_id,
    fecha_cita, hora_inicio, hora_fin, status, notas_agendamiento
FROM ops.citas
WHERE deleted_at IS NULL 
  AND status NOT IN ('Cancelada', 'No Asistió');

COMMENT ON VIEW ops.v_citas_activas IS 
    'Citas activas (no borradas ni canceladas). Para mostrar agenda.';

-- Podólogos activos
CREATE OR REPLACE VIEW ops.v_podologos_activos AS
SELECT 
    id_podologo, usuario_sistema_id, nombre_completo, cedula_profesional,
    especialidad
FROM ops.podologos
WHERE deleted_at IS NULL AND activo = TRUE;

COMMENT ON VIEW ops.v_podologos_activos IS 
    'Podólogos activos. Para selectores en agenda.';

-- Saldos pendientes
CREATE OR REPLACE VIEW finance.v_saldos_pendientes AS
SELECT 
    paciente_id,
    SUM(saldo_pendiente) AS deuda_total,
    MIN(fecha_emision) AS deuda_desde,
    COUNT(id_pago) AS facturas_pendientes
FROM finance.pagos
WHERE saldo_pendiente > 0 
  AND status_pago IN ('Pendiente', 'Parcial')
  AND deleted_at IS NULL
GROUP BY paciente_id
ORDER BY deuda_total DESC;

COMMENT ON VIEW finance.v_saldos_pendientes IS 
    'Pacientes con deuda pendiente, ordenados por monto.';

-- Gastos por categoría
CREATE OR REPLACE VIEW finance.v_gastos_por_categoria AS
SELECT 
    c.nombre AS categoria,
    c.color_hex,
    COUNT(*) AS num_gastos,
    SUM(g.monto_total) AS total_gastado,
    AVG(g.monto_total) AS promedio_gasto,
    MAX(g.fecha_gasto) AS ultimo_gasto
FROM finance.gastos g
JOIN finance.categorias_gasto c ON g.categoria_id = c.id_categoria
WHERE g.deleted_at IS NULL AND g.status != 'Cancelado'
GROUP BY c.id_categoria, c.nombre, c.color_hex
ORDER BY total_gastado DESC;

COMMENT ON VIEW finance.v_gastos_por_categoria IS 
    'Resumen de gastos agrupados por categoría.';

-- 18. CONFIGURAR TIMEOUT
-- =============================================================================
ALTER DATABASE clinica_ops_db SET idle_in_transaction_session_timeout = '5min';

-- =============================================================================
-- FIN DE CLINICA_OPS_DB
-- =============================================================================
