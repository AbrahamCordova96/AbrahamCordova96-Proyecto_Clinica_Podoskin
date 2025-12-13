# 🎯 PROMPT PARA AGENTE: Implementación NOM-024 Pragmática

## Contexto Rápido
Somos una **clínica podológica privada NO certificada aún**. No necesitamos cumplir TODO de la NOM-024 AHORA, pero queremos dejar el sistema **listo para certificar en el futuro** sin rehacer todo.

**Meta**: Implementar lo que podamos hacer con código (sin trámites burocráticos) y preparar campos/estructura para lo que vendrá después.

---

## 🚫 LO QUE NO DEBES HACER (Sin trámites de gobierno)

**NO implementes**:
- Firma electrónica FIEL/e.firma del SAT (requiere trámites)
- Validación en tiempo real con RENAPO (requiere convenios)
- Certificación ante DGIS (requiere auditoría oficial)
- Catálogos oficiales completos (CIE-10, CLUES, etc.) - solo deja la estructura preparada

**NO hagas campos obligatorios** si son para "futuro":
- Si agregamos campo `cedula_profesional`, déjalo opcional por ahora
- Si agregamos `clues_establecimiento`, opcional
- Comentar en código: `# Opcional ahora, será obligatorio para certificación`

---

## ✅ LO QUE SÍ DEBES IMPLEMENTAR (19 Preguntas del Informe)

### **BLOQUE 1: Audit Log Inmutable (CRÍTICO)**

**Problema**: Audit log actual puede tener debilidades de inmutabilidad.

**Solución**:
1. Crear tabla `audit_logs_inmutable` (append-only, sin UPDATE/DELETE permitido)
2. Trigger PostgreSQL que bloquee modificaciones
3. Guardar estado COMPLETO antes del cambio (no solo deltas)
4. Campos: `id`, `timestamp`, `user_id`, `username_snapshot`, `tabla_afectada`, `registro_id`, `accion` (INSERT/UPDATE/DELETE), `datos_antes` (JSONB), `datos_despues` (JSONB)

**Archivos a modificar**:
- `backend/schemas/auth/models.py` - Crear modelo `AuditLogInmutable`
- `backend/api/deps/audit.py` - Función decorador `@audit_action`
- Migración Alembic

---

### **BLOQUE 2: Identificación de Pacientes (Campos Mínimos)**

**Problema**: Faltan campos obligatorios de la Tabla 1 NOM-024.

**Solución**: Agregar a tabla `pacientes` (opcionales por ahora):
```python
# Campos NOM-024 Tabla 1
curp = Column(String(18), nullable=True, index=True)  # Opcional ahora
primer_apellido = Column(String(50))  # Ya existe como "apellidos"
segundo_apellido = Column(String(50), nullable=True)  # NUEVO
estado_nacimiento = Column(String(2), nullable=True)  # Catálogo INEGI
nacionalidad = Column(String(3), nullable=True, default='MEX')  # ISO 3166
estado_residencia = Column(String(2), nullable=True)
municipio_residencia = Column(String(3), nullable=True)
localidad_residencia = Column(String(4), nullable=True)
```

**Validaciones**:
- CURP formato: 18 caracteres alfanuméricos
- Campo `sexo` debe ser `H` o `M` (no `M`, `F`)
- Fecha nacimiento: formato ISO 8601

**Archivos**:
- `backend/schemas/core/models.py` - Modelo `Paciente`
- `backend/schemas/core/schemas.py` - Schemas Pydantic
- `backend/api/routes/pacientes.py` - Validaciones

---

### **BLOQUE 3: Identificación de Profesionales**

**Problema**: Falta información de médicos para reportes oficiales.

**Solución**: Agregar a tabla `podologos`:
```python
cedula_profesional = Column(String(20), nullable=True)  # Futuro obligatorio
especialidad = Column(String(100), nullable=True)
institucion_titulo = Column(String(200), nullable=True)
```

**Archivos**:
- `backend/schemas/ops/models.py` - Modelo `Podologo`

---

### **BLOQUE 4: Catálogos (Estructura Preparada)**

**Problema**: No hay tablas para catálogos oficiales.

**Solución**: Crear tablas (vacías o con datos genéricos):
```python
# Nuevas tablas en schema "clinic"
class CatDiagnostico(Base):
    id = Column(BigInteger, primary_key=True)
    codigo_cie10 = Column(String(10), unique=True)  # Ej: "B35.1"
    descripcion = Column(String(500))
    activo = Column(Boolean, default=True)

class CatProcedimiento(Base):
    id = Column(BigInteger, primary_key=True)
    codigo = Column(String(20), unique=True)
    descripcion = Column(String(500))
    activo = Column(Boolean, default=True)

class CatMedicamento(Base):
    id = Column(BigInteger, primary_key=True)
    clave_cuadro_basico = Column(String(20), nullable=True)
    nombre_generico = Column(String(200))
    activo = Column(Boolean, default=True)
```

**NO llenes con datos oficiales ahora** - solo crea la estructura.

**Archivos**:
- `backend/schemas/core/models.py`
- Migración Alembic

---

### **BLOQUE 5: RBAC (Control de Acceso)**

**Problema**: Verificar que roles/permisos estén bien implementados.

**Checklist**:
- ✅ Tabla `sys_usuarios` tiene campo `rol`
- ✅ Enum `UserRole` con Admin, Podologo, Recepcion
- ✅ Decoradores `@require_role()` en endpoints
- ⚠️ **AGREGAR**: Tabla `permisos` para granularidad futura

**Solución**:
```python
class Permiso(Base):
    id = Column(BigInteger, primary_key=True)
    nombre = Column(String(100), unique=True)  # "leer_expediente"
    descripcion = Column(String(200))

class RolPermiso(Base):
    rol = Column(Enum(UserRole))
    permiso_id = Column(BigInteger, ForeignKey('permisos.id'))
```

**Archivos**:
- `backend/schemas/auth/models.py`
- Dejar comentado: "# Futuro: implementar permisos granulares"

---

### **BLOQUE 6: Campos para Firma Electrónica (Preparación)**

**Problema**: No hay donde guardar firmas electrónicas.

**Solución**: Agregar a tablas críticas (`evoluciones`, `tratamientos`):
```python
# Campos para futuro
firma_electronica = Column(Text, nullable=True)  # Hash de firma
firma_timestamp = Column(TIMESTAMP(timezone=True), nullable=True)
firma_tipo = Column(String(50), nullable=True)  # 'FIEL', 'e.firma', etc.
```

**Archivos**:
- `backend/schemas/core/models.py`

---

### **BLOQUE 7: Log de Accesos (No solo modificaciones)**

**Problema**: Solo auditas cambios, no consultas.

**Solución**: Crear tabla `access_logs`:
```python
class AccessLog(Base):
    id = Column(BigInteger, primary_key=True)
    timestamp = Column(TIMESTAMP(timezone=True), default=func.now())
    user_id = Column(BigInteger)
    accion = Column(String(50))  # "consultar_expediente"
    recurso = Column(String(100))  # "paciente_123"
    ip_address = Column(String(50))
```

**Implementar en endpoints críticos**:
- GET `/pacientes/{id}`
- GET `/tratamientos/{id}`
- GET `/evoluciones`

**Archivos**:
- `backend/schemas/auth/models.py`
- `backend/api/deps/audit.py` - Función `log_access()`

---

### **BLOQUE 8: Exportación de Expedientes**

**Problema**: No hay forma de exportar expediente completo.

**Solución**: Crear endpoint `/api/v1/pacientes/{id}/exportar`:
```python
@router.get("/{id}/exportar")
async def exportar_expediente(
    id: int,
    formato: str = Query("html", regex="^(html|json|xml)$"),
    db: Session = Depends(get_core_db)
):
    # Recopilar TODO del paciente
    paciente = db.query(Paciente).filter_by(id_paciente=id).first()
    tratamientos = db.query(Tratamiento).filter_by(paciente_id=id).all()
    evoluciones = db.query(Evolucion).join(Tratamiento).filter(...)
    evidencias = ...
    
    if formato == "html":
        return generar_html_expediente(paciente, tratamientos, evoluciones)
    elif formato == "json":
        return exportar_json_estructurado(...)
    elif formato == "xml":
        return exportar_xml_preparado_hl7(...)  # Estructura similar a CDA
```

**HTML**: Diseño elegante con CSS formal (tipo certificado médico).

**JSON**: Estructura que mapee a HL7 CDA (preparación futura):
```json
{
  "clinicalDocument": {
    "patient": {
      "id": "...",
      "name": {"given": "Juan", "family": "Pérez"},
      "birthDate": "1990-05-15"
    },
    "encounters": [...],
    "diagnoses": [...],
    "procedures": [...]
  }
}
```

**Archivos**:
- `backend/api/routes/pacientes.py`
- `backend/utils/exporters.py` - Funciones de exportación
- `backend/templates/expediente.html` - Template HTML

---

### **BLOQUE 9: Campos de Interoperabilidad**

**Problema**: Faltan campos para compartir información.

**Solución**: Agregar a tabla `clinicas`:
```python
clues = Column(String(12), nullable=True)  # Clave Única Establecimiento Salud
```

Agregar a `pacientes`:
```python
consentimiento_intercambio = Column(Boolean, default=False)
fecha_consentimiento = Column(Date, nullable=True)
```

**Archivos**:
- `backend/schemas/auth/models.py` (clinicas)
- `backend/schemas/core/models.py` (pacientes)

---

### **BLOQUE 10: Timestamps Consistentes**

**Problema**: Verificar que todas las fechas usen formato consistente.

**Checklist**:
- ✅ Usar `TIMESTAMP(timezone=True)` en PostgreSQL
- ✅ Serializar a ISO 8601 en JSON
- ✅ Campo `created_at` en todas las tablas importantes

**Acción**: Revisar modelos y corregir si hay inconsistencias.

---

### **BLOQUE 11: Backup Automatizado**

**Problema**: Verificar si existe proceso de backup.

**Solución**: Crear script `backup_database.sh`:
```bash
#!/bin/bash
# Backup diario de las 3 bases de datos
docker exec podoskin-db pg_dump -U podoskin clinica_auth_db > backup_auth_$(date +%Y%m%d).sql
docker exec podoskin-db pg_dump -U podoskin clinica_core_db > backup_core_$(date +%Y%m%d).sql
docker exec podoskin-db pg_dump -U podoskin clinica_ops_db > backup_ops_$(date +%Y%m%d).sql
```

Agregar a `docker-compose.yml`:
```yaml
services:
  backup:
    image: postgres:15
    volumes:
      - ./backups:/backups
    command: /backup_script.sh
    depends_on:
      - db
```

**Archivos**:
- `scripts/backup_database.sh`
- `docker-compose.yml`

---

### **BLOQUE 12: Documentación del Modelo**

**Problema**: Falta diccionario de datos.

**Solución**: Crear `Docs/DICCIONARIO_DATOS.md`:
```markdown
# Diccionario de Datos - PodoSkin

## Tabla: pacientes (schema: clinic)
| Campo | Tipo | Descripción | Obligatorio | Norma |
|-------|------|-------------|-------------|-------|
| id_paciente | BigInteger | PK | Sí | - |
| curp | String(18) | CURP validada | No (futuro sí) | NOM-024 Tabla 1 |
| nombres | String(100) | Nombre(s) completo(s) | Sí | NOM-024 |
...
```

**Archivos**:
- `Docs/DICCIONARIO_DATOS.md`

---

### **BLOQUE 13: Reportes Estadísticos**

**Problema**: Necesitas poder extraer estadísticas.

**Solución**: Crear endpoint `/api/v1/reportes/estadisticas`:
```python
@router.get("/estadisticas")
async def estadisticas_clinica(
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_core_db)
):
    return {
        "total_consultas": ...,
        "diagnosticos_frecuentes": [...],
        "pacientes_nuevos": ...,
        "procedimientos_realizados": [...]
    }
```

**Archivos**:
- `backend/api/routes/reportes.py` (nuevo)

---

## 📊 PRIORIDADES DE IMPLEMENTACIÓN

### **Fase 1 (CRÍTICO - Hacer primero)**:
1. ✅ Audit Log Inmutable (Bloque 1)
2. ✅ Campos NOM-024 en Pacientes (Bloque 2)
3. ✅ Exportación HTML de Expedientes (Bloque 8)
4. ✅ Log de Accesos (Bloque 7)

### **Fase 2 (IMPORTANTE - Esta semana)**:
5. ✅ Catálogos (estructura) (Bloque 4)
6. ✅ Campos de Firma Electrónica (Bloque 6)
7. ✅ Campos Interoperabilidad (Bloque 9)
8. ✅ Backup Automatizado (Bloque 11)

### **Fase 3 (PREPARACIÓN - Cuando tengas tiempo)**:
9. ⚠️ RBAC granular (Bloque 5)
10. ⚠️ Reportes estadísticos (Bloque 13)
11. ⚠️ Diccionario de datos (Bloque 12)
12. ⚠️ Exportación XML/HL7-ready (Bloque 8)

---

## 🎨 ESPECIFICACIONES HTML DE EXPEDIENTE

**Template**: `backend/templates/expediente.html`

**Diseño**:
```html
<!DOCTYPE html>
<html>
<head>
    <style>
        @media print {
            .no-print { display: none; }
        }
        body {
            font-family: 'Times New Roman', serif;
            max-width: 210mm; /* A4 */
            margin: auto;
            padding: 20mm;
        }
        .header {
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
        }
        .section {
            margin-top: 20px;
            page-break-inside: avoid;
        }
        .section-title {
            background: #f0f0f0;
            padding: 5px 10px;
            font-weight: bold;
            border-left: 4px solid #333;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        td, th {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Expediente Clínico</h1>
        <p>Clínica Podológica PodoSkin</p>
    </div>
    
    <div class="section">
        <div class="section-title">Datos del Paciente</div>
        <table>
            <tr><td>Nombre</td><td>{{ paciente.nombres }} {{ paciente.apellidos }}</td></tr>
            <tr><td>CURP</td><td>{{ paciente.curp or 'N/A' }}</td></tr>
            <tr><td>Fecha Nacimiento</td><td>{{ paciente.fecha_nacimiento }}</td></tr>
        </table>
    </div>
    
    <div class="section">
        <div class="section-title">Historial de Consultas</div>
        {% for evolucion in evoluciones %}
        <div class="consulta">
            <p><strong>Fecha:</strong> {{ evolucion.fecha }}</p>
            <p><strong>Médico:</strong> {{ evolucion.podologo.nombre }}</p>
            <p><strong>SOAP:</strong></p>
            <ul>
                <li><strong>S:</strong> {{ evolucion.subjetivo }}</li>
                <li><strong>O:</strong> {{ evolucion.objetivo }}</li>
                <li><strong>A:</strong> {{ evolucion.analisis }}</li>
                <li><strong>P:</strong> {{ evolucion.plan }}</li>
            </ul>
        </div>
        {% endfor %}
    </div>
    
    <div class="no-print">
        <button onclick="window.print()">Imprimir</button>
    </div>
</body>
</html>
```

**Usar Jinja2** para renderizar.

---

## 🚨 RESTRICCIONES Y LÍMITES

### **NO hagas**:
- ❌ Cambiar lógica de negocio existente
- ❌ Modificar endpoints que funcionen bien
- ❌ Romper tests existentes
- ❌ Hacer campos obligatorios que afecten datos existentes

### **SÍ puedes**:
- ✅ Agregar campos opcionales
- ✅ Crear nuevos endpoints
- ✅ Agregar validaciones no-bloqueantes
- ✅ Crear tablas nuevas
- ✅ Documentar TODO con comentarios

---

## 📝 CHECKLIST FINAL

Después de implementar, verifica:

- [ ] Migración Alembic ejecuta sin errores
- [ ] Tests existentes siguen pasando
- [ ] Nuevos campos aparecen en Swagger UI
- [ ] Endpoint de exportación HTML funciona
- [ ] Audit log registra cambios correctamente
- [ ] Backup script funciona
- [ ] Documentación actualizada

---

## 📚 REFERENCIAS

**Documentos legales** (si tienes dudas):
- NOM-024-SSA3-2012: Sistemas de información de registro electrónico para la salud
- NOM-004-SSA3-2012: Expediente clínico
- LFPDPPP: Protección de datos personales

**NO leas TODO** - solo consulta secciones específicas si necesitas clarificar algo.

---

**Última actualización**: 13 de diciembre de 2025
