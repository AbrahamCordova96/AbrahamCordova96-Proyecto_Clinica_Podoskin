# 🦶 Sistema PodoSkin

## Documentación de Desarrollo: Arquitectura de Base de Datos v4.1

---

**Documento técnico para referencia del equipo de desarrollo**  
**Fecha Actualización:** 9 de Diciembre, 2025  
**Versión:** 4.1 (Post-Testing Completo)

---

## 📋 Resumen del Desarrollo

Este documento describe el proceso técnico de implementación de la arquitectura de 3 bases de datos separadas para el sistema PodoSkin.

**Estado Final del Proyecto:**
- ✅ 95 endpoints REST implementados
- ✅ 89 endpoints funcionales (93.7% operativo)
- ✅ 3 bugs críticos corregidos
- ✅ Test automatizado completo (`test_all_95_endpoints.ps1`)

---

## 🏗️ Arquitectura Implementada

### Estructura de Bases de Datos

```
┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER: podoskin-db                          │
│                    PostgreSQL 17-alpine                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────────────────┐                                      │
│   │   clinica_auth_db   │  Schema: auth                        │
│   │   ───────────────   │  • sys_usuarios (login)              │
│   │   Seguridad         │  • audit_log (particionado x13)      │
│   │                     │  • clinicas (multi-tenant)           │
│   └─────────────────────┘                                      │
│                                                                 │
│   ┌─────────────────────┐                                      │
│   │   clinica_core_db   │  Schema: clinic                      │
│   │   ───────────────   │  • pacientes                         │
│   │   Datos Clínicos    │  • historial_medico_general          │
│   │                     │  • historial_gineco                  │
│   │                     │  • tratamientos                      │
│   │                     │  • evoluciones_clinicas              │
│   │                     │  • evidencia_fotografica             │
│   │                     │  • sesiones_ia_conversacion          │
│   └─────────────────────┘                                      │
│                                                                 │
│   ┌─────────────────────┐                                      │
│   │   clinica_ops_db    │  Schemas: ops + finance              │
│   │   ───────────────   │  ops:                                │
│   │   Operaciones       │  • citas (EXCLUDE constraint)        │
│   │                     │  • catalogo_servicios                │
│   │                     │  • podologos                         │
│   │                     │  • solicitudes_prospectos            │
│   │                     │  finance:                            │
│   │                     │  • pagos, transacciones              │
│   │                     │  • gastos, categorias_gasto          │
│   │                     │  • proveedores, metodos_pago         │
│   └─────────────────────┘                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Archivos Creados

### Estructura del Directorio `sql/`

```
Project-Medical/
├── docker-compose.yml          # Configuración Docker actualizada
└── sql/
    ├── 01_create_databases.sh  # Script bash (formato Unix LF)
    ├── 02_init_auth_db.sql     # Inicialización clinica_auth_db
    ├── 03_init_core_db.sql     # Inicialización clinica_core_db
    └── 04_init_ops_db.sql      # Inicialización clinica_ops_db
```

---

## 🔧 Características Técnicas Implementadas

### Cumplimiento con Auditoría PostgreSQL Avanzada

| Característica | Implementación |
|----------------|----------------|
| **Claves primarias** | `BIGINT GENERATED ALWAYS AS IDENTITY` (no SERIAL) |
| **Tipos de texto** | `TEXT` con `CHECK` constraints (no VARCHAR) |
| **Cálculos automáticos** | Columnas generadas (`GENERATED ALWAYS AS... STORED`) |
| **Anti double-booking** | `EXCLUDE CONSTRAINT` con `btree_gist` en `ops.citas` |
| **Búsqueda fuzzy** | Índices GIN con `pg_trgm` para tolerancia a typos |
| **Auditoría particionada** | `auth.audit_log` particionado por mes (2024-12 a 2025-12) |
| **Hashing seguro** | `pgcrypto` con bcrypt para passwords |

---

### Columnas Generadas Automáticas

```sql
-- IMC en historial_medico_general
imc DECIMAL(5,2) GENERATED ALWAYS AS (
    CASE 
        WHEN peso_kg IS NOT NULL AND talla_cm IS NOT NULL AND talla_cm > 0
        THEN ROUND(peso_kg / POWER(talla_cm / 100.0, 2), 2)
        ELSE NULL
    END
) STORED

-- Subtotal en servicios_prestados
subtotal DECIMAL(10,2) GENERATED ALWAYS AS (
    (precio_aplicado * cantidad) - descuento
) STORED

-- Monto total en gastos
monto_total DECIMAL(12,2) GENERATED ALWAYS AS (
    monto + COALESCE(iva, 0)
) STORED
```

---

### EXCLUDE Constraint para Citas

```sql
-- Previene solapamiento de citas del mismo podólogo
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
```

---

## 🔄 Proceso de Inicialización

```
docker-compose up -d
        │
        ▼
┌───────────────────────────────────────┐
│  01_create_databases.sh               │
│  ─────────────────────────────────    │
│  1. Crea clinica_auth_db              │
│  2. Crea clinica_core_db              │
│  3. Crea clinica_ops_db               │
│  4. Ejecuta 02_init_auth_db.sql       │
│  5. Ejecuta 03_init_core_db.sql       │
│  6. Ejecuta 04_init_ops_db.sql        │
└───────────────────────────────────────┘
```

---

## 📊 Datos Iniciales Insertados

### Usuario Administrador

```sql
INSERT INTO auth.sys_usuarios (nombre_usuario, password_hash, rol, activo, email)
VALUES ('admin', crypt('Admin2024!', gen_salt('bf')), 'Admin', TRUE, 'admin@podoskin.local');
```

### Catálogo de Servicios

| Servicio | Precio | Duración |
|----------|--------|----------|
| Consulta Primera Vez | $400.00 | 45 min |
| Consulta Seguimiento | $300.00 | 30 min |
| Limpieza Profunda | $250.00 | 45 min |
| Tratamiento Onicomicosis | $600.00 | 60 min |
| Plantillas Ortopédicas | $1,200.00 | 90 min |

### Métodos de Pago

- Efectivo
- Tarjeta Débito
- Tarjeta Crédito
- Transferencia
- Depósito

### Categorías de Gasto

- Renta (recurrente, 30 días)
- Servicios (recurrente, 30 días)
- Sueldos (recurrente, 15 días)
- Insumos Médicos
- Instrumentos
- Comisiones
- Mantenimiento
- Marketing
- Impuestos
- Otros

---

## 🔗 Conexión desde FastAPI

### Variables de Entorno

```bash
# Agregar a .env
AUTH_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db
CORE_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db
OPS_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db
```

### Ejemplo de Conexión

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Crear engines para cada base de datos
auth_engine = create_engine(os.getenv("AUTH_DB_URL"))
core_engine = create_engine(os.getenv("CORE_DB_URL"))
ops_engine = create_engine(os.getenv("OPS_DB_URL"))

# Crear sesiones
AuthSession = sessionmaker(bind=auth_engine)
CoreSession = sessionmaker(bind=core_engine)
OpsSession = sessionmaker(bind=ops_engine)
```

---

## ⚠️ Errores Resueltos Durante Desarrollo

| Error | Causa | Solución |
|-------|-------|----------|
| Script .sh no se ejecuta | Formato CRLF (Windows) | Convertir a LF (Unix) |
| `cannot specify storage parameters for partitioned table` | PostgreSQL 17 no permite `ALTER TABLE SET` en tablas particionadas | Eliminar parámetros de autovacuum en tabla padre |
| `database "podoskin" does not exist` | Healthcheck apuntaba a BD inexistente | Cambiar healthcheck a `clinica_core_db` |

---

## 🖥️ Comandos Útiles

```bash
# Listar bases de datos
docker exec podoskin-db psql -U podoskin -d postgres -c "\l"

# Ver tablas de un schema
docker exec podoskin-db psql -U podoskin -d clinica_core_db -c "\dt clinic.*"

# Conectar interactivamente
docker exec -it podoskin-db psql -U podoskin -d clinica_core_db

# Ver logs
docker-compose logs -f db

# Reiniciar limpio
docker-compose down -v && docker-compose up -d
```

---

## 📞 Información del Desarrollador

| Campo | Información |
|-------|-------------|
| **Desarrollador** | Abraham Cordova |
| **Fecha de implementación** | 6 de Diciembre, 2025 |
| **PostgreSQL** | 17-alpine |
| **Docker Compose** | v2 |

---

<div align="center">

---

**Documentación Técnica - Sistema PodoSkin**  
*Base de Datos v4.0*

---

</div>
