# 🤖 PROMPT COMPLETO - Construcción de Agente LangGraph para PodoSkin

## Instrucciones para el LLM

Eres un experto en LangGraph, LangChain y arquitectura de agentes conversacionales. Tu tarea es construir un sistema completo de consultas en lenguaje natural para una clínica podológica.

**IMPORTANTE:** 
- Tienes libre albedrío para decidir la implementación óptima
- Usa las mejores prácticas de LangGraph 0.2+
- El código debe ser production-ready, no esqueletos
- Incluye manejo de errores robusto
- Documenta cada decisión de diseño

---

## 1. CONTEXTO DEL PROYECTO

### 1.1 Descripción General
**PodoSkin** es un sistema de gestión clínica podológica con:
- **Backend:** FastAPI (Python 3.12) + SQLAlchemy 2.0.44
- **Base de Datos:** PostgreSQL 17 con 3 databases separadas
- **Autenticación:** JWT + RBAC (3 roles: Admin, Podologo, Recepcion)
- **Estado actual:** 95 endpoints REST funcionando (93.7% operativos)
- **Extensiones PostgreSQL:** pg_trgm (fuzzy search), btree_gist (anti-overlap), pgcrypto (bcrypt)

### 1.2 Arquitectura de Base de Datos

#### Database 1: `clinica_auth_db` (schema: `auth`)
```sql
-- Clínicas (multi-tenant ready)
CREATE TABLE auth.clinicas (
    id_clinica BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    rfc VARCHAR(20),
    activa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usuarios del sistema
CREATE TABLE auth.sys_usuarios (
    id_usuario BIGSERIAL PRIMARY KEY,
    nombre_usuario VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('Admin', 'Podologo', 'Recepcion')),
    activo BOOLEAN DEFAULT TRUE,
    email VARCHAR(255) UNIQUE,
    last_login TIMESTAMPTZ,
    failed_login_attempts INT DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    clinica_id BIGINT REFERENCES auth.clinicas(id_clinica)
);

-- Auditoría (particionada por mes)
CREATE TABLE auth.audit_log (
    id_log BIGSERIAL,
    timestamp_accion TIMESTAMPTZ DEFAULT NOW(),
    tabla_afectada VARCHAR(100) NOT NULL,
    registro_id BIGINT NOT NULL,
    accion VARCHAR(50) NOT NULL,
    usuario_id BIGINT,
    datos_anteriores JSONB,
    datos_nuevos JSONB,
    ip_address VARCHAR(45),
    PRIMARY KEY (id_log, timestamp_accion)
) PARTITION BY RANGE (timestamp_accion);
```

#### Database 2: `clinica_core_db` (schema: `clinic`)
```sql
-- Pacientes
CREATE TABLE clinic.pacientes (
    id_paciente BIGSERIAL PRIMARY KEY,
    id_clinica BIGINT DEFAULT 1,
    nombres VARCHAR(100) NOT NULL,
    apellidos VARCHAR(100) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    sexo CHAR(1) CHECK (sexo IN ('M', 'F')),
    estado_civil VARCHAR(20),
    ocupacion VARCHAR(100),
    escolaridad VARCHAR(50),
    religion VARCHAR(50),
    domicilio TEXT,
    telefono VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    como_supo_de_nosotros VARCHAR(100),
    fecha_registro TIMESTAMPTZ DEFAULT NOW(),
    created_by BIGINT,
    updated_at TIMESTAMPTZ
);

-- Índice para búsqueda fuzzy
CREATE INDEX idx_pacientes_nombres_trgm ON clinic.pacientes 
    USING gin (nombres gin_trgm_ops);
CREATE INDEX idx_pacientes_apellidos_trgm ON clinic.pacientes 
    USING gin (apellidos gin_trgm_ops);

-- Historial médico
CREATE TABLE clinic.historial_medico (
    id_historial BIGSERIAL PRIMARY KEY,
    paciente_id BIGINT UNIQUE REFERENCES clinic.pacientes(id_paciente),
    peso_kg DECIMAL(5,2),
    talla_cm DECIMAL(5,2),
    imc DECIMAL(5,2) GENERATED ALWAYS AS (peso_kg / ((talla_cm/100)^2)) STORED,
    tipos_sangre VARCHAR(5),
    ahf_diabetes BOOLEAN DEFAULT FALSE,
    ahf_hipertension BOOLEAN DEFAULT FALSE,
    ahf_cancer BOOLEAN DEFAULT FALSE,
    ahf_cardiacas BOOLEAN DEFAULT FALSE,
    app_diabetes BOOLEAN DEFAULT FALSE,
    app_hipertension BOOLEAN DEFAULT FALSE,
    app_artritis BOOLEAN DEFAULT FALSE,
    medicamentos_actuales TEXT,
    alergias_conocidas TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Tratamientos (carpetas de problemas)
CREATE TABLE clinic.tratamientos (
    id_tratamiento BIGSERIAL PRIMARY KEY,
    paciente_id BIGINT REFERENCES clinic.pacientes(id_paciente),
    motivo_consulta_principal TEXT NOT NULL,
    diagnostico_inicial TEXT,
    plan_general TEXT,
    fecha_inicio DATE DEFAULT CURRENT_DATE,
    fecha_fin DATE,
    estado_tratamiento VARCHAR(20) DEFAULT 'Activo' 
        CHECK (estado_tratamiento IN ('Activo', 'En Curso', 'Completado', 'Abandonado')),
    created_by BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Evoluciones (notas clínicas SOAP)
CREATE TABLE clinic.evoluciones (
    id_evolucion BIGSERIAL PRIMARY KEY,
    tratamiento_id BIGINT REFERENCES clinic.tratamientos(id_tratamiento),
    fecha_evolucion TIMESTAMPTZ DEFAULT NOW(),
    subjetivo TEXT,           -- S: Lo que el paciente dice
    objetivo TEXT,            -- O: Lo que el médico observa
    analisis TEXT,            -- A: Diagnóstico/interpretación
    plan TEXT,                -- P: Plan de tratamiento
    signos_vitales JSONB,
    procedimientos_realizados TEXT,
    recetas_emitidas TEXT,
    proxima_cita DATE,
    podologo_id BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Evidencias fotográficas
CREATE TABLE clinic.evidencias (
    id_evidencia BIGSERIAL PRIMARY KEY,
    evolucion_id BIGINT REFERENCES clinic.evoluciones(id_evolucion),
    url_imagen TEXT NOT NULL,
    descripcion TEXT,
    tipo_imagen VARCHAR(50),
    fecha_captura TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alergias del paciente
CREATE TABLE clinic.alergias (
    id_alergia BIGSERIAL PRIMARY KEY,
    id_historial BIGINT REFERENCES clinic.historial_medico(id_historial),
    nombre VARCHAR(200) NOT NULL,
    tipo VARCHAR(50),
    observaciones TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Suplementos del paciente
CREATE TABLE clinic.suplementos (
    id_suplemento BIGSERIAL PRIMARY KEY,
    id_historial BIGINT REFERENCES clinic.historial_medico(id_historial),
    nombre VARCHAR(200) NOT NULL,
    dosis VARCHAR(100),
    frecuencia VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Antecedentes no patológicos
CREATE TABLE clinic.antecedentes_no_patologicos (
    id_antnp BIGSERIAL PRIMARY KEY,
    id_historial BIGINT REFERENCES clinic.historial_medico(id_historial),
    descripcion TEXT NOT NULL,
    tipo VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);

-- Conversaciones digitales
CREATE TABLE clinic.conversaciones_digitales (
    id_conversacion BIGSERIAL PRIMARY KEY,
    id_paciente BIGINT REFERENCES clinic.pacientes(id_paciente),
    canal VARCHAR(50) NOT NULL,  -- whatsapp, web, email, llamada
    remitente VARCHAR(100),
    mensaje TEXT NOT NULL,
    url_adjunto TEXT,
    leido BOOLEAN DEFAULT FALSE,
    fecha TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    deleted_at TIMESTAMPTZ
);
```

#### Database 3: `clinica_ops_db` (schemas: `ops` + `finance`)
```sql
-- Schema: ops

-- Podólogos
CREATE TABLE ops.podologos (
    id_podologo BIGSERIAL PRIMARY KEY,
    nombre_completo VARCHAR(200) NOT NULL,
    especialidad VARCHAR(100),
    cedula_profesional VARCHAR(50),
    usuario_sistema_id BIGINT,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Citas con anti-solapamiento
CREATE TABLE ops.citas (
    id_cita BIGSERIAL PRIMARY KEY,
    paciente_id BIGINT NOT NULL,
    podologo_id BIGINT REFERENCES ops.podologos(id_podologo),
    servicio_id BIGINT,
    fecha_hora_inicio TIMESTAMPTZ NOT NULL,
    fecha_hora_fin TIMESTAMPTZ NOT NULL,
    motivo TEXT,
    notas TEXT,
    estado VARCHAR(20) DEFAULT 'Programada' 
        CHECK (estado IN ('Programada', 'Confirmada', 'En Curso', 'Completada', 'Cancelada', 'No Asistio')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    EXCLUDE USING gist (
        podologo_id WITH =,
        tstzrange(fecha_hora_inicio, fecha_hora_fin) WITH &&
    ) WHERE (estado NOT IN ('Cancelada', 'No Asistio'))
);

-- Catálogo de servicios
CREATE TABLE ops.catalogo_servicios (
    id_servicio BIGSERIAL PRIMARY KEY,
    nombre_servicio VARCHAR(200) NOT NULL,
    descripcion TEXT,
    precio DECIMAL(10,2),
    duracion_minutos INT DEFAULT 30,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Prospectos/Leads
CREATE TABLE ops.solicitudes_prospectos (
    id_prospecto BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    telefono VARCHAR(20),
    email VARCHAR(255),
    mensaje TEXT,
    origen VARCHAR(50),
    estado VARCHAR(20) DEFAULT 'Nuevo' 
        CHECK (estado IN ('Nuevo', 'Contactado', 'Interesado', 'Convertido', 'Descartado')),
    fecha_solicitud TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

-- Schema: finance

-- Métodos de pago
CREATE TABLE finance.metodos_pago (
    id_metodo BIGSERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    activo BOOLEAN DEFAULT TRUE
);

-- Pagos
CREATE TABLE finance.pagos (
    id_pago BIGSERIAL PRIMARY KEY,
    paciente_id BIGINT NOT NULL,
    total_facturado DECIMAL(10,2) NOT NULL,
    monto_pagado DECIMAL(10,2) DEFAULT 0,
    saldo_pendiente DECIMAL(10,2),
    status_pago VARCHAR(20) DEFAULT 'Pendiente' 
        CHECK (status_pago IN ('Pendiente', 'Parcial', 'Pagado')),
    notas TEXT,
    fecha_emision TIMESTAMPTZ DEFAULT NOW()
);

-- Transacciones
CREATE TABLE finance.transacciones (
    id_transaccion BIGSERIAL PRIMARY KEY,
    pago_id BIGINT REFERENCES finance.pagos(id_pago),
    monto DECIMAL(10,2) NOT NULL,
    metodo_pago_id BIGINT REFERENCES finance.metodos_pago(id_metodo),
    notas TEXT,
    recibido_por BIGINT,
    fecha TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 2. LOS 95 ENDPOINTS DE LA API

### 2.1 Autenticación (3 endpoints)
```
POST   /api/v1/auth/login              # Login, retorna JWT
GET    /api/v1/auth/me                 # Perfil del usuario autenticado
PUT    /api/v1/auth/change-password    # Cambiar contraseña propia
```

### 2.2 Pacientes (7 endpoints)
```
GET    /api/v1/pacientes               # Lista todos los pacientes
GET    /api/v1/pacientes/buscar?q=     # Búsqueda fuzzy por nombre
GET    /api/v1/pacientes/{id}          # Detalle de un paciente
POST   /api/v1/pacientes               # Crear paciente nuevo
PUT    /api/v1/pacientes/{id}          # Actualizar paciente
DELETE /api/v1/pacientes/{id}          # Soft delete (activo=false)
DELETE /api/v1/pacientes/{id}/purge    # Hard delete (solo Admin)
```

### 2.3 Citas (8 endpoints)
```
GET    /api/v1/citas                   # Lista todas las citas
GET    /api/v1/citas/agenda/{fecha}    # Agenda del día
GET    /api/v1/citas/disponibilidad    # Slots disponibles por podólogo
GET    /api/v1/citas/{id}              # Detalle de una cita
POST   /api/v1/citas                   # Crear cita (valida anti-solapamiento)
PUT    /api/v1/citas/{id}              # Actualizar cita
PATCH  /api/v1/citas/{id}/status       # Cambiar estado (Confirmada, Cancelada, etc.)
DELETE /api/v1/citas/{id}              # Cancelar cita
```

### 2.4 Podólogos (5 endpoints)
```
GET    /api/v1/podologos               # Lista todos los podólogos
GET    /api/v1/podologos/{id}          # Detalle de un podólogo
POST   /api/v1/podologos               # Crear podólogo
PUT    /api/v1/podologos/{id}          # Actualizar podólogo
DELETE /api/v1/podologos/{id}          # Desactivar podólogo
```

### 2.5 Servicios (5 endpoints)
```
GET    /api/v1/servicios               # Lista catálogo de servicios
GET    /api/v1/servicios/{id}          # Detalle de un servicio
POST   /api/v1/servicios               # Crear servicio
PUT    /api/v1/servicios/{id}          # Actualizar servicio
DELETE /api/v1/servicios/{id}          # Desactivar servicio
```

### 2.6 Tratamientos (6 endpoints)
```
GET    /api/v1/tratamientos            # Lista tratamientos
GET    /api/v1/tratamientos/{id}       # Detalle con evoluciones
POST   /api/v1/tratamientos            # Crear tratamiento
PUT    /api/v1/tratamientos/{id}       # Actualizar tratamiento
PATCH  /api/v1/tratamientos/{id}/status # Cambiar estado
DELETE /api/v1/tratamientos/{id}       # Cerrar tratamiento
```

### 2.7 Evoluciones SOAP (5 endpoints)
```
GET    /api/v1/evoluciones             # Lista evoluciones
GET    /api/v1/evoluciones/{id}        # Detalle de una evolución
POST   /api/v1/evoluciones             # Crear nota SOAP
PUT    /api/v1/evoluciones/{id}        # Actualizar nota
DELETE /api/v1/evoluciones/{id}        # Eliminar nota
```

### 2.8 Evidencias Fotográficas (8 endpoints)
```
GET    /api/v1/evidencias              # Lista todas las evidencias
GET    /api/v1/evidencias/evolucion/{id}    # Evidencias de una evolución
GET    /api/v1/evidencias/tratamiento/{id}  # Evidencias de un tratamiento
GET    /api/v1/evidencias/{id}         # Detalle de una evidencia
POST   /api/v1/evidencias              # Crear registro de evidencia
POST   /api/v1/evidencias/upload       # Subir archivo de imagen
PUT    /api/v1/evidencias/{id}         # Actualizar metadata
DELETE /api/v1/evidencias/{id}         # Eliminar evidencia
```

### 2.9 Historial Detalles (20 endpoints - 4 recursos × 5 operaciones)
```
# Alergias
GET    /api/v1/historial/alergias?paciente_id=
GET    /api/v1/historial/alergias/{id}
POST   /api/v1/historial/alergias
PUT    /api/v1/historial/alergias/{id}
DELETE /api/v1/historial/alergias/{id}

# Suplementos
GET    /api/v1/historial/suplementos?paciente_id=
GET    /api/v1/historial/suplementos/{id}
POST   /api/v1/historial/suplementos
PUT    /api/v1/historial/suplementos/{id}
DELETE /api/v1/historial/suplementos/{id}

# Antecedentes No Patológicos
GET    /api/v1/historial/antecedentes-no-patologicos?paciente_id=
GET    /api/v1/historial/antecedentes-no-patologicos/{id}
POST   /api/v1/historial/antecedentes-no-patologicos
PUT    /api/v1/historial/antecedentes-no-patologicos/{id}
DELETE /api/v1/historial/antecedentes-no-patologicos/{id}

# Conversaciones Digitales
GET    /api/v1/historial/conversaciones-digitales?paciente_id=
GET    /api/v1/historial/conversaciones-digitales/{id}
POST   /api/v1/historial/conversaciones-digitales
PUT    /api/v1/historial/conversaciones-digitales/{id}
DELETE /api/v1/historial/conversaciones-digitales/{id}
```

### 2.10 Finance (7 endpoints)
```
GET    /api/v1/finance/metodos         # Lista métodos de pago
POST   /api/v1/finance/metodos         # Crear método de pago
GET    /api/v1/finance/pagos           # Lista todos los pagos
GET    /api/v1/finance/pagos/{id}      # Detalle de un pago
POST   /api/v1/finance/pagos           # Crear pago
POST   /api/v1/finance/pagos/{id}/transacciones  # Agregar transacción
GET    /api/v1/finance/pagos/{id}/transacciones  # Listar transacciones
```

### 2.11 Prospectos/Leads (5 endpoints)
```
GET    /api/v1/prospectos              # Lista prospectos
GET    /api/v1/prospectos/{id}         # Detalle de un prospecto
POST   /api/v1/prospectos              # Crear prospecto
PUT    /api/v1/prospectos/{id}         # Actualizar prospecto
POST   /api/v1/prospectos/{id}/convertir # Convertir a paciente
```

### 2.12 Usuarios (6 endpoints)
```
GET    /api/v1/usuarios                # Lista usuarios (Admin)
GET    /api/v1/usuarios/{id}           # Detalle de usuario
POST   /api/v1/usuarios                # Crear usuario (Admin)
PUT    /api/v1/usuarios/{id}           # Actualizar usuario
PUT    /api/v1/usuarios/{id}/reset-password # Resetear contraseña (Admin)
DELETE /api/v1/usuarios/{id}           # Desactivar usuario
```

### 2.13 Auditoría (3 endpoints)
```
GET    /api/v1/audit                   # Lista logs de auditoría
GET    /api/v1/audit/pacientes/{id}    # Historial de cambios de un paciente
GET    /api/v1/audit/export            # Exportar logs a CSV
```

### 2.14 Examples/Validaciones (3 endpoints)
```
POST   /api/v1/examples/pacientes      # Crear paciente con validación Pydantic
PUT    /api/v1/examples/pacientes/{id} # Actualizar con validación
POST   /api/v1/examples/tratamientos   # Crear tratamiento con validación
```

---

## 3. PERMISOS POR ROL (RBAC)

### Matriz de Permisos
```
| Recurso              | Admin | Podologo | Recepcion |
|----------------------|-------|----------|-----------|
| auth/login           | ✅    | ✅       | ✅        |
| auth/me              | ✅    | ✅       | ✅        |
| auth/change-password | ✅    | ✅       | ✅        |
| pacientes (CRUD)     | ✅    | ✅       | ✅ (solo contacto) |
| pacientes/historial  | ✅    | ✅       | ❌        |
| citas (CRUD)         | ✅    | ✅       | ✅        |
| tratamientos         | ✅    | ✅       | ❌        |
| evoluciones          | ✅    | ✅       | ❌        |
| evidencias           | ✅    | ✅       | ❌        |
| finance/pagos        | ✅    | ✅       | ✅ (solo ver) |
| finance/transacciones| ✅    | ✅       | ❌        |
| usuarios             | ✅    | ❌       | ❌        |
| audit                | ✅    | ✅ (limitado) | ❌    |
| prospectos           | ✅    | ✅       | ✅        |
| podologos            | ✅    | ✅ (solo ver) | ✅ (solo ver) |
| servicios            | ✅    | ✅ (solo ver) | ✅ (solo ver) |
```

### Restricciones Especiales
- **Recepcion** NO puede ver: historial médico, evoluciones, evidencias, transacciones, audit
- **Podologo** NO puede: crear/eliminar usuarios, ver audit de otros usuarios
- **Admin** puede: todo

---

## 4. ESTRUCTURA DE CARPETAS ACTUAL

```
backend/
├── api/
│   ├── app.py                    # FastAPI entry point
│   ├── core/
│   │   ├── config.py             # Settings (DB URLs, JWT secrets)
│   │   └── security.py           # JWT encode/decode
│   ├── deps/
│   │   ├── database.py           # get_auth_db(), get_core_db(), get_ops_db()
│   │   ├── auth.py               # get_current_user, get_current_active_user
│   │   └── permissions.py        # require_role(), RBAC decorators
│   └── routes/
│       ├── auth.py
│       ├── pacientes.py
│       ├── citas.py
│       ├── podologos.py
│       ├── servicios.py
│       ├── tratamientos.py
│       ├── evoluciones.py
│       ├── evidencias.py
│       ├── historial_detalles.py
│       ├── finance.py
│       ├── prospectos.py
│       ├── usuarios.py
│       ├── audit.py
│       └── examples_schemas.py
├── schemas/
│   ├── auth/
│   │   ├── models.py             # SQLAlchemy: Clinica, SysUsuario, AuditLog
│   │   ├── schemas.py            # Pydantic: ClinicaRead, SysUsuarioCreate, etc.
│   │   └── auth_utils.py         # hash_password, verify_password (bcrypt)
│   ├── core/
│   │   ├── models.py             # SQLAlchemy: Paciente, Tratamiento, Evolucion, etc.
│   │   └── schemas.py            # Pydantic: PacienteCreate, TratamientoRead, etc.
│   ├── ops/
│   │   └── models.py             # SQLAlchemy: Podologo, Cita, CatalogoServicio, Prospecto
│   └── finance/
│       ├── models.py             # SQLAlchemy: MetodoPago, Pago, Transaccion
│       └── schemas.py            # Pydantic: PagoCreate, TransaccionResponse, etc.
├── agents/                       # <-- A IMPLEMENTAR
│   ├── __init__.py
│   ├── state.py                  # TypedDict state definition
│   ├── graph.py                  # StateGraph definition
│   ├── workflow.py               # Main workflow orchestration
│   └── nodes/
│       ├── __init__.py
│       ├── classify_intent.py
│       ├── check_permissions.py
│       ├── generate_sql.py
│       ├── validate_sql.py
│       ├── execute_sql.py
│       └── generate_response.py
├── tools/                        # <-- A IMPLEMENTAR
│   ├── __init__.py
│   ├── sql_executor.py           # Tool para ejecutar SQL readonly
│   ├── fuzzy_search.py           # Tool para búsqueda con pg_trgm
│   ├── date_parser.py            # Tool para interpretar fechas naturales
│   └── schema_info.py            # Tool para obtener info del esquema
└── config/
    └── logging_config.py
```

---

## 5. LO QUE NECESITO QUE CONSTRUYAS

### 5.1 State (TypedDict)
Define un state completo que capture:
- Input del usuario (query, user_id, role)
- Análisis semántico (intent, entities, target_database)
- SQL generado (query, params, is_safe)
- Resultados (rows, count, error)
- Respuesta final (natural language)
- Metadata (timing, audit)

### 5.2 Nodos del Grafo
Implementa nodos funcionales para:
1. **classify_intent**: Clasifica la consulta (pacientes, citas, finanzas, etc.)
2. **check_permissions**: Valida RBAC según rol del usuario
3. **generate_sql**: Genera SQL seguro con parámetros
4. **validate_sql**: Valida que solo sea SELECT, sin DROP/DELETE/etc.
5. **execute_sql**: Ejecuta contra la BD correcta
6. **generate_response**: Convierte resultados a lenguaje natural
7. **handle_error**: Maneja errores gracefully

### 5.3 Graph
Construye un StateGraph con:
- Edges condicionales (permission denied → error response)
- Validación de SQL (unsafe → error response)
- Flujo principal completo

### 5.4 Tools
Implementa tools de LangChain para:
- `execute_readonly_sql`: Ejecuta SELECT contra las 3 BDs
- `fuzzy_search_patient`: Búsqueda tolerante a errores (pg_trgm)
- `parse_date_expression`: "este mes", "ayer", "última semana"
- `get_table_schema`: Info de columnas para el LLM

### 5.5 Ejemplos de Consultas a Soportar
```
# Pacientes
"¿Cuántos pacientes tenemos?"
"Busca a Juan Pérez" (debe encontrar "Juna Peres")
"¿Qué pacientes vinieron este mes?"
"Muéstrame el historial del paciente 5"

# Citas
"¿Qué citas hay mañana?"
"¿Cuántas cancelaciones hubo esta semana?"
"¿Qué horarios tiene libres el Dr. García?"

# Tratamientos
"¿Cuántos tratamientos activos hay?"
"¿Qué pacientes no han tenido evolución en 30 días?"

# Finanzas
"¿Cuánto facturamos este mes?"
"¿Cuáles son los pagos pendientes?"
"¿Cuál es el método de pago más usado?"

# Auditoría (solo Admin)
"¿Quién modificó al paciente 5?"
"¿Cuántos logins fallidos hubo hoy?"
```

---

## 6. CONEXIÓN A BASE DE DATOS

### Código existente para conectar
```python
# backend/api/deps/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend.api.core.config import get_settings

settings = get_settings()

# Engines para cada BD
auth_engine = create_engine(settings.AUTH_DB_URL)
core_engine = create_engine(settings.CORE_DB_URL)
ops_engine = create_engine(settings.OPS_DB_URL)

# Sessions
AuthSession = sessionmaker(bind=auth_engine)
CoreSession = sessionmaker(bind=core_engine)
OpsSession = sessionmaker(bind=ops_engine)

def get_auth_db():
    db = AuthSession()
    try:
        yield db
    finally:
        db.close()

def get_core_db():
    db = CoreSession()
    try:
        yield db
    finally:
        db.close()

def get_ops_db():
    db = OpsSession()
    try:
        yield db
    finally:
        db.close()
```

### URLs de conexión (en .env)
```
AUTH_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db
CORE_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db
OPS_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db
```

---

## 7. REQUISITOS TÉCNICOS

- **Python:** 3.12
- **LangGraph:** 0.2+
- **LangChain:** 0.2+
- **LLM:** Compatible con OpenAI API (puede ser local o cloud)
- **SQLAlchemy:** 2.0.44
- **PostgreSQL:** 17 con extensiones pg_trgm, btree_gist, pgcrypto

---

## 8. ENTREGABLES ESPERADOS

Por favor genera código completo y funcional para:

1. `backend/agents/state.py` - TypedDict state completo
2. `backend/agents/nodes/*.py` - Cada nodo como módulo separado
3. `backend/agents/graph.py` - StateGraph con edges
4. `backend/agents/workflow.py` - Función principal para invocar
5. `backend/tools/*.py` - Tools de LangChain
6. `backend/api/routes/chat.py` - Endpoint `/chat` que use el workflow

El código debe ser production-ready, con:
- Type hints completos
- Docstrings descriptivos
- Manejo de errores robusto
- Logging apropiado
- Tests básicos si es posible

---

**Tienes libertad total para decidir la implementación óptima. Sorpréndeme con código elegante y eficiente.**
