# 🤖 Arquitectura del Chatbot Conversacional Natural - PodoSkin

**Fecha:** 14 de Diciembre de 2024  
**Versión:** 1.0  
**Estado:** Implementación en progreso

---

## 📋 Tabla de Contenidos

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Workflows vs Agentes](#workflows-vs-agentes)
4. [Middleware y Guardrails](#middleware-y-guardrails)
5. [Observabilidad](#observabilidad)
6. [Flujo de Conversación](#flujo-de-conversación)
7. [Casos de Uso](#casos-de-uso)
8. [Referencias](#referencias)

---

## Visión General

Este sistema implementa un chatbot conversacional natural para la clínica podológica PodoSkin, siguiendo las mejores prácticas de LangGraph y LangChain para combinar:

- **Workflows**: Procesos determinísticos y repetibles (CRUD, validaciones, transacciones)
- **Agentes con Criterio**: Conversación natural con decisiones controladas por guardrails
- **Middleware**: Control de seguridad, sanitización y cumplimiento
- **Observabilidad**: Trazabilidad completa con LangSmith

### Principios de Diseño

1. **Separación de Responsabilidades**: Workflows para procesos administrativos, Agentes para interacción natural
2. **Seguridad Primero**: Todos los inputs pasan por validación y sanitización
3. **Guardrails Clínicos**: Decisiones médicas requieren revisión humana
4. **Trazabilidad Total**: Toda interacción es auditable y observable
5. **Escalamiento Inteligente**: El sistema sabe cuándo pedir ayuda humana

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                       USUARIO (Frontend)                        │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 │ HTTP/WebSocket
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API ENDPOINT (/chat)                         │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              1. VALIDACIÓN DE ENTRADA                     │  │
│  │  - JWT Authentication                                     │  │
│  │  - Rate Limiting                                          │  │
│  │  - Input Validation                                       │  │
│  └──────────────┬───────────────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MIDDLEWARE LAYER                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. PROMPT CONTROLLER                                     │  │
│  │  - Sanitización de prompt                                 │  │
│  │  - Detección de inyección                                 │  │
│  │  - Análisis de riesgo                                     │  │
│  └──────────────┬───────────────────────────────────────────┘  │
│                 │                                                │
│  ┌──────────────▼───────────────────────────────────────────┐  │
│  │  3. GUARDRAILS                                            │  │
│  │  - Detección de temas sensibles                           │  │
│  │  - Validación de permisos por rol                         │  │
│  │  - Decisión de escalamiento                               │  │
│  └──────────────┬───────────────────────────────────────────┘  │
└─────────────────┼───────────────────────────────────────────────┘
                  │
                  ▼
         ┌────────┴────────┐
         │                 │
    ¿Workflow             ¿Agente
    o Agente?             Conversacional?
         │                 │
         ▼                 ▼
┌──────────────────┐  ┌──────────────────┐
│   WORKFLOWS      │  │   AGENTES        │
│                  │  │                  │
│ - Pacientes      │  │ - Chat Clínica   │
│ - Citas          │  │ - Evoluciones    │
│ - Tratamientos   │  │ - General        │
│ - Finanzas       │  │                  │
│                  │  │ Integrado con:   │
│ Características: │  │ - LangGraph      │
│ - Determinístico │  │ - Memoria        │
│ - Transaccional  │  │ - LLM (Claude)   │
│ - Rollback       │  │ - Tools          │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         │                     ▼
         │            ┌──────────────────┐
         │            │  LANGGRAPH       │
         │            │  StateGraph      │
         │            │                  │
         │            │ - Nodes          │
         │            │ - Edges          │
         │            │ - Checkpointing  │
         │            └────────┬─────────┘
         │                     │
         └─────────┬───────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│              4. OBSERVABILITY MIDDLEWARE                        │
│  - Trace de interacción completa                                │
│  - Log de errores                                               │
│  - Métricas de rendimiento                                      │
│  - Integración con LangSmith                                    │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      5. RESPUESTA                               │
│  - Formato estructurado (JSON)                                  │
│  - Mensaje natural para usuario                                 │
│  - Datos para UI                                                │
│  - Indicadores de revisión humana                               │
│  - Trace ID para debugging                                      │
└────────────────┬────────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    USUARIO (Frontend)                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Workflows vs Agentes

### Workflows (Procesos Determinísticos)

**Cuándo usar Workflows:**
- Operaciones CRUD estándar
- Procesos con pasos bien definidos
- Transacciones que requieren atomicidad
- Validaciones de negocio complejas

**Ejemplo: Crear Paciente**
```python
workflow = PacientesWorkflow(context)
result = await workflow.execute(
    action="create",
    data={
        "nombres": "María",
        "apellidos": "García",
        "telefono": "5551234567"
    }
)
# Workflow automáticamente:
# 1. Valida permisos
# 2. Verifica duplicados
# 3. Crea paciente
# 4. Genera código interno
# 5. Registra auditoría
# 6. Retorna resultado o hace rollback
```

**Características:**
- ✅ Predecible y testeable
- ✅ Rollback automático
- ✅ Auditoría integrada
- ✅ Validación de permisos
- ❌ No toma decisiones autónomas

### Agentes (Conversación Natural con Criterio)

**Cuándo usar Agentes:**
- Consultas en lenguaje natural
- Búsqueda y exploración
- Asistencia conversacional
- Decisiones que requieren contexto

**Ejemplo: Consulta de Citas**
```python
agent = ChatClinicaAgent(
    user_id=5,
    user_role="Podologo"
)
response = await agent.process(
    "Muéstrame las citas de mañana que tengan pendiente de pago"
)
# Agente automáticamente:
# 1. Valida y sanitiza input
# 2. Verifica guardrails
# 3. Clasifica intención
# 4. Genera y ejecuta SQL si es seguro
# 5. Formatea respuesta natural
# 6. Registra trace
```

**Características:**
- ✅ Conversación natural
- ✅ Contexto multi-turno
- ✅ Guardrails integrados
- ✅ Observabilidad completa
- ⚠️ Requiere supervisión para acciones críticas

---

## Middleware y Guardrails

### 1. Prompt Controller

**Propósito:** Prevenir ataques de inyección de prompts y contenido malicioso.

**Funciones:**
- Sanitización de input
- Detección de patrones peligrosos
- Análisis de riesgo (SAFE, LOW, MEDIUM, HIGH, CRITICAL)
- Truncado de prompts largos

**Ejemplo de Patrones Bloqueados:**
```python
DANGEROUS_PATTERNS = [
    r"ignore\s+(previous|above|all)\s+(instructions|rules)",
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
    r"<\s*script\s*>",
]
```

### 2. Guardrails

**Propósito:** Proteger decisiones clínicas y datos sensibles.

**Reglas:**
1. **Diagnósticos Clínicos**: Requieren revisión de profesional
2. **Prescripciones**: Bloqueadas para IA, solo humanos
3. **Datos Sensibles**: No se procesan contraseñas ni API keys
4. **Permisos por Rol**: 
   - Recepción: Solo agenda y datos de contacto
   - Podólogo: Datos clínicos completos
   - Admin: Todo

**Ejemplo de Decisión:**
```python
# Usuario pregunta: "¿Qué medicamento debo tomar para la infección?"
guardrail_decision = guardrails.check(input, user_role)

# Resultado:
GuardrailDecision(
    should_block=True,
    requires_human=True,
    reason="clinical_diagnosis",
    message="Esta consulta requiere revisión de un profesional médico",
    escalation_notes="Pregunta sobre medicación específica"
)
```

### 3. Observabilidad

**Propósito:** Trazabilidad y debugging.

**Logs Capturados:**
- Timestamp de cada interacción
- User ID y rol
- Input original y sanitizado
- Decisiones de guardrails
- Respuesta del agente
- Tiempo de ejecución
- Errores y warnings

**Integración con LangSmith:**
```python
# Se activa automáticamente con:
export LANGSMITH_API_KEY="lsv2_..."

# Cada interacción genera un trace_id único
# visible en: https://smith.langchain.com/
```

---

## Flujo de Conversación

### Escenario 1: Consulta Simple (SAFE)

**Usuario:** "¿Cuántos pacientes tenemos?"

```
1. Validación JWT ✓
2. Rate Limit Check ✓
3. Prompt Controller → SAFE ✓
4. Guardrails → Permitir ✓
5. Agente → Clasificar intent: query_aggregate
6. Generar SQL: SELECT COUNT(*) FROM pacientes
7. Ejecutar consulta
8. Respuesta: "Tienes 234 pacientes registrados."
9. Trace registrado ✓
```

### Escenario 2: Consulta Sensible (REQUIRES_REVIEW)

**Usuario Recepción:** "Muéstrame el diagnóstico del paciente Juan"

```
1. Validación JWT ✓
2. Rate Limit Check ✓
3. Prompt Controller → LOW (keyword: diagnóstico)
4. Guardrails → BLOCK (Recepción no puede ver diagnósticos)
5. Respuesta: "No tienes permisos para ver información clínica."
6. Escalamiento registrado para Admin
7. Trace con flag de seguridad ✓
```

### Escenario 3: Solicitud de Acción Crítica (HUMAN_REVIEW)

**Usuario Podólogo:** "Marca al paciente 123 como diabético tipo 2"

```
1. Validación JWT ✓
2. Rate Limit Check ✓
3. Prompt Controller → MEDIUM (diagnóstico médico)
4. Guardrails → REQUIRES_REVIEW
5. Respuesta: "Esta acción requiere confirmación. ¿Deseas continuar? (S/N)"
6. Usuario confirma → Ejecutar acción
7. Auditoría completa registrada ✓
8. Trace con nota de confirmación humana ✓
```

---

## Casos de Uso

### 1. Consulta de Agenda

**Input:** "Muéstrame mis citas de esta semana"

**Procesamiento:**
- Workflow: No (es consulta, no modificación)
- Agente: Sí (consulta conversacional)
- Guardrails: Permitir (lectura de datos propios)
- SQL generado: `SELECT * FROM citas WHERE podologo_id = {user_id} AND fecha_cita BETWEEN ...`

**Output:**
```
📅 **Citas de esta semana**

**Lunes 14 de Diciembre:**
- 10:00 AM - María García (Revisión)
- 11:30 AM - Juan Pérez (Primera consulta)

**Martes 15 de Diciembre:**
- 09:00 AM - Ana López (Seguimiento)

Total: 3 citas programadas
```

### 2. Creación de Paciente

**Input:** "Crea un nuevo paciente: Carlos Mendoza, tel 5551234567"

**Procesamiento:**
- Workflow: Sí (operación transaccional)
- Guardrails: Verificar permisos (solo Admin/Podologo)
- Workflow ejecuta:
  1. Parsear datos del input
  2. Verificar duplicados por teléfono
  3. Crear paciente en BD
  4. Generar código interno
  5. Registrar auditoría

**Output:**
```
✅ **Paciente creado exitosamente**

**Datos:**
- ID: 235
- Nombre: Carlos Mendoza
- Teléfono: 5551234567
- Código: EZJU-1214-00235

⚠️ Advertencia: Se encontró un paciente con teléfono similar. Verifica que no sea duplicado.
```

### 3. Consulta Clínica con Guardrail

**Input (Recepción):** "¿Qué tratamiento tiene el paciente 50?"

**Procesamiento:**
- Agente: Sí
- Guardrails: BLOCK (Recepción + información clínica)
- Escalamiento activado

**Output:**
```
🚫 **Acceso restringido**

Esta información es confidencial y requiere autorización de un profesional clínico.

Si necesitas acceso, contacta a tu supervisor.

*Referencia de solicitud: REQ-2024-12-14-001*
```

---

## Referencias

### Documentación LangGraph y LangChain

1. **Workflows y Agentes**  
   https://docs.langchain.com/oss/python/langgraph/workflows-agents  
   Guía sobre cuándo usar workflows vs agentes

2. **Middleware**  
   https://docs.langchain.com/oss/python/langchain/middleware  
   Control de prompts, tool calls y salidas

3. **Agentes**  
   https://docs.langchain.com/oss/python/langchain/agents  
   Fundamentos de construcción de agentes

4. **LangGraph Overview**  
   https://docs.langchain.com/oss/python/langgraph/overview  
   Introducción general a LangGraph

5. **LangSmith Observabilidad**  
   https://docs.langsmith.dev/observability  
   Trazabilidad y debugging

### Documentación Interna

- `API_REFERENCE_FRONTEND.md` - Referencia completa de API
- `API_ENDPOINTS_GUIA_COMPLETA.md` - Guía de endpoints
- `backend/middleware/` - Implementación de middleware
- `backend/workflows/` - Implementación de workflows
- `backend/conversational_agents/` - Implementación de agentes

---

**Última actualización:** 14 de Diciembre de 2024  
**Versión:** 1.0  
**Autor:** Sistema de IA Copilot
