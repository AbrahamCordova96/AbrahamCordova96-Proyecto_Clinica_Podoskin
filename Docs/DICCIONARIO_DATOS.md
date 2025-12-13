# Diccionario de Datos - PodoSkin
## NOM-024 Compliance Documentation

**Versión**: 1.0  
**Fecha**: 13 de diciembre de 2025  
**Propósito**: Documentar la estructura de datos para cumplimiento NOM-024 y certificación futura

---

## Base de Datos: clinica_auth_db (Schema: auth)

### Tabla: clinicas
Información de las clínicas registradas en el sistema (multi-tenant).

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_clinica | BigInteger | Primary Key | Sí | - | Autoincremental |
| nombre | String | Nombre de la clínica | Sí | - | |
| rfc | String | RFC de la clínica | No | - | Para facturación |
| activa | Boolean | Clínica activa | Sí | - | Default: true |
| clues | String(12) | Clave Única de Establecimiento de Salud | No | NOM-024 | Opcional ahora, obligatorio para certificación |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

**Índices**: PK en id_clinica, UNIQUE en clues

---

### Tabla: sys_usuarios
Usuarios del sistema con roles y permisos.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_usuario | BigInteger | Primary Key | Sí | - | Autoincremental |
| nombre_usuario | String(50) | Username único | Sí | - | UNIQUE |
| password_hash | String | Password hasheado (bcrypt) | Sí | - | Nunca almacenar plain text |
| rol | String | Rol del usuario | Sí | NOM-024 RBAC | Admin, Podologo, Recepcion |
| activo | Boolean | Usuario activo | Sí | - | Default: true (soft delete) |
| email | String | Email del usuario | No | - | UNIQUE |
| last_login | TIMESTAMPTZ | Último login | No | - | |
| failed_login_attempts | BigInteger | Intentos fallidos | Sí | - | Default: 0 |
| locked_until | TIMESTAMPTZ | Bloqueado hasta | No | - | Anti-brute force |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |
| clinica_id | BigInteger | FK a clinicas | No | - | Multi-tenant |

**Índices**: PK en id_usuario, UNIQUE en (nombre_usuario, email)

---

### Tabla: audit_log
Log de auditoría histórico (modificable, para compatibilidad).

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_log | BigInteger | Primary Key | Sí | - | Autoincremental |
| timestamp_accion | TIMESTAMPTZ | Momento de la acción | Sí | NOM-024 | Auto-generado |
| tabla_afectada | String | Tabla modificada | Sí | NOM-024 | |
| registro_id | BigInteger | ID del registro | No | NOM-024 | |
| accion | String | Tipo de acción | Sí | NOM-024 | CREATE, UPDATE, DELETE, READ |
| usuario_id | BigInteger | FK a sys_usuarios | No | NOM-024 | |
| username | String | Snapshot del username | No | NOM-024 | |
| datos_anteriores | JSONB | Estado antes del cambio | No | NOM-024 | |
| datos_nuevos | JSONB | Estado después del cambio | No | NOM-024 | |
| ip_address | INET | IP del cliente | No | NOM-024 | |

---

### Tabla: audit_logs_inmutable (NOM-024 NEW)
**Log de auditoría INMUTABLE** - Append-only, protegido por trigger PostgreSQL.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | NOM-024 | Autoincremental, NUNCA se modifica |
| timestamp | TIMESTAMPTZ | Momento de la acción | Sí | NOM-024 | Auto-generado, INMUTABLE |
| user_id | BigInteger | ID del usuario | Sí | NOM-024 | Sin FK (sobrevive a deletes) |
| username_snapshot | String(50) | Snapshot del username | Sí | NOM-024 | Preserva identidad aunque se borre usuario |
| tabla_afectada | String(100) | Tabla modificada | Sí | NOM-024 | |
| registro_id | BigInteger | ID del registro | Sí | NOM-024 | |
| accion | String(20) | INSERT, UPDATE, DELETE | Sí | NOM-024 | UPPERCASE |
| datos_antes | JSONB | Estado COMPLETO antes | No | NOM-024 | NULL para INSERT |
| datos_despues | JSONB | Estado COMPLETO después | No | NOM-024 | NULL para DELETE |
| ip_address | INET | IP del cliente | No | NOM-024 | |
| razon_cambio | String(500) | Razón del cambio | No | NOM-024 | Para overrides manuales |

**CRÍTICO**: Esta tabla NO permite UPDATE ni DELETE. Protegida por trigger PostgreSQL.

---

### Tabla: access_logs (NOM-024 NEW)
Log de accesos a datos sensibles (operaciones de lectura).

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | NOM-024 | Autoincremental |
| timestamp | TIMESTAMPTZ | Momento del acceso | Sí | NOM-024 | Auto-generado |
| user_id | BigInteger | ID del usuario | Sí | NOM-024 | |
| username_snapshot | String(50) | Snapshot del username | Sí | NOM-024 | |
| accion | String(100) | Descripción | Sí | NOM-024 | Ej: "consultar_expediente" |
| recurso | String(200) | Recurso accedido | Sí | NOM-024 | Ej: "paciente_123" |
| ip_address | INET | IP del cliente | No | NOM-024 | |
| metodo_http | String(10) | GET, POST, etc. | No | NOM-024 | |
| endpoint | String(200) | Ruta del API | No | NOM-024 | |

---

### Tabla: permisos (NOM-024 NEW - Preparación)
Catálogo de permisos del sistema (para RBAC granular futuro).

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | NOM-024 | Autoincremental |
| nombre | String(100) | Nombre del permiso | Sí | NOM-024 | snake_case, UNIQUE |
| descripcion | String(200) | Descripción legible | No | NOM-024 | |
| modulo | String(50) | Categoría | No | NOM-024 | pacientes, finanzas, etc. |
| activo | Boolean | Permiso activo | Sí | NOM-024 | Default: true |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

**Ejemplos**: leer_expediente, modificar_expediente, eliminar_paciente, ver_finanzas

---

### Tabla: rol_permisos (NOM-024 NEW - Preparación)
Relación muchos-a-muchos entre roles y permisos.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | - | Autoincremental |
| rol | String(50) | Rol | Sí | NOM-024 | Admin, Podologo, Recepcion |
| permiso_id | BigInteger | FK a permisos | Sí | NOM-024 | |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

---

## Base de Datos: clinica_core_db (Schema: clinic)

### Tabla: pacientes
Expediente clínico del paciente - tabla central del sistema.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_paciente | BigInteger | Primary Key | Sí | - | Autoincremental |
| id_clinica | BigInteger | Clínica | Sí | - | Default: 1 (multi-tenant) |
| nombres | Text | Nombre(s) | Sí | NOM-024 Tabla 1 | |
| apellidos | Text | Apellido paterno | Sí | NOM-024 Tabla 1 | |
| segundo_apellido | String(50) | Apellido materno | No | NOM-024 Tabla 1 | **NUEVO** |
| fecha_nacimiento | Date | Fecha de nacimiento | Sí | NOM-024 Tabla 1 | ISO 8601 |
| sexo | String(1) | Sexo biológico | No | NOM-024 Tabla 1 | M o F (no H) |
| curp | String(18) | CURP | No | NOM-024 Tabla 1 | **NUEVO**: Opcional ahora, obligatorio futuro |
| estado_nacimiento | String(2) | Estado de nacimiento | No | NOM-024 Tabla 1 | **NUEVO**: Código INEGI |
| nacionalidad | String(3) | Nacionalidad | No | NOM-024 Tabla 1 | **NUEVO**: ISO 3166 (default: MEX) |
| estado_residencia | String(2) | Estado de residencia | No | NOM-024 | **NUEVO**: Código INEGI |
| municipio_residencia | String(3) | Municipio | No | NOM-024 | **NUEVO**: Código INEGI |
| localidad_residencia | String(4) | Localidad | No | NOM-024 | **NUEVO**: Código INEGI |
| estado_civil | Text | Estado civil | No | - | |
| ocupacion | Text | Ocupación | No | - | |
| escolaridad | Text | Nivel educativo | No | - | |
| religion | Text | Religión | No | - | |
| domicilio | Text | Dirección completa | No | - | |
| telefono | Text | Teléfono | Sí | - | Mínimo 10 caracteres |
| email | Text | Email | No | - | Validación regex |
| como_supo_de_nosotros | Text | Origen de contacto | No | - | Marketing |
| consentimiento_intercambio | Boolean | Consiente compartir datos | Sí | NOM-024 | **NUEVO**: Default: false |
| fecha_consentimiento | Date | Fecha del consentimiento | No | NOM-024 | **NUEVO** |
| fecha_registro | TIMESTAMPTZ | Fecha de registro | Sí | - | Auto-generado |
| created_by | BigInteger | Usuario creador | Sí | - | FK virtual a auth.sys_usuarios |
| updated_at | TIMESTAMPTZ | Última actualización | Sí | - | Auto-actualizado |
| updated_by | BigInteger | Usuario que actualizó | No | - | |
| deleted_at | TIMESTAMPTZ | Fecha de borrado | No | - | Soft delete |

**Índices**: PK en id_paciente, INDEX en curp

---

### Tabla: tratamientos
Carpetas de tratamiento por problema específico del paciente.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_tratamiento | BigInteger | Primary Key | Sí | - | Autoincremental |
| id_clinica | BigInteger | Clínica | Sí | - | Default: 1 |
| paciente_id | BigInteger | FK a pacientes | Sí | - | |
| motivo_consulta_principal | Text | Motivo de consulta | Sí | NOM-004 | |
| diagnostico_inicial | Text | Diagnóstico | No | NOM-004 | |
| fecha_inicio | Date | Fecha de inicio | Sí | - | Default: hoy |
| estado_tratamiento | Text | Estado | Sí | - | En Curso, Alta, Pausado, Abandonado |
| plan_general | Text | Plan de tratamiento | No | NOM-004 | |
| firma_electronica | Text | Hash de firma | No | NOM-024 | **NUEVO**: Preparación futura |
| firma_timestamp | TIMESTAMPTZ | Momento de firma | No | NOM-024 | **NUEVO** |
| firma_tipo | String(50) | Tipo de firma | No | NOM-024 | **NUEVO**: FIEL, e.firma, etc. |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |
| updated_at | TIMESTAMPTZ | Última actualización | Sí | - | Auto-actualizado |
| updated_by | BigInteger | Usuario que actualizó | No | - | |
| deleted_at | TIMESTAMPTZ | Fecha de borrado | No | - | Soft delete |

---

### Tabla: evoluciones_clinicas
Notas clínicas SOAP por cada visita/consulta.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_evolucion | BigInteger | Primary Key | Sí | - | Autoincremental |
| id_clinica | BigInteger | Clínica | Sí | - | Default: 1 |
| tratamiento_id | BigInteger | FK a tratamientos | Sí | - | |
| cita_id | BigInteger | FK virtual a ops.citas | No | - | Cross-DB |
| podologo_id | BigInteger | FK virtual a ops.podologos | No | - | Cross-DB |
| fecha_visita | TIMESTAMPTZ | Fecha de la visita | Sí | - | Auto-generado |
| nota_subjetiva | Text | S: Subjetivo | No | NOM-004 SOAP | Lo que el paciente dice |
| nota_objetiva | Text | O: Objetivo | No | NOM-004 SOAP | Observaciones médicas |
| analisis_texto | Text | A: Análisis | No | NOM-004 SOAP | Diagnóstico/interpretación |
| plan_texto | Text | P: Plan | No | NOM-004 SOAP | Plan de tratamiento |
| signos_vitales_visita | JSONB | Signos vitales | No | NOM-004 | PA, FC, temp, glucosa |
| firma_electronica | Text | Hash de firma | No | NOM-024 | **NUEVO**: Preparación futura |
| firma_timestamp | TIMESTAMPTZ | Momento de firma | No | NOM-024 | **NUEVO** |
| firma_tipo | String(50) | Tipo de firma | No | NOM-024 | **NUEVO** |
| created_by | BigInteger | Usuario creador | No | - | FK virtual a auth.sys_usuarios |

---

### Tabla: cat_diagnosticos (NOM-024 NEW)
Catálogo de diagnósticos según CIE-10.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | - | Autoincremental |
| codigo_cie10 | String(10) | Código CIE-10 | Sí | NOM-024 | UNIQUE, ej: "B35.1" |
| descripcion | String(500) | Descripción | Sí | - | En español |
| categoria | String(100) | Categoría | No | - | Para búsquedas |
| activo | Boolean | Activo | Sí | - | Default: true |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

**Status**: Estructura preparada, se llenará con catálogo oficial cuando se busque certificación.

---

### Tabla: cat_procedimientos (NOM-024 NEW)
Catálogo de procedimientos médicos.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | - | Autoincremental |
| codigo | String(20) | Código | Sí | NOM-024 | UNIQUE |
| descripcion | String(500) | Descripción | Sí | - | |
| duracion_estimada_min | Integer | Duración (min) | No | - | Para agenda |
| activo | Boolean | Activo | Sí | - | Default: true |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

---

### Tabla: cat_medicamentos (NOM-024 NEW)
Catálogo de medicamentos según Cuadro Básico.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id | BigInteger | Primary Key | Sí | - | Autoincremental |
| clave_cuadro_basico | String(20) | Clave oficial | No | NOM-024 | UNIQUE |
| nombre_generico | String(200) | Nombre genérico | Sí | - | |
| nombre_comercial | String(200) | Nombre comercial | No | - | |
| presentacion | String(100) | Presentación | No | - | Tabletas, pomada, etc. |
| concentracion | String(50) | Concentración | No | - | 500mg, 10ml, etc. |
| activo | Boolean | Activo | Sí | - | Default: true |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |

---

## Base de Datos: clinica_ops_db (Schema: ops)

### Tabla: podologos
Profesionales que atienden en la clínica.

| Campo | Tipo | Descripción | Obligatorio | Norma | Comentarios |
|-------|------|-------------|-------------|-------|-------------|
| id_podologo | BigInteger | Primary Key | Sí | - | Autoincremental |
| id_clinica | BigInteger | Clínica | Sí | - | Default: 1 |
| usuario_sistema_id | BigInteger | FK virtual a auth.sys_usuarios | No | - | Para login |
| nombre_completo | Text | Nombre completo | Sí | - | |
| cedula_profesional | Text | Cédula profesional | No | NOM-024 | UNIQUE, opcional ahora |
| especialidad | Text | Especialidad | No | - | Default: Podología General |
| institucion_titulo | String(200) | Institución del título | No | NOM-024 | **NUEVO**: Opcional ahora |
| activo | Boolean | Activo | Sí | - | Default: true |
| created_at | TIMESTAMPTZ | Fecha de creación | Sí | - | Auto-generado |
| updated_at | TIMESTAMPTZ | Última actualización | Sí | - | Auto-actualizado |
| deleted_at | TIMESTAMPTZ | Fecha de borrado | No | - | Soft delete |

---

## Notas Importantes

### Campos NOM-024
Todos los campos marcados como "NOM-024" son requeridos por la norma pero se han dejado **opcionales** (nullable=True) para:
- No romper datos existentes
- Permitir transición gradual
- Facilitar implementación sin trámites burocráticos

Cuando se busque certificación oficial, estos campos deberán:
1. Validarse en la aplicación
2. Hacerse obligatorios mediante migración
3. Llenarse con catálogos oficiales (CIE-10, CLUES, etc.)

### Inmutabilidad
La tabla `audit_logs_inmutable` debe protegerse con trigger PostgreSQL:
```sql
CREATE OR REPLACE FUNCTION prevent_audit_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_logs_inmutable is append-only. Modifications not allowed.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER protect_audit_log
BEFORE UPDATE OR DELETE ON auth.audit_logs_inmutable
FOR EACH ROW EXECUTE FUNCTION prevent_audit_modification();
```

### Cross-Database References
Los campos marcados como "FK virtual" NO tienen Foreign Key real (SQLAlchemy no lo soporta entre BDs).
Las validaciones deben hacerse en la capa de aplicación.

### Soft Deletes
Todas las tablas principales usan `deleted_at` para borrado lógico.
Nunca usar DELETE físico excepto para purges administrativos.

---

**Última actualización**: 13 de diciembre de 2025  
**Próxima revisión**: Al iniciar proceso de certificación NOM-024
