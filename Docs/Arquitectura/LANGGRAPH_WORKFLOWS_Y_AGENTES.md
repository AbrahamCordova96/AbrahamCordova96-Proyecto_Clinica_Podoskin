# Arquitectura LangGraph: Workflows y Agentes con Criterio Controlado

## Tabla de Contenidos
1. [Visión General](#visión-general)
2. [Arquitectura de Componentes](#arquitectura-de-componentes)
3. [Workflows Determinísticos](#workflows-determinísticos)
4. [Agentes con Criterio Controlado](#agentes-con-criterio-controlado)
5. [Infraestructura y Calidad](#infraestructura-y-calidad)
6. [Guías de Implementación](#guías-de-implementación)
7. [Referencias y Recursos](#referencias-y-recursos)

---

## Visión General

**PodoSkin** implementa una arquitectura híbrida que combina:

- **Workflows** → Procesos determinísticos y repetibles para operaciones administrativas
- **Agentes IA** → Interacciones conversacionales con guardrails y supervisión humana

### Principios Fundamentales

1. **Separación de Responsabilidades**: Workflows manejan procesos de negocio; agentes manejan conversaciones naturales
2. **Seguridad por Diseño**: Guardrails, validación de permisos, y puntos de escalamiento humano
3. **Observabilidad Total**: Trazabilidad completa de decisiones y acciones mediante LangSmith
4. **Conformidad Clínica**: Cumplimiento con NOM-024-SSA3-2013 para expedientes electrónicos

### Beneficios de esta Arquitectura

- ✅ **Mantenibilidad**: Cambios en procesos administrativos no afectan conversaciones IA
- ✅ **Auditabilidad**: Logs completos de cada decisión y acción
- ✅ **Seguridad**: Control granular de permisos y validación en múltiples capas
- ✅ **Escalabilidad**: Workflows y agentes pueden evolucionar independientemente

---

## Arquitectura de Componentes

```
PodoSkin
├── Workflows (Orquestación Determinística)
│   ├── Autenticación y Seguridad
│   ├── Pacientes (CRUD + Historial)
│   ├── Citas (Agenda + Disponibilidad)
│   ├── Tratamientos (Carpetas de Problemas)
│   ├── Evoluciones (Notas SOAP)
│   ├── Evidencias (Fotos Clínicas)
│   ├── Podólogos (Recursos Humanos)
│   ├── Servicios (Catálogo)
│   ├── Prospectos (Leads)
│   ├── Usuarios (Administración)
│   ├── Auditoría (Trazabilidad)
│   ├── Finanzas (Pagos + Transacciones)
│   ├── Historial Médico (Alergias, Antecedentes)
│   ├── Estadísticas (Dashboards)
│   ├── Notificaciones (Recordatorios)
│   └── Integración (Contexto Multi-Sistema)
│
├── Agentes con Criterio (IA Supervisada)
│   ├── Chat Clínica (Asistencia + Comunicación)
│   ├── Asistente de Evoluciones (SOAP + Revisión Humana)
│   └── Agentes de Soporte Clínico (Extensibles)
│
└── Infraestructura
    ├── Middleware (Prompt Control, Guardrails, Sanitización)
    ├── Observabilidad (LangSmith)
    ├── WebSocket (Streaming Tiempo Real)
    └── TTS/Accesibilidad (Lectura por Voz)
```

---

## Workflows Determinísticos

### Qué Son

Flujos secuenciales o paralelos que ejecutan operaciones predefinidas con reglas de negocio claras.

### Características

- **Deterministicos**: Misma entrada → Misma salida
- **Auditables**: Cada paso se registra en `auth.audit_logs`
- **Con Validación**: Permisos RBAC verificados en cada paso
- **Escalables**: Puntos de aprobación humana donde sea necesario

### Módulos de Workflows

#### 1. Autenticación y Seguridad
**Responsabilidad**: Gestión de sesiones JWT, validación de permisos, escalamiento para acciones críticas

**Flujo Típico**:
```
Login → Validar Credenciales → Generar JWT → Registrar Auditoría → Retornar Token
```

**Endpoints Clave**:
- `POST /api/v1/auth/login` - Autenticación con email/usuario/teléfono
- `GET /api/v1/auth/me` - Información del usuario actual
- `POST /api/v1/auth/change-password` - Cambio de contraseña

**Permisos**: Público (login), Autenticado (me, change-password)

---

#### 2. Pacientes
**Responsabilidad**: CRUD de expedientes, verificación de duplicados, historial clínico completo

**Flujo de Creación**:
```
Recibir Datos → Validar Pydantic → Verificar Duplicados (fuzzy) → 
Crear Paciente → Asignar Código Interno → Auditoría → Retornar Expediente
```

**Endpoints Clave**:
- `POST /api/v1/pacientes` - Crear paciente con validación de duplicados
- `GET /api/v1/pacientes` - Listar con paginación y búsqueda fuzzy
- `GET /api/v1/pacientes/{id}` - Detalle de expediente
- `PUT /api/v1/pacientes/{id}` - Actualizar datos
- `GET /api/v1/pacientes/{id}/historial` - Historial clínico completo

**Permisos**: 
- Admin, Podologo → Acceso completo
- Recepcion → Solo lectura de datos de contacto (no historial médico)

**Reglas de Negocio**:
- Soft delete: `deleted_at IS NULL` (nunca DELETE físico)
- Verificación de duplicados: Levenshtein distance en nombres + teléfono
- IMC calculado automáticamente en PostgreSQL si peso/altura disponibles

---

#### 3. Citas
**Responsabilidad**: Agenda, disponibilidad, reservas, cancelaciones, recordatorios

**Flujo de Agendamiento**:
```
Validar Paciente → Validar Podólogo → Verificar Disponibilidad → 
Calcular Duración (según servicio) → Crear Cita → Notificar → Auditoría
```

**Endpoints Clave**:
- `POST /api/v1/citas` - Crear cita con validación de conflictos
- `GET /api/v1/citas` - Listar con filtros (fecha, podólogo, paciente, status)
- `PUT /api/v1/citas/{id}` - Actualizar status o reprogramar
- `DELETE /api/v1/citas/{id}` - Cancelar (soft delete)
- `GET /api/v1/citas/disponibilidad` - Horarios libres

**Permisos**: 
- Admin, Podologo, Recepcion → Todos

**Reglas de Negocio**:
- **No se permiten conflictos de horario**: Validación en app y BD
- Status válidos: `Pendiente`, `Confirmada`, `En Sala`, `Realizada`, `Cancelada`, `No Asistió`
- Duración calculada desde `catalogo_servicios.duracion_minutos`
- Recordatorios automáticos 24h antes (workflow de notificaciones)

---

#### 4. Tratamientos
**Responsabilidad**: "Carpetas de problemas", cada tratamiento agrupa evoluciones de un problema específico

**Flujo de Inicio**:
```
Seleccionar Paciente → Definir Problema → Establecer Plan → 
Crear Tratamiento → Vincular a Paciente → Auditoría
```

**Endpoints Clave**:
- `POST /api/v1/tratamientos` - Iniciar tratamiento nuevo
- `GET /api/v1/tratamientos` - Listar tratamientos activos/completados
- `PUT /api/v1/tratamientos/{id}` - Actualizar diagnóstico/plan/estado
- `GET /api/v1/tratamientos/{id}` - Detalle con todas sus evoluciones

**Permisos**: 
- Admin, Podologo → CRUD completo
- Recepcion → Solo lectura

**Reglas de Negocio**:
- Un paciente puede tener **múltiples tratamientos simultáneos** (ej: pie derecho + pie izquierdo)
- Estados: `activo`, `completado`, `suspendido`
- Cada tratamiento tiene fecha_inicio y fecha_fin (nullable)
- Soft delete preserva historial

---

#### 5. Evoluciones
**Responsabilidad**: Notas clínicas SOAP por visita, vinculadas a tratamientos

**Flujo de Registro**:
```
Seleccionar Tratamiento → Capturar SOAP (Subjetivo, Objetivo, Análisis, Plan) → 
Adjuntar Evidencias → Firmar Digitalmente → Crear Evolución → Auditoría
```

**Endpoints Clave**:
- `POST /api/v1/evoluciones` - Registrar nota SOAP
- `GET /api/v1/evoluciones` - Listar evoluciones por tratamiento
- `GET /api/v1/evoluciones/{id}` - Detalle con evidencias

**Permisos**: 
- Admin, Podologo → Crear y editar (solo propio podólogo puede editar sus notas)
- Recepcion → No acceso

**Reglas de Negocio**:
- Formato SOAP obligatorio: Subjetivo, Objetivo, Análisis (Assessment), Plan
- Cada evolución se vincula a un `tratamiento_id`
- Soporte para evidencias fotográficas adjuntas
- Cumplimiento NOM-024-SSA3-2013

---

#### 6. Evidencias
**Responsabilidad**: Fotos clínicas, documentos adjuntos a evoluciones o tratamientos

**Flujo de Subida**:
```
Validar Formato (JPEG, PNG) → Validar Tamaño (<5MB) → 
Almacenar en Filesystem/S3 → Registrar Metadata → Vincular a Evolución → Auditoría
```

**Endpoints Clave**:
- `POST /api/v1/evidencias` - Subir foto/documento
- `GET /api/v1/evidencias/{id}` - Descargar evidencia
- `DELETE /api/v1/evidencias/{id}` - Eliminar (soft delete)

**Permisos**: 
- Admin, Podologo → CRUD
- Recepcion → No acceso

**Reglas de Negocio**:
- Formatos permitidos: JPEG, PNG, PDF
- Tamaño máximo: 5MB por archivo
- Almacenamiento: Filesystem local o S3 (configurable)
- Metadata: fecha_captura, tipo_evidencia, descripcion

---

#### 7. Finanzas
**Responsabilidad**: Métodos de pago, transacciones, gastos, reportes financieros

**Flujo de Pago**:
```
Registrar Servicio → Calcular Precio → Seleccionar Método de Pago → 
Crear Transacción → Actualizar Balance → Auditoría
```

**Endpoints Clave**:
- `POST /api/v1/finanzas/transacciones` - Registrar pago
- `POST /api/v1/finanzas/gastos` - Registrar gasto
- `GET /api/v1/finanzas/resumen` - Dashboard financiero

**Permisos**: 
- Admin → Acceso completo
- Podologo, Recepcion → Solo lectura de transacciones propias

---

#### 8. Auditoría
**Responsabilidad**: Registro de todas las operaciones CREATE/UPDATE/DELETE

**Flujo Automático**:
```
Usuario Realiza Acción → Interceptor Captura Request → 
Extrae Datos Relevantes → Inserta en auth.audit_logs → Continúa Request
```

**Endpoints Clave**:
- `GET /api/v1/audit` - Consultar logs (Admin, Podologo)
- `GET /api/v1/audit/usuario/{id}` - Logs de usuario específico

**Permisos**: 
- Admin → Ver todos los logs
- Podologo → Ver logs propios

**Campos Registrados**:
- `user_id`, `action` (CREATE/UPDATE/DELETE), `table_name`, `record_id`, `old_values`, `new_values`, `timestamp`

---

### Patrón de Implementación de Workflows

```python
# backend/workflows/pacientes_workflow.py
from langgraph.graph import StateGraph, END
from backend.api.deps.database import get_core_db
from backend.schemas.core.models import Paciente

def crear_paciente_workflow():
    """
    Workflow para creación de paciente con validación de duplicados.
    """
    workflow = StateGraph()
    
    # Paso 1: Validar entrada Pydantic
    workflow.add_node("validar_entrada", validar_datos_paciente)
    
    # Paso 2: Verificar duplicados (fuzzy search)
    workflow.add_node("verificar_duplicados", buscar_duplicados)
    
    # Paso 3: Crear en BD
    workflow.add_node("crear_bd", insertar_paciente)
    
    # Paso 4: Auditoría
    workflow.add_node("auditar", registrar_auditoria)
    
    # Paso 5: Notificar
    workflow.add_node("notificar", enviar_notificacion)
    
    # Definir flujo
    workflow.add_edge("validar_entrada", "verificar_duplicados")
    workflow.add_conditional_edges(
        "verificar_duplicados",
        lambda state: "crear_bd" if not state["duplicados_encontrados"] else "escalar_humano"
    )
    workflow.add_edge("crear_bd", "auditar")
    workflow.add_edge("auditar", "notificar")
    workflow.add_edge("notificar", END)
    
    return workflow.compile()
```

---

## Agentes con Criterio Controlado

### Qué Son

Agentes conversacionales basados en LLM (Claude 3.5 Haiku) con capacidad de razonamiento pero controlados mediante guardrails, middlewares y puntos de escalamiento humano.

### Características

- **Conversacionales**: Lenguaje natural, contexto multi-turno
- **Controlados**: Guardrails bloquean acciones riesgosas
- **Supervisados**: Escalamiento automático a humanos cuando sea necesario
- **Trazables**: Cada interacción se registra en LangSmith

### Módulos de Agentes

#### 1. Chat IA Clínica

**Propósito**: Asistente conversacional para consultas, búsquedas, y acciones dentro de guardrails

**Personalidad**:
- 🩺 **Profesional y empático**
- 📊 **Claro y conciso en respuestas**
- 🔒 **Conservador en recomendaciones clínicas**

**Capacidades**:
- Búsqueda de pacientes (fuzzy matching)
- Consulta de citas del día/semana
- Estadísticas rápidas (conteos, KPIs)
- Información de servicios y precios
- Ayuda con navegación del sistema

**Restricciones (Guardrails)**:
- ❌ **No puede** crear/modificar datos sin confirmación explícita del usuario
- ❌ **No puede** realizar diagnósticos médicos
- ❌ **No puede** acceder a datos fuera del scope del rol del usuario (RBAC)
- ❌ **No puede** ejecutar queries SQL directos sin validación

**Flujo de Interacción**:
```
Usuario: "¿Cuántas citas tengo hoy?"
  ↓
[Middleware: Validar Prompt] → OK
  ↓
[Guardrails: Verificar Permisos] → OK (Usuario tiene acceso a citas)
  ↓
[Agent: Clasificar Intent] → "query_citas_hoy"
  ↓
[Tool: SQL Executor] → SELECT COUNT(*) FROM ops.citas WHERE ...
  ↓
[Agent: Formatear Respuesta] → "📅 Tienes 5 citas programadas para hoy"
  ↓
[Observability: Log en LangSmith] → Registrado
```

**Ejemplo de Escalamiento**:
```
Usuario: "El paciente Juan Pérez tiene dolor intenso, ¿qué le receto?"
  ↓
[Middleware: Detectar Tema Clínico Sensible]
  ↓
[Guardrails: Bloquear por "diagnostic_clinical"]
  ↓
Response: "⚠️ Esta consulta requiere evaluación clínica directa. 
Por favor revisa el expediente del paciente y realiza el diagnóstico 
de acuerdo a tu criterio profesional."
```

**Implementación**:
- **Backend**: `backend/agents/graph.py` (LangGraph state machine)
- **Endpoint**: `POST /api/v1/chat`
- **Middleware**: `backend/middleware/` (PromptController, Guardrails)

---

#### 2. Asistente de Evoluciones con Revisión Humana

**Propósito**: Ayudar a generar notas SOAP basadas en inputs del podólogo, pero siempre requiere revisión humana antes de persistir

**Flujo**:
```
Podólogo: "El paciente presenta onicomicosis en dedo gordo derecho"
  ↓
[Agent: Estructurar SOAP]
  S: Paciente refiere dolor al caminar
  O: Onicomicosis visible en dedo gordo derecho
  A: Diagnóstico presuntivo de onicomicosis
  P: Tratamiento tópico con antifúngico
  ↓
[Agent: Generar Borrador] → JSON con SOAP estructurado
  ↓
[UI: Mostrar Borrador al Podólogo]
  ↓
[Podólogo: Revisar y Aprobar]
  ↓
[Workflow: Persistir en BD] → Solo si el podólogo aprueba
```

**Características Clave**:
- ✅ **Nunca persiste automáticamente**: Siempre requiere aprobación humana
- ✅ **Sugiere estructura SOAP**: Ayuda a formatear correctamente
- ✅ **Extrae datos relevantes**: De inputs en lenguaje natural
- ✅ **Cumplimiento NOM-024**: Genera notas conformes al estándar

---

### Guardrails Implementados

#### Tipos de Guardrails

1. **Prompt Validation** (`PromptController`)
   - Detecta injection attempts
   - Sanitiza caracteres especiales
   - Limita longitud de prompts
   - Clasifica riesgo: `safe`, `medium`, `high`

2. **Permission Guardrails** (`require_role`)
   - Verifica rol del usuario contra RBAC
   - Bloquea acceso a endpoints según rol
   - Logs de intentos de acceso denegado

3. **Clinical Guardrails** (`Guardrails`)
   - Detecta temas clínicos sensibles (diagnóstico, prescripción)
   - Bloquea acciones que requieren licencia médica
   - Escala a humano cuando detecta riesgo

4. **Data Access Guardrails**
   - Limita resultados de queries (máx 100 filas)
   - Filtra datos según `clinica_id` del usuario
   - Solo queries SELECT (no INSERT/UPDATE/DELETE desde chat)

#### Ejemplo de Configuración de Guardrails

```python
# backend/middleware/guardrails.py
from enum import Enum

class GuardrailReason(Enum):
    SAFE = "safe"
    CLINICAL_ADVICE = "clinical_advice_required"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SENSITIVE_DATA = "sensitive_data_access"
    HARMFUL_CONTENT = "harmful_content"

class Guardrails:
    CLINICAL_KEYWORDS = [
        "diagnosticar", "recetar", "prescribir", "medicar",
        "tratamiento para", "qué tomar", "qué medicamento"
    ]
    
    def check(self, prompt: str, user_role: str, intent: str, context: dict) -> GuardrailDecision:
        # 1. Verificar si es tema clínico sensible
        if any(kw in prompt.lower() for kw in self.CLINICAL_KEYWORDS):
            if user_role not in ["Admin", "Podologo"]:
                return GuardrailDecision(
                    should_block=True,
                    reason=GuardrailReason.CLINICAL_ADVICE,
                    message="Esta consulta requiere evaluación por un profesional de la salud."
                )
        
        # 2. Verificar acceso a datos sensibles
        if intent == "query_historial_clinico" and user_role == "Recepcion":
            return GuardrailDecision(
                should_block=True,
                reason=GuardrailReason.UNAUTHORIZED_ACCESS,
                message="No tienes permiso para acceder al historial clínico."
            )
        
        # 3. Si pasa todas las verificaciones
        return GuardrailDecision(
            should_block=False,
            reason=GuardrailReason.SAFE,
            message="OK"
        )
```

---

## Infraestructura y Calidad

### 1. Middleware Stack

```
HTTP Request
    ↓
[CORS Middleware] → Permite origins configurados
    ↓
[Rate Limiter] → 30 requests/min para /chat
    ↓
[JWT Validator] → Verifica token y extrae user
    ↓
[RBAC Middleware] → Verifica permisos según rol
    ↓
[Prompt Controller] → Valida y sanitiza inputs
    ↓
[Guardrails] → Bloquea acciones riesgosas
    ↓
[Agent/Workflow] → Procesa request
    ↓
[Observability] → Log en LangSmith
    ↓
[Response Formatter] → Retorna JSON
    ↓
HTTP Response
```

### 2. Observabilidad con LangSmith

**Configuración**:
```python
# backend/middleware/observability.py
import os
from langsmith import Client

class ObservabilityMiddleware:
    def __init__(self):
        self.enabled = bool(os.getenv("LANGSMITH_API_KEY"))
        if self.enabled:
            self.client = Client()
    
    def trace_interaction(self, user_id, user_role, user_input, agent_response, 
                         intent, execution_time_ms, metadata):
        """Registra cada interacción del agente en LangSmith."""
        if not self.enabled:
            return None
        
        return self.client.create_run(
            name="chat_interaction",
            inputs={"user_input": user_input, "user_role": user_role},
            outputs={"response": agent_response, "intent": intent},
            run_type="chain",
            extra={
                "user_id": user_id,
                "execution_time_ms": execution_time_ms,
                **metadata
            }
        )
```

**Métricas Rastreadas**:
- Tiempo de ejecución por interacción
- Tasa de éxito/error
- Intents más frecuentes
- Queries SQL generadas
- Escalamientos a humano (frecuencia y razones)
- Uso de tokens (costos de Claude API)

### 3. WebSocket para Streaming

**Uso**: Streaming de respuestas del agente en tiempo real

```python
# backend/api/routes/chat_ws.py
from fastapi import WebSocket

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, token: str):
    await websocket.accept()
    user = validate_jwt(token)
    
    try:
        while True:
            message = await websocket.receive_text()
            
            # Stream response chunk by chunk
            async for chunk in agent_stream(message, user):
                await websocket.send_text(chunk)
    except WebSocketDisconnect:
        logger.info(f"User {user.id_usuario} disconnected")
```

### 4. TTS/Accesibilidad

**Preparación para Text-to-Speech**:
- Respuestas formateadas con pausas lógicas
- Evitar exceso de emojis
- Usar lenguaje natural fluido

---

## Guías de Implementación

### Crear un Nuevo Workflow

1. **Definir el State Schema**:
```python
from typing import TypedDict

class PacienteWorkflowState(TypedDict):
    input_data: dict
    validated: bool
    duplicados_encontrados: list
    paciente_id: int
    error: str | None
```

2. **Crear Nodos del Workflow**:
```python
def validar_datos(state: PacienteWorkflowState) -> PacienteWorkflowState:
    # Lógica de validación Pydantic
    pass

def verificar_duplicados(state: PacienteWorkflowState) -> PacienteWorkflowState:
    # Fuzzy search en BD
    pass
```

3. **Ensamblar el Graph**:
```python
from langgraph.graph import StateGraph

workflow = StateGraph(PacienteWorkflowState)
workflow.add_node("validar", validar_datos)
workflow.add_node("verificar", verificar_duplicados)
workflow.add_edge("validar", "verificar")
# ...
graph = workflow.compile()
```

4. **Invocar desde Endpoint**:
```python
@router.post("/pacientes")
async def create_patient(data: PacienteCreate):
    result = await graph.ainvoke({"input_data": data.dict()})
    return result
```

---

### Crear un Nuevo Agente

1. **Definir el Tool**:
```python
from langchain.tools import tool

@tool
def buscar_paciente(nombre: str) -> dict:
    """Busca pacientes por nombre usando fuzzy matching."""
    # Lógica de búsqueda
    return {"pacientes": [...]}
```

2. **Configurar el Agent**:
```python
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

llm = ChatAnthropic(model="claude-3-5-haiku-20241022")
tools = [buscar_paciente, get_citas_hoy]

agent = create_react_agent(
    llm,
    tools,
    state_modifier="Eres Maya, asistente de la clínica PodoSkin..."
)
```

3. **Agregar Guardrails**:
```python
def agent_con_guardrails(user_input, user_role):
    # Pre-check
    guardrail_check = guardrails.check(user_input, user_role, None, {})
    if guardrail_check.should_block:
        return {"response": guardrail_check.message, "blocked": True}
    
    # Ejecutar agent
    result = agent.invoke({"messages": [user_input]})
    
    # Post-check (si es necesario)
    return result
```

---

## Referencias y Recursos

### Documentación Oficial

- **LangGraph - Workflows y Agentes**: https://python.langchain.com/docs/langgraph
- **LangGraph - Control de Flujo**: https://python.langchain.com/docs/langgraph/how-tos/branching
- **LangChain - Middleware**: https://python.langchain.com/docs/how_to/middleware
- **LangSmith - Observabilidad**: https://docs.smith.langchain.com/

### Patrones de Referencia

- **ReAct Agent Pattern**: https://python.langchain.com/docs/how_to/agent_executor
- **Human-in-the-Loop**: https://python.langchain.com/docs/langgraph/how-tos/human_in_the_loop
- **Conditional Edges**: https://python.langchain.com/docs/langgraph/how-tos/branching

### Ejemplos en el Codebase

- **Workflow Example**: `backend/workflows/` (por implementar)
- **Agent Example**: `backend/agents/graph.py` (implementado)
- **Middleware Example**: `backend/middleware/` (implementado)
- **Guardrails Example**: `backend/middleware/guardrails.py` (implementado)

---

## Roadmap de Implementación

### Fase 1: Workflows Básicos ✅ (COMPLETADO)
- [x] CRUD de Pacientes
- [x] CRUD de Citas
- [x] CRUD de Tratamientos
- [x] Auditoría automática

### Fase 2: Agentes con Guardrails ✅ (COMPLETADO)
- [x] Chat IA básico con NL-to-SQL
- [x] Middleware de seguridad (PromptController, Guardrails)
- [x] Observabilidad con LangSmith
- [x] Rate limiting

### Fase 3: Workflows Avanzados 🚧 (EN PROGRESO)
- [ ] Workflow de Evoluciones con asistente IA
- [ ] Workflow de Notificaciones automáticas
- [ ] Workflow de Reportes financieros
- [ ] Workflow de Exportación NOM-024

### Fase 4: Agentes Especializados 📅 (PLANEADO)
- [ ] Agente de Triaje (clasificar urgencia de consultas)
- [ ] Agente de Seguimiento (recordatorios personalizados)
- [ ] Agente de Análisis (insights de datos clínicos)

### Fase 5: Integración Completa 🔮 (FUTURO)
- [ ] Voice interface (TTS + STT)
- [ ] Multi-modal (análisis de imágenes de evidencias)
- [ ] Predicción de no-shows con ML
- [ ] Dashboard ejecutivo con BI integrado

---

## Conclusión

Esta arquitectura híbrida de **Workflows + Agentes** permite a PodoSkin:

1. ✅ **Mantener control**: Workflows determinísticos para operaciones críticas
2. ✅ **Ofrecer flexibilidad**: Agentes conversacionales para consultas naturales
3. ✅ **Garantizar seguridad**: Guardrails y middleware en múltiples capas
4. ✅ **Cumplir normativa**: NOM-024-SSA3-2013 para expedientes electrónicos
5. ✅ **Escalar eficientemente**: Componentes independientes y observables

---

**Última actualización**: 14 de diciembre de 2025  
**Versión del documento**: 1.0  
**Autor**: PodoSkin Development Team
