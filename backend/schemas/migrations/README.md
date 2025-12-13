# Database Migrations - PodoSkin

## Estructura de Migraciones

Este directorio contiene migraciones SQL manuales para las 3 bases de datos del sistema.

### Migraciones Existentes

1. **002_add_gemini_api_key.sql** - Campos para API Key de Gemini
2. **003_nom024_compliance.sql** - Cumplimiento NOM-024 (NUEVA)

---

## Migración 003: NOM-024 Compliance

**Fecha**: 13 de diciembre de 2025  
**Propósito**: Implementar cumplimiento pragmático de NOM-024

### Cambios Incluidos

#### clinica_auth_db (schema: auth)
- ✅ Nueva tabla: `audit_logs_inmutable` (log inmutable con trigger)
- ✅ Nueva tabla: `access_logs` (log de accesos/lecturas)
- ✅ Nueva tabla: `permisos` (catálogo de permisos)
- ✅ Nueva tabla: `rol_permisos` (relación rol-permiso)
- ✅ Nuevo campo en `clinicas`: `clues` (Clave Única de Establecimiento)

#### clinica_core_db (schema: clinic)
- ✅ Nuevos campos en `pacientes`:
  - `curp`, `segundo_apellido`
  - `estado_nacimiento`, `nacionalidad`
  - `estado_residencia`, `municipio_residencia`, `localidad_residencia`
  - `consentimiento_intercambio`, `fecha_consentimiento`
- ✅ Nuevos campos en `tratamientos`:
  - `firma_electronica`, `firma_timestamp`, `firma_tipo`
- ✅ Nuevos campos en `evoluciones_clinicas`:
  - `firma_electronica`, `firma_timestamp`, `firma_tipo`
- ✅ Nueva tabla: `cat_diagnosticos` (catálogo CIE-10)
- ✅ Nueva tabla: `cat_procedimientos` (catálogo de procedimientos)
- ✅ Nueva tabla: `cat_medicamentos` (Cuadro Básico)

#### clinica_ops_db (schema: ops)
- ✅ Nuevo campo en `podologos`: `institucion_titulo`

---

## Cómo Ejecutar la Migración

### Opción 1: Usando psql (Recomendado)

```bash
# Ejecutar la migración completa
docker exec -i podoskin-db psql -U podoskin < backend/schemas/migrations/003_nom024_compliance.sql
```

### Opción 2: Conectar manualmente y ejecutar

```bash
# Conectar al contenedor
docker exec -it podoskin-db psql -U podoskin

# Dentro de psql, ejecutar:
\i /path/to/003_nom024_compliance.sql
```

### Opción 3: Base por base

```bash
# Auth DB
docker exec -i podoskin-db psql -U podoskin -d clinica_auth_db < backend/schemas/migrations/003_nom024_compliance.sql

# Core DB
docker exec -i podoskin-db psql -U podoskin -d clinica_core_db < backend/schemas/migrations/003_nom024_compliance.sql

# Ops DB
docker exec -i podoskin-db psql -U podoskin -d clinica_ops_db < backend/schemas/migrations/003_nom024_compliance.sql
```

---

## Verificación

Después de ejecutar la migración, verifica que todo está correcto:

```bash
docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db
```

```sql
-- Verificar tablas nuevas
\dt auth.audit_logs_inmutable
\dt auth.access_logs
\dt auth.permisos

-- Verificar trigger de inmutabilidad
SELECT 
    tgname as trigger_name,
    tgenabled as enabled
FROM pg_trigger
WHERE tgrelid = 'auth.audit_logs_inmutable'::regclass;

-- Verificar campos en pacientes
\d clinic.pacientes

-- Verificar tablas de catálogos
\dt clinic.cat_*
```

### Test del Trigger de Inmutabilidad

```sql
-- Este comando debe FALLAR (es lo esperado)
INSERT INTO auth.audit_logs_inmutable (user_id, username_snapshot, tabla_afectada, registro_id, accion)
VALUES (1, 'test', 'test', 1, 'INSERT');

-- Intentar actualizar (debe fallar)
UPDATE auth.audit_logs_inmutable SET user_id = 2 WHERE id = 1;
-- ERROR: audit_logs_inmutable is append-only. Modifications not allowed.

-- Intentar eliminar (debe fallar)
DELETE FROM auth.audit_logs_inmutable WHERE id = 1;
-- ERROR: audit_logs_inmutable is append-only. Modifications not allowed.
```

---

## Rollback

Si necesitas revertir los cambios, descomenta y ejecuta la sección ROLLBACK al final del archivo de migración.

**⚠️ ADVERTENCIA**: El rollback eliminará todas las tablas y datos de NOM-024.

```bash
# Ejecutar sección de rollback (editada)
docker exec -i podoskin-db psql -U podoskin < backend/schemas/migrations/003_nom024_compliance_rollback.sql
```

---

## Notas Importantes

### Inmutabilidad del Audit Log

La tabla `audit_logs_inmutable` está protegida por un trigger PostgreSQL que previene:
- ❌ UPDATE operations
- ❌ DELETE operations
- ✅ INSERT operations (append-only)

Este es un requisito crítico de NOM-024 para garantizar la integridad de la auditoría.

### Campos Opcionales

Todos los nuevos campos son OPCIONALES (nullable) para:
- No romper datos existentes
- Permitir migración gradual
- No requerir trámites burocráticos inmediatos

Cuando se busque certificación, estos campos deberán validarse en la aplicación.

### Cross-Database References

Los "FK virtuales" mencionados en comentarios NO son Foreign Keys reales.
SQLAlchemy no soporta FKs entre bases de datos diferentes.
Las validaciones se hacen en la capa de aplicación.

---

## Próximas Migraciones

Futuras migraciones podrían incluir:
- Datos iniciales para catálogos (CIE-10, Cuadro Básico)
- Permisos predefinidos (leer_expediente, modificar_expediente, etc.)
- Catálogos INEGI (estados, municipios, localidades)
- Índices adicionales según análisis de performance

---

## Soporte

Si encuentras problemas durante la migración:

1. Revisa los logs de PostgreSQL:
   ```bash
   docker logs podoskin-db
   ```

2. Verifica que el contenedor esté corriendo:
   ```bash
   docker ps | grep podoskin-db
   ```

3. Verifica conectividad:
   ```bash
   docker exec -it podoskin-db psql -U podoskin -c "SELECT version();"
   ```

4. Verifica la última migración aplicada:
   ```sql
   SELECT MAX(id) FROM auth.audit_logs_inmutable;
   ```

---

**Última actualización**: 13 de diciembre de 2025
