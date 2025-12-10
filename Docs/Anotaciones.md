# Notas para Implementación de Workflow LLM+LangGraph

## ✅ Viabilidad de Consultas Complejas

**Conclusión**: La BD está **preparada** (4.5/5) para NL→SQL con LLM.

---

## 📋 Ejemplos de Consultas Soportadas

### 1. Pacientes nuevos por periodo (agregación temporal)

**Tabla**: `clinic.pacientes`
**Técnica**: `DATE_TRUNC` + `GROUP BY` + filtro `deleted_at IS NULL`
**Calificación**: ⭐⭐⭐⭐⭐

### 2. Tratamientos activos sin citas (JOIN cross-DB)

**Tablas**: `clinic.pacientes`, `clinic.tratamientos`, `ops.citas`

**⚠️ DESAFÍO**: PostgreSQL NO permite JOINs directos entre diferentes databases

**Soluciones**:

- **A) Foreign Data Wrapper (FDW)**: Crear tablas "espejo" via `postgres_fdw`
- **B) 2 Queries en Python**: Query en core_db + Query en ops_db, combinar en aplicación

**Calificación**: ⭐⭐⭐⭐

### 3. Ingresos por podólogo (agregación financiera)

**Tablas**: `ops.podologos`, `ops.citas`, `finance.pagos`

**✅ VENTAJA**: Todas en `clinica_ops_db` (diferentes schemas, misma BD)

**Técnica**: `LEFT JOIN` + `SUM()` + `AVG()` + `GROUP BY`

**Calificación**: ⭐⭐⭐⭐⭐

### 4. Pacientes diabéticos con IMC alto sin visitas (análisis clínico)

**Tablas**: `clinic.pacientes`, `clinic.historial_medico_general`, `clinic.tratamientos`, `clinic.evoluciones_clinicas`

**✅ VENTAJA ESPECIAL**: Columna `imc` es **COMPUTED** automáticamente por PostgreSQL

**Técnica**: JOIN + `HAVING` + `INTERVAL` + `AGE()`

**Calificación**: ⭐⭐⭐⭐⭐

---

## 📊 Fortalezas de la BD

1. **Nomenclatura clara**: Tablas/columnas descriptivas
2. **Soft deletes consistentes**: `deleted_at` en todas las tablas
3. **TIMESTAMPTZ**: Perfecto para agregaciones temporales
4. **Computed columns**: IMC calculado automáticamente
5. **Foreign Keys**: Integridad referencial con CASCADE/RESTRICT
6. **Normalización 3NF**: Buena separación de responsabilidades

## ⚠️ Limitaciones

- **Cross-DB Queries**: Requiere FDW o 2 queries en aplicación
- **Índices**: Faltan en columnas de búsqueda frecuente

---

## 🛠️ Recomendaciones para Workflow

### A) Vistas Materializadas (opcional para cross-DB)

Crear `v_pacientes_completos` con datos de múltiples BDs, refrescar periódicamente.

### B) Documentar Esquema con COMMENT ON

```sql
COMMENT ON TABLE clinic.pacientes IS 'Expedientes clínicos';
COMMENT ON COLUMN clinic.historial_medico_general.imc IS 'IMC auto-calculado: peso/(talla/100)²';
```

### C) Índices para Reportes Frecuentes

```sql
-- Pacientes por periodo
CREATE INDEX idx_pacientes_fecha_registro ON clinic.pacientes(fecha_registro) WHERE deleted_at IS NULL;

-- Diabéticos con IMC alto
CREATE INDEX idx_historial_diabetes_imc ON clinic.historial_medico_general(app_diabetes, imc);

-- Evoluciones por fecha
CREATE INDEX idx_evoluciones_fecha ON clinic.evoluciones_clinicas(fecha_visita DESC);
```

---

## 🚀 Contexto para LangGraph (Prompts)

```python
DATABASE_SCHEMA_CONTEXT = """
=== ARQUITECTURA MULTI-BD ===

BASES DE DATOS:
- clinica_auth_db.auth → Usuarios, roles, auditoría
- clinica_core_db.clinic → Pacientes, tratamientos, evoluciones
- clinica_ops_db.ops → Citas, podólogos, servicios
- clinica_ops_db.finance → Pagos, gastos, transacciones

REGLAS CRÍTICAS:
- SIEMPRE filtrar 'deleted_at IS NULL' (soft delete)
- Fechas son TIMESTAMPTZ (incluyen zona horaria)
- IMC es COMPUTED (no insertar manualmente)
- Cross-database JOINs NO soportados (usar 2 queries)

RELACIONES:
- pacientes (1) → (N) tratamientos
- tratamientos (1) → (N) evoluciones_clinicas
- pacientes (1) → (1) historial_medico_general
- citas (N) → (1) pacientes [CROSS-DB]
- pagos (N) → (1) citas

COLUMNAS PARA REPORTES:
- pacientes.fecha_registro → Nuevos por periodo
- tratamientos.estado_tratamiento → 'En Curso', 'Alta', 'Pausado'
- historial_medico_general.app_diabetes → Boolean
- historial_medico_general.imc → Auto-calculado
- evoluciones_clinicas.fecha_visita → Última visita
"""
```

---

## ✅ Checklist Implementación

1. Implementar FDW o estrategia 2-queries para cross-DB
2. Crear índices en columnas de búsqueda frecuente
3. Documentar esquema con `COMMENT ON`
4. Crear archivo de contexto DB para prompts LLM
5. Implementar nodos LangGraph (NL→SQL, SQL Executor, Response)

**Calificación final BD**: ⭐⭐⭐⭐ (4.5/5) - Lista para NL→SQL
