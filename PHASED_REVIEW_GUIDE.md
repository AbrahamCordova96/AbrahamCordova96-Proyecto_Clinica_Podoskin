# Guía de Revisión por Fases - Voice Integration Backend

Este documento organiza el PR en fases lógicas para facilitar la revisión estructurada. Cada fase se puede revisar independientemente antes de pasar a la siguiente.

---

## 📋 Estado de Fases

| Fase | Descripción | Estado | Archivos | Tests |
|------|-------------|--------|----------|-------|
| **Fase 1** | Modelos de Base de Datos | ✅ Completado | 2 archivos | - |
| **Fase 2** | Utilidades de Seguridad | ✅ Completado | 1 archivo | 21 tests ✅ |
| **Fase 3** | Middleware de Auditoría | ✅ Completado | 2 archivos | - |
| **Fase 4** | Endpoints de Integración | ✅ Completado | 1 archivo | Pendiente |
| **Fase 5** | WebSocket Streaming | ✅ Completado | 1 archivo | Pendiente |
| **Fase 6** | Catálogos API | ✅ Completado | 2 archivos | - |
| **Fase 7** | Documentación | ✅ Completado | 4 archivos | - |

---

## 🔍 FASE 1: Modelos de Base de Datos

### Objetivo
Establecer la estructura de datos para auditoría mejorada y transcripciones de voz.

### Archivos a Revisar
1. **`backend/schemas/auth/models.py`**
   - Líneas agregadas: ~47
   - Cambios: Enhanced `AuditLog` + Nuevo `VoiceTranscript`

2. **`backend/schemas/auth/schemas.py`**
   - Líneas agregadas: ~42
   - Cambios: Schemas Pydantic para los nuevos modelos

### Cambios Detallados

#### 1.1 Enhanced AuditLog Model
**Ubicación**: `backend/schemas/auth/models.py`

**Campos Nuevos (8)**:
```python
username = Column(String, nullable=True)           # Usuario para referencia rápida
session_id = Column(String, nullable=True)         # Identificador de sesión
method = Column(String, nullable=True)             # HTTP method (GET, POST, etc.)
endpoint = Column(String, nullable=True)           # Ruta del endpoint
request_body = Column(String, nullable=True)       # Request body enmascarado
response_hash = Column(String, nullable=True)      # SHA-256 para no-repudio
source_refs = Column(JSONB, nullable=True)         # Referencias de proveniencia
note = Column(String, nullable=True)               # Notas adicionales
```

**Cambios Estructurales**:
- `registro_id` ahora es nullable (no todas las auditorías tienen un registro específico)
- Se eliminó primary key duplicada en `timestamp_accion`
- Se agregaron índices para queries comunes (session_id, endpoint, username)

**Justificación**:
- Soporta trazabilidad completa de conversaciones de voz
- Permite verificación de respuestas (no-repudiation)
- Facilita auditorías de cumplimiento PII/PHI

#### 1.2 VoiceTranscript Model (Nuevo)
**Ubicación**: `backend/schemas/auth/models.py`

```python
class VoiceTranscript(Base):
    __tablename__ = "voice_transcripts"
    __table_args__ = {"schema": "auth"}

    id_transcript = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("auth.sys_usuarios.id_usuario"))
    user_text = Column(String, nullable=False)
    assistant_text = Column(String, nullable=True)
    timestamp = Column(TIMESTAMP(timezone=True), nullable=False)
    langgraph_job_id = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
```

**Características**:
- Almacena pares usuario/asistente de conversaciones
- Vinculado a sesiones y jobs de LangGraph
- Contiene PII/PHI - requiere política de retención
- Índices en session_id, user_id, timestamp para queries eficientes

#### 1.3 Schemas Pydantic
**Ubicación**: `backend/schemas/auth/schemas.py`

**Nuevos Schemas**:
```python
class AuditLogRead(BaseModel):
    # Campos existentes +
    username: Optional[str]
    session_id: Optional[str]
    method: Optional[str]
    endpoint: Optional[str]
    request_body: Optional[str]
    response_hash: Optional[str]
    source_refs: Optional[list]
    note: Optional[str]

class VoiceTranscriptCreate(BaseModel):
    session_id: str
    user_text: str
    assistant_text: Optional[str]
    timestamp: str  # ISO-8601
    langgraph_job_id: Optional[str]

class VoiceTranscriptRead(BaseModel):
    id_transcript: int
    session_id: str
    user_id: int
    user_text: str
    assistant_text: Optional[str]
    timestamp: datetime
    langgraph_job_id: Optional[str]
    created_at: datetime
```

### Checklist de Revisión - Fase 1

- [ ] **Estructura de Datos**: ¿Los campos nuevos tienen sentido para auditoría de IA?
- [ ] **Tipos de Datos**: ¿Son apropiados los tipos (VARCHAR, JSONB, TIMESTAMPTZ)?
- [ ] **Índices**: ¿Los índices mejoran las queries esperadas?
- [ ] **Seguridad**: ¿VoiceTranscript está marcado como PII/PHI sensible?
- [ ] **Migración**: Revisar `backend/integration/MIGRATION_PLAN.md`
- [ ] **Compatibilidad**: ¿Los cambios son backward-compatible?

### Preguntas para el Revisor
1. ¿Necesitas otros campos en AuditLog para tus casos de uso?
2. ¿La estructura de VoiceTranscript cubre tus necesidades de transcripción?
3. ¿Hay otros índices que consideres necesarios?

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 2: Utilidades de Seguridad**

---

## 🔒 FASE 2: Utilidades de Seguridad

### Objetivo
Implementar funciones de enmascaramiento PII/PHI y hashing de respuestas.

### Archivos a Revisar
1. **`backend/api/utils/security_utils.py`** (NUEVO)
   - Líneas: 233
   - 8 funciones principales

### Funciones Implementadas

#### 2.1 Enmascaramiento de Email
```python
def mask_email(email: str) -> str
```
**Ejemplos**:
- `john.doe@example.com` → `j***e@e***e.com`
- `ab@xy.com` → `a*@x*.com`

**Uso**: Proteger emails en logs de auditoría

#### 2.2 Enmascaramiento de Teléfono
```python
def mask_phone(phone: str) -> str
```
**Ejemplos**:
- `+52 123 456 7890` → `+52 *** *** 7890`
- `1234567890` → `*** *** 7890`

**Uso**: Proteger números telefónicos

#### 2.3 Enmascaramiento de Identificaciones
```python
def mask_identification(id_str: str) -> str
```
**Ejemplos**:
- `123-45-6789` → `***6789`
- `CURP123456` → `***3456`

**Uso**: Proteger SSN, CURP, RFC, etc.

#### 2.4 Enmascaramiento Recursivo de Datos
```python
def mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]
```

**Patrones Detectados**:
- email, correo, mail → `mask_email()`
- telefono, celular, phone, movil → `mask_phone()`
- ssn, curp, rfc, nss → `mask_identification()`
- password, contraseña, pwd, credit_card, tarjeta → `***MASKED***`

**Características**:
- Recursivo (maneja diccionarios anidados)
- Maneja listas de objetos
- Preserva estructura original

**Ejemplo**:
```python
data = {
    "nombre": "Juan Pérez",
    "email": "juan@example.com",
    "telefono": "+52 123 456 7890",
    "password": "secret123",
    "datos_medicos": {
        "curp": "ABCD123456",
        "contacto": {
            "correo": "backup@example.com"
        }
    }
}

masked = mask_sensitive_data(data)
# {
#     "nombre": "Juan Pérez",
#     "email": "j***n@e***e.com",
#     "telefono": "+52 *** *** 7890",
#     "password": "***MASKED***",
#     "datos_medicos": {
#         "curp": "***3456",
#         "contacto": {
#             "correo": "b***p@e***e.com"
#         }
#     }
# }
```

#### 2.5 Hash de Respuesta (No-Repudiation)
```python
def compute_response_hash(data: Any) -> str
```

**Características**:
- SHA-256 hash
- JSON con keys ordenadas (consistencia)
- Retorna hex digest

**Uso**:
```python
response_data = {"id": 123, "nombre": "Juan"}
hash_value = compute_response_hash(response_data)
# "843f8bdd7074f8834a5c0e8b5a6e4b2c..."

# Almacenar en audit_log.response_hash
# Permite verificar que el asistente no fabricó datos
```

#### 2.6 Crear Referencias de Fuente
```python
def create_source_refs(table: str, record_id: int, 
                       fields: Optional[list] = None, 
                       confidence: float = 1.0) -> dict
```

**Ejemplo**:
```python
ref = create_source_refs(
    table="pacientes",
    record_id=123,
    fields=["nombre", "fecha_nacimiento"],
    confidence=1.0
)
# {
#     "table": "pacientes",
#     "id": 123,
#     "excerpt": "nombre, fecha_nacimiento",
#     "confidence": 1.0
# }
```

**Uso**: Rastrear proveniencia de datos en respuestas de IA

#### 2.7 Enmascarar Request Body
```python
def mask_request_body(body: Optional[str]) -> Optional[str]
```

**Funcionalidad**:
- Parsea JSON string
- Aplica `mask_sensitive_data()`
- Retorna JSON enmascarado
- Maneja casos de JSON inválido

### Tests - Fase 2

**Archivo**: `backend/tests/test_security_utils.py`

**Cobertura**: 21 test cases

**Categorías**:
1. Email masking (4 tests)
2. Phone masking (3 tests)
3. ID masking (2 tests)
4. Nested data masking (2 tests)
5. Response hashing (4 tests)
6. Source refs (2 tests)
7. Request body masking (3 tests)
8. Hash order independence (1 test)

**Ejecución**:
```bash
cd backend
python3 tests/test_security_utils.py
```

**Resultado Esperado**: ✅ All basic tests passed!

### Checklist de Revisión - Fase 2

- [ ] **Funcionalidad**: ¿Las funciones de masking cubren tus necesidades?
- [ ] **Patrones**: ¿Hay otros campos sensibles que detectar?
- [ ] **Tests**: ¿Los 21 tests cubren casos de uso reales?
- [ ] **Performance**: ¿El masking recursivo es eficiente?
- [ ] **Seguridad**: ¿El hash SHA-256 es suficiente para no-repudiation?

### Preguntas para el Revisor
1. ¿Hay otros patrones de datos sensibles específicos de tu dominio?
2. ¿Necesitas máscaras diferentes (más o menos restrictivas)?
3. ¿El formato de source_refs cumple tus requerimientos de auditoría?

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 3: Middleware de Auditoría**

---

## 📝 FASE 3: Middleware de Auditoría

### Objetivo
Implementar logging automático de operaciones sensibles con enmascaramiento PII/PHI.

### Archivos a Revisar
1. **`backend/api/middleware/__init__.py`** (NUEVO)
   - Líneas: 1
   
2. **`backend/api/middleware/audit_middleware.py`** (NUEVO)
   - Líneas: 178

### Componente Principal

#### 3.1 AuditMiddleware Class
**Ubicación**: `backend/api/middleware/audit_middleware.py`

**Rutas Sensibles Monitoreadas**:
```python
SENSITIVE_PATHS = [
    "/api/v1/pacientes",
    "/api/v1/tratamientos",
    "/api/v1/evoluciones",
    "/api/v1/citas",
    "/api/v1/usuarios",
    "/api/v1/finance",
]
```

**Métodos Auditados**:
```python
SENSITIVE_METHODS = ["POST", "PUT", "DELETE", "PATCH"]
```

### Flujo de Auditoría

```
1. Request llega → Middleware intercepta
2. ¿Es ruta sensible? → Verificar SENSITIVE_PATHS
3. ¿Es método sensible? → Verificar SENSITIVE_METHODS
4. Leer request body → Cache para auditoría
5. Ejecutar endpoint → call_next(request)
6. ¿Response exitoso (< 400)? → Proceder con audit
7. Extraer contexto:
   - user_id, username (de request.state)
   - session_id (de request.state)
   - client_ip (de request.client)
8. Enmascarar request_body → mask_request_body()
9. Determinar acción → method_to_action_map
10. Crear AuditLog → db.add()
11. Commit → db.commit()
12. Si falla → Log error, NO interrumpir request
```

### Métodos Clave

#### 3.2 _should_audit()
```python
def _should_audit(self, request: Request) -> bool
```

**Lógica**:
- Excluye: `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`
- Incluye: Todas las rutas en `SENSITIVE_PATHS`
- Incluye: Todos los métodos en `SENSITIVE_METHODS` para `/api/v1/*`

#### 3.3 _create_audit_log()
```python
def _create_audit_log(self, request: Request, response: Response, 
                      request_body: str = None)
```

**Información Capturada**:
```python
audit_log = AuditLog(
    usuario_id=user_id,           # De request.state
    username=username,             # De request.state
    session_id=session_id,         # De request.state
    ip_address=client_ip,          # De request.client
    method=request.method,         # GET, POST, etc.
    endpoint=request.url.path,     # /api/v1/pacientes
    accion=action,                 # CREATE, UPDATE, DELETE
    tabla_afectada=table,          # pacientes, citas, etc.
    request_body=masked_body,      # Request enmascarado
    # response_hash y source_refs se agregan por endpoints
)
```

#### 3.4 _determine_action()
```python
def _determine_action(self, method: str, path: str) -> str
```

**Mapeo**:
- GET → READ
- POST → CREATE
- PUT → UPDATE
- PATCH → UPDATE
- DELETE → DELETE

#### 3.5 _extract_table_from_path()
```python
def _extract_table_from_path(self, path: str) -> str
```

**Ejemplos**:
- `/api/v1/pacientes` → `pacientes`
- `/api/v1/citas/123` → `citas`
- `/api/v1/tratamientos/456/evoluciones` → `tratamientos`

### Características Importantes

**1. Non-Blocking**:
```python
try:
    self._create_audit_log(request, response, request_body)
except Exception as e:
    logger.error(f"Failed to create audit log: {e}")
    # NO interrumpe el request
```

**2. Enmascaramiento Automático**:
```python
masked_body = mask_request_body(request_body) if request_body else None
```

**3. Sesión de Base de Datos**:
```python
db_gen = get_auth_db()
db = next(db_gen)
# ... usar db
finally:
    if db:
        db.close()
```

### Integración con app.py

**NOTA**: El middleware NO está actualmente habilitado en `app.py`. Esto es intencional para permitir revisión antes de activar.

**Para activar** (después de aprobación):
```python
# En backend/api/app.py
from backend.api.middleware.audit_middleware import AuditMiddleware

app.add_middleware(AuditMiddleware)
```

### Checklist de Revisión - Fase 3

- [ ] **Rutas Monitoreadas**: ¿Las rutas en SENSITIVE_PATHS son correctas?
- [ ] **Métodos**: ¿Los métodos auditados son apropiados?
- [ ] **Performance**: ¿El overhead del middleware es aceptable?
- [ ] **Confiabilidad**: ¿El non-blocking approach es adecuado?
- [ ] **Seguridad**: ¿El enmascaramiento protege adecuadamente PII/PHI?
- [ ] **Context**: ¿La extracción de user_id/session_id de request.state funciona?

### Preguntas para el Revisor
1. ¿Hay otras rutas que deban ser auditadas?
2. ¿Quieres auditar también los GET (lecturas)?
3. ¿Prefieres que el middleware lance excepción si falla el audit?
4. ¿Cuándo quieres activar el middleware en producción?

### Consideraciones de Activación

**Antes de activar**:
1. Aplicar migración de base de datos
2. Verificar que request.state contiene user_id/username
3. Probar en staging
4. Configurar alertas para fallos de audit
5. Revisar impacto en performance

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 4: Endpoints de Integración**

---

## 🔌 FASE 4: Endpoints de Integración

### Objetivo
Implementar endpoints REST para contexto de usuario y almacenamiento de transcripciones.

### Archivos a Revisar
1. **`backend/api/routes/integration.py`** (NUEVO)
   - Líneas: 244
   - 3 endpoints principales

### Endpoints Implementados

#### 4.1 GET /api/v1/integration/user-context

**Propósito**: Proveer contexto seguro para system prompts de Gemini.

**Parámetros**:
- `user_id` (query, opcional): ID del usuario (default: usuario autenticado)

**Autenticación**: Requiere JWT ******

**Response**:
```json
{
  "is_first_time": false,
  "user_name": "dr_lopez",
  "summary": "La última vez actualizó un tratamiento",
  "last_active": "2025-12-11T01:00:00Z"
}
```

**Lógica**:
1. Obtener usuario (user_id o current_user)
2. Verificar que usuario existe y está activo
3. Determinar si es primera vez: `user.last_login is None`
4. Buscar última actividad en audit_logs
5. Generar summary basado en última acción
6. Retornar contexto

**Caso de Uso**:
```javascript
// Frontend - Al iniciar sesión
const context = await fetch('/api/v1/integration/user-context', {
  headers: { 'Authorization': `****** }
}).then(r => r.json());

if (context.is_first_time) {
  gemini.speak("Bienvenido a PodoSkin. Te mostraré cómo funciona...");
} else {
  gemini.speak(`Hola ${context.user_name}, ${context.summary}`);
}
```

**Summaries Generados**:
```python
action_summaries = {
    "pacientes": {
        "CREATE": "creó un nuevo paciente",
        "UPDATE": "actualizó información de paciente",
        "READ": "consultó expedientes de pacientes"
    },
    "citas": {
        "CREATE": "agendó una nueva cita",
        "UPDATE": "modificó una cita",
        "READ": "revisó la agenda"
    },
    # ... más tablas
}
```

#### 4.2 POST /api/v1/integration/save-transcript

**Propósito**: Guardar transcripciones de conversaciones de voz en batch.

**Autenticación**: Requiere JWT ******

**Request Body**:
```json
{
  "transcripts": [
    {
      "session_id": "session-abc-123",
      "user_text": "Muéstrame la agenda de mañana",
      "assistant_text": "Encontré 3 citas programadas...",
      "timestamp": "2025-12-11T10:30:00Z",
      "langgraph_job_id": "job-xyz-456"
    }
  ]
}
```

**Response**:
```json
{
  "ok": true,
  "saved": 1
}
```

**Lógica**:
1. Iterar sobre transcripts
2. Parsear timestamp ISO-8601
3. Crear VoiceTranscript con user_id automático
4. db.add() para cada transcript
5. db.commit() en batch
6. Retornar count de guardados

**Características**:
- Batch processing (múltiples transcripts en un request)
- user_id automático desde current_user
- Timestamps en UTC (TIMESTAMPTZ)
- Manejo de errores por transcript individual

**Caso de Uso**:
```javascript
// Frontend - Después de cada intercambio de voz
const saveTranscript = async (sessionId, userText, assistantText) => {
  await fetch('/api/v1/integration/save-transcript', {
    method: 'POST',
    headers: {
      'Authorization': `******
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      transcripts: [{
        session_id: sessionId,
        user_text: userText,
        assistant_text: assistantText,
        timestamp: new Date().toISOString()
      }]
    })
  });
};

gemini.on('exchange', (userText, assistantText) => {
  saveTranscript(currentSessionId, userText, assistantText);
});
```

**Compliance**:
- TODO: Verificar consentimiento del usuario antes de guardar
- Transcripciones son PII/PHI
- Requiere política de retención configurada

#### 4.3 GET /api/v1/integration/transcript-history

**Propósito**: Recuperar historial de transcripciones de una sesión.

**Parámetros**:
- `session_id` (query, requerido): ID de la sesión

**Autenticación**: Requiere JWT ******

**Response**:
```json
{
  "session_id": "session-abc-123",
  "transcripts": [
    {
      "user_text": "Muéstrame la agenda",
      "assistant_text": "Encontré 3 citas...",
      "timestamp": "2025-12-11T10:30:00Z",
      "langgraph_job_id": null
    }
  ]
}
```

**Lógica**:
1. Validar session_id
2. Filtrar por session_id AND user_id (seguridad)
3. Ordenar por timestamp ASC
4. Retornar lista

**Seguridad**: Solo retorna transcripts del usuario autenticado

**Caso de Uso**:
```javascript
// Frontend - Recuperar sesión anterior
const history = await fetch(
  `/api/v1/integration/transcript-history?session_id=${sessionId}`,
  { headers: { 'Authorization': `****** } }
).then(r => r.json());

// Mostrar historial en UI
history.transcripts.forEach(t => {
  displayMessage(t.user_text, 'user');
  displayMessage(t.assistant_text, 'assistant');
});
```

### Schemas Pydantic

**Ubicación**: Dentro de `integration.py`

```python
class UserContextResponse(BaseModel):
    is_first_time: bool
    user_name: str
    summary: Optional[str] = None
    last_active: Optional[str] = None

class SaveTranscriptRequest(BaseModel):
    transcripts: List[VoiceTranscriptCreate]

class SaveTranscriptResponse(BaseModel):
    ok: bool
    saved: int
```

### Checklist de Revisión - Fase 4

- [ ] **user-context**: ¿Los summaries son útiles para personalización?
- [ ] **save-transcript**: ¿El batch processing es eficiente?
- [ ] **transcript-history**: ¿La seguridad (filtrar por user_id) es suficiente?
- [ ] **Consentimiento**: ¿Cómo implementaremos el check de consentimiento?
- [ ] **Retención**: ¿Cuál debe ser la política de retención por default?
- [ ] **Performance**: ¿Necesitamos paginación en transcript-history?

### Preguntas para el Revisor
1. ¿Los summaries cubren las acciones principales que tu quieres destacar?
2. ¿Necesitas más información en el contexto de usuario?
3. ¿Qué política de retención prefieres? (90 días, 180 días, custom)
4. ¿Necesitas endpoint para borrar transcripts (GDPR/user request)?

### TODOs Identificados
- [ ] Implementar check de consentimiento en save-transcript
- [ ] Agregar paginación a transcript-history (si >100 transcripts)
- [ ] Crear endpoint DELETE /transcript-history?session_id=X
- [ ] Agregar filtros de fecha en transcript-history

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 5: WebSocket Streaming**

---

## 🔄 FASE 5: WebSocket Streaming

### Objetivo
Implementar comunicación bidireccional en tiempo real para streaming de LangGraph.

### Archivos a Revisar
1. **`backend/api/routes/websocket_langgraph.py`** (NUEVO)
   - Líneas: 326

### Componentes Principales

#### 5.1 ConnectionManager

**Propósito**: Gestionar conexiones WebSocket y suscripciones a jobs.

**Estructuras de Datos**:
```python
active_connections: Dict[str, WebSocket]  # connection_id -> websocket
job_subscriptions: Dict[str, str]         # job_id -> connection_id
```

**Métodos**:
```python
async def connect(connection_id: str, websocket: WebSocket)
def disconnect(connection_id: str)
async def send_message(connection_id: str, message: dict)
async def send_to_job(job_id: str, message: dict)
def subscribe_to_job(job_id: str, connection_id: str)
def unsubscribe_from_job(job_id: str)
```

**Características**:
- Múltiples conexiones por usuario
- Enrutamiento de mensajes por job_id
- Auto-cleanup en desconexión

#### 5.2 WebSocket Endpoint

**Ruta**: `WS /ws/langgraph-stream`

**Autenticación**: 
- Parámetro query: `?token=<jwt>`
- TODO: Implementar validación JWT real

**Conexión**:
```javascript
const ws = new WebSocket(
  `ws://localhost:8000/ws/langgraph-stream?token=${token}`
);
```

### Protocolo de Mensajes

#### Cliente → Servidor

**1. start_job**: Iniciar nuevo job
```json
{
  "action": "start_job",
  "session_id": "session-123",
  "user_id": 1,
  "utterance": "Muéstrame la agenda de mañana",
  "job_metadata": {}
}
```

**2. cancel**: Cancelar job en progreso
```json
{
  "action": "cancel",
  "job_id": "job-uuid-123"
}
```

**3. followup**: Enviar seguimiento a job existente
```json
{
  "action": "followup",
  "job_id": "job-uuid-123",
  "utterance": "¿Y para pasado mañana?"
}
```

**4. resubscribe**: Reconectar a job existente
```json
{
  "action": "resubscribe",
  "job_id": "job-uuid-123"
}
```

#### Servidor → Cliente

**1. connected**: Confirmación de conexión
```json
{
  "type": "connected",
  "connection_id": "conn-uuid-456",
  "message": "WebSocket conectado..."
}
```

**2. job_started**: Job iniciado
```json
{
  "type": "job_started",
  "job_id": "job-uuid-123",
  "message": "Job iniciado",
  "session_id": "session-123"
}
```

**3. update**: Actualización parcial
```json
{
  "type": "update",
  "job_id": "job-uuid-123",
  "content": "Consultando disponibilidad...",
  "chunk_meta": {
    "step": 1,
    "node_id": "fetch_appointments",
    "partial": true
  }
}
```

**4. final**: Resultado final
```json
{
  "type": "final",
  "job_id": "job-uuid-123",
  "content": "Encontré 3 citas para mañana",
  "data": {...},
  "chunk_meta": {
    "step": 3,
    "node_id": "format_response",
    "partial": false
  }
}
```

**5. error**: Error en procesamiento
```json
{
  "type": "error",
  "job_id": "job-uuid-123",
  "message": "Error al consultar base de datos"
}
```

**6. cancelled**: Job cancelado
```json
{
  "type": "cancelled",
  "job_id": "job-uuid-123",
  "message": "Job job-uuid-123 cancelado"
}
```

### Handlers de Mensajes

#### 5.3 handle_start_job()
```python
async def handle_start_job(connection_id: str, data: dict, 
                           websocket: WebSocket) -> str
```

**Flujo**:
1. Generar job_id único (UUID)
2. Suscribir conexión a job
3. Extraer parámetros (session_id, user_id, utterance)
4. Enviar job_started
5. Iniciar task asíncrono para LangGraph
6. Retornar job_id

#### 5.4 handle_cancel_job()
```python
async def handle_cancel_job(job_id: str, websocket: WebSocket)
```

**Flujo**:
1. TODO: Cancelar job en LangGraph
2. Enviar mensaje cancelled
3. Unsuscribir de job

#### 5.5 handle_followup()
```python
async def handle_followup(job_id: str, utterance: str, 
                          websocket: WebSocket)
```

**Flujo**:
1. TODO: Enviar followup a LangGraph
2. Enviar confirmación followup_received

### Simulación de LangGraph

**IMPORTANTE**: La implementación actual usa simulación.

```python
async def simulate_langgraph_streaming(job_id: str, utterance: str)
```

**Simulación**:
1. Update: "Procesando solicitud..." (delay 0.5s)
2. Update: "Consultando base de datos..." (delay 1s)
3. Final: Resultado completo (delay 1s)

**En Producción**: Reemplazar con integración real a LangGraph.

### Caso de Uso Completo

```javascript
// Frontend
const ws = new WebSocket(`ws://localhost:8000/ws/langgraph-stream?token=${token}`);

ws.onopen = () => {
  // Iniciar job
  ws.send(JSON.stringify({
    action: 'start_job',
    session_id: 'session-123',
    user_id: 1,
    utterance: 'Muéstrame la agenda de mañana'
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  switch (msg.type) {
    case 'connected':
      console.log('Connected:', msg.connection_id);
      break;
      
    case 'job_started':
      currentJobId = msg.job_id;
      showSpinner("Procesando...");
      break;
      
    case 'update':
      updateStatus(msg.content);
      gemini.speak(msg.content);  // Leer en voz
      break;
      
    case 'final':
      hideSpinner();
      displayResult(msg.data);
      gemini.speak(msg.content);
      break;
      
    case 'error':
      showError(msg.message);
      break;
  }
};

// Cancelar
const cancelJob = () => {
  ws.send(JSON.stringify({
    action: 'cancel',
    job_id: currentJobId
  }));
};

// Seguimiento
const followUp = (text) => {
  ws.send(JSON.stringify({
    action: 'followup',
    job_id: currentJobId,
    utterance: text
  }));
};
```

### Checklist de Revisión - Fase 5

- [ ] **Protocolo**: ¿Los mensajes cubren todos los casos de uso?
- [ ] **Reconexión**: ¿El mecanismo de resubscribe es suficiente?
- [ ] **Autenticación**: ¿Cómo validamos el JWT en query param?
- [ ] **Escalabilidad**: ¿El ConnectionManager maneja múltiples usuarios?
- [ ] **Error Handling**: ¿Los errores se comunican apropiadamente?
- [ ] **Simulación**: ¿Cuándo integramos el LangGraph real?

### Preguntas para el Revisor
1. ¿El protocolo de mensajes cubre tus casos de uso?
2. ¿Necesitas otros tipos de mensajes (progress percentage, ETA)?
3. ¿Cómo quieres que se maneje la reconexión después de desconexión?
4. ¿Tienes ya un LangGraph endpoint para integrar?

### TODOs Identificados
- [ ] Implementar validación JWT desde query param
- [ ] Integrar LangGraph real (reemplazar simulación)
- [ ] Agregar heartbeat para mantener conexión viva
- [ ] Implementar rate limiting por conexión
- [ ] Agregar métricas (conexiones activas, jobs en progreso)
- [ ] Persistir jobs para recuperación después de restart

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 6: Catálogos API**

---

## 📚 FASE 6: Catálogos API

### Objetivo
Generar catálogos machine-readable de endpoints y funciones para LangGraph y Gemini.

### Archivos a Revisar
1. **`backend/integration/endpoints.json`**
   - Líneas: 918 (82 endpoints catalogados)
   
2. **`backend/integration/function_schema.json`**
   - Líneas: 236 (9 funciones para Gemini)

### 6.1 endpoints.json

**Propósito**: Catálogo completo de endpoints para generación de Tools en LangGraph.

**Estructura**:
```json
{
  "generated_at": "2025-12-11T01:31:27Z",
  "total_endpoints": 82,
  "description": "Machine-readable catalog...",
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/v1/pacientes",
      "function_name": "list_pacientes",
      "file_path": "backend/api/routes/pacientes.py",
      "auth_required": true,
      "roles_allowed": ["Admin", "Podologo", "Recepcion"]
    }
  ]
}
```

**Generación**: Script automático que parsea todos los archivos en `backend/api/routes/`.

**Uso en LangGraph**:
```python
import json
from langchain.tools import Tool

# Cargar catálogo
with open('backend/integration/endpoints.json') as f:
    catalog = json.load(f)

# Crear tools
tools = []
for endpoint in catalog['endpoints']:
    if endpoint['method'] == 'GET' and 'pacientes' in endpoint['path']:
        tools.append(Tool(
            name=endpoint['function_name'],
            description=f"{endpoint['method']} {endpoint['path']}",
            func=lambda: call_api(endpoint)
        ))
```

**Endpoints Catalogados por Módulo**:
- Auditoría: 2 endpoints
- Auth: 3 endpoints
- Chat: 2 endpoints
- Citas: 5 endpoints
- Evidencias: 4 endpoints
- Evoluciones: 4 endpoints
- Finance: 8 endpoints
- Historial: 8 endpoints
- Integration: 3 endpoints (nuevos)
- Notifications: 2 endpoints
- Pacientes: 5 endpoints
- Podólogos: 5 endpoints
- Prospectos: 5 endpoints
- Servicios: 5 endpoints
- Statistics: 6 endpoints
- Tratamientos: 5 endpoints
- Usuarios: 8 endpoints

**Total**: 82 endpoints

### 6.2 function_schema.json

**Propósito**: Definiciones de funciones para Gemini function calling.

**Estructura**:
```json
{
  "generated_at": "2025-12-11T01:31:27Z",
  "description": "Function schemas for Gemini...",
  "functions": [
    {
      "name": "get_patient_by_id",
      "description": "Obtiene el detalle de un paciente por ID",
      "parameters": {
        "type": "object",
        "properties": {
          "paciente_id": {
            "type": "integer",
            "description": "ID del paciente"
          }
        },
        "required": ["paciente_id"]
      },
      "auth_required": true,
      "roles_allowed": ["Admin", "Podologo"]
    }
  ],
  "usage_notes": {
    "authentication": "Todas las funciones marcadas con auth_required=true requieren JWT",
    "source_refs": "Todas las respuestas DEBEN incluir source_refs",
    "response_hash": "Las respuestas sensibles deben incluir response_hash",
    "error_handling": "Si no hay datos, decir 'No tengo registro'",
    "confirmations": "Acciones DELETE requieren confirmación"
  }
}
```

**Funciones Definidas**:
1. `get_patient_by_id` - Obtener paciente por ID
2. `list_patients` - Listar pacientes con filtros
3. `get_appointments` - Obtener citas por fecha/podólogo
4. `create_appointment` - Crear nueva cita
5. `get_tratamientos` - Obtener tratamientos de paciente
6. `get_evoluciones` - Obtener notas clínicas
7. `get_statistics` - Obtener métricas del consultorio
8. `get_audit_logs` - Obtener logs de auditoría
9. `open_file_picker` - Abrir selector de archivos (frontend-only)

**Uso en Gemini**:
```python
import json
import google.generativeai as genai

# Cargar schemas
with open('backend/integration/function_schema.json') as f:
    schemas = json.load(f)

# Configurar Gemini
model = genai.GenerativeModel(
    model_name='gemini-pro',
    tools=schemas['functions']
)

# Gemini puede ahora llamar funciones
response = model.generate_content(
    "Muéstrame el paciente 123",
    tool_config={'function_calling_config': 'AUTO'}
)
```

### Checklist de Revisión - Fase 6

- [ ] **endpoints.json**: ¿Todos los endpoints relevantes están catalogados?
- [ ] **Precisión**: ¿Los auth_required y roles_allowed son correctos?
- [ ] **function_schema.json**: ¿Las 9 funciones cubren casos de uso principales?
- [ ] **Parámetros**: ¿Las definiciones de parámetros son completas?
- [ ] **Descripciones**: ¿Las descripciones son claras para el LLM?
- [ ] **Actualización**: ¿Cómo mantenemos estos archivos sincronizados?

### Preguntas para el Revisor
1. ¿Hay endpoints que faltan en el catálogo?
2. ¿Necesitas más funciones específicas para Gemini?
3. ¿Las descripciones en español+inglés son adecuadas?
4. ¿Prefieres generar estos archivos automáticamente en CI?

### Mantenimiento

**Regenerar endpoints.json**:
```bash
cd backend
python3 << 'PYEOF'
# Script de generación aquí
PYEOF
```

**Actualizar function_schema.json**: Editar manualmente según casos de uso.

### TODOs Identificados
- [ ] Automatizar generación en CI/CD
- [ ] Agregar versioning a los catálogos
- [ ] Crear validación contra OpenAPI spec
- [ ] Agregar más ejemplos de uso en comments

### Siguiente Fase
Una vez aprobada esta fase, continuar con **Fase 7: Documentación**

---

## 📖 FASE 7: Documentación

### Objetivo
Proveer documentación completa para implementación, migración y uso.

### Archivos a Revisar
1. **`backend/integration/README.md`** (372 líneas)
2. **`backend/integration/MIGRATION_PLAN.md`** (420 líneas)
3. **`IMPLEMENTATION_SUMMARY.md`** (500+ líneas)
4. **`QUICK_START.md`** (450+ líneas)

### 7.1 Integration README

**Ubicación**: `backend/integration/README.md`

**Contenido**:
- Purpose y key endpoints
- Security features (masking, hashing, source refs)
- Audit middleware configuration
- Database models
- Usage examples (Python, JavaScript)
- Development notes
- Deployment checklist

**Secciones Principales**:
1. Overview con lista de archivos
2. Key Endpoints (user-context, save-transcript, WebSocket)
3. Security Features con ejemplos de código
4. Audit Middleware con configuración
5. Database Models con SQL
6. Usage Examples con código completo
7. Development Notes (migration, testing, compliance)
8. Deployment Checklist
9. References

**Ideal Para**: Desarrolladores que integran con los endpoints.

### 7.2 Migration Plan

**Ubicación**: `backend/integration/MIGRATION_PLAN.md`

**Contenido**:
- Pre-migration checklist (backup, staging, approval)
- SQL scripts para forward migration
- SQL scripts para rollback
- Validation queries
- Impact assessment
- Troubleshooting guide

**Secciones Principales**:
1. Overview y checklist crítico
2. Database changes detallados (AuditLog + VoiceTranscript)
3. Forward migration SQL completo
4. Rollback migration SQL completo
5. Validation queries
6. Impact assessment (storage, performance, compatibility)
7. Security considerations
8. Post-migration tasks
9. Troubleshooting

**Ideal Para**: DBAs y DevOps que aplicarán la migración.

### 7.3 Implementation Summary

**Ubicación**: `IMPLEMENTATION_SUMMARY.md`

**Contenido**:
- Overview de toda la implementación
- File summary con líneas y descripción
- Compliance con prompt original
- Security features review
- Testing status
- Next steps

**Secciones Principales**:
1. Overview y deliverables
2. What Was Implemented (por componente)
3. File Summary (tabla completa)
4. Compliance Score (95%)
5. Security Features Implemented
6. What Needs to Be Done Next
7. Deployment Instructions
8. Success Criteria

**Ideal Para**: Project managers y revisores técnicos senior.

### 7.4 Quick Start Guide

**Ubicación**: `QUICK_START.md`

**Contenido**:
- Quick overview
- Prerequisites
- Authentication setup
- Using each endpoint con ejemplos curl y JavaScript
- Security features usage
- Testing instructions
- Troubleshooting

**Secciones Principales**:
1. Quick Overview
2. Prerequisites
3. Authentication (obtener JWT)
4. Using Integration Endpoints (3 ejemplos completos)
5. WebSocket Streaming (ejemplo completo)
6. Security Features (ejemplos de uso)
7. Using API Catalogs
8. Testing
9. Troubleshooting
10. Next Steps

**Ideal Para**: Desarrolladores nuevos que quieren empezar rápido.

### Checklist de Revisión - Fase 7

- [ ] **README**: ¿Cubre todos los casos de uso de integración?
- [ ] **MIGRATION_PLAN**: ¿Los scripts SQL son seguros?
- [ ] **IMPLEMENTATION_SUMMARY**: ¿El overview es preciso?
- [ ] **QUICK_START**: ¿Los ejemplos funcionan out-of-the-box?
- [ ] **Claridad**: ¿La documentación es clara para tu equipo?
- [ ] **Completitud**: ¿Falta algún aspecto importante?

### Preguntas para el Revisor
1. ¿Qué sección de documentación necesita más detalle?
2. ¿Hay casos de uso que no están cubiertos?
3. ¿Los ejemplos de código son claros y completos?
4. ¿Necesitas documentación en otro formato (wiki, video)?

### TODOs Identificados
- [ ] Agregar diagramas de arquitectura
- [ ] Crear video walkthrough
- [ ] Traducir documentación clave a inglés
- [ ] Agregar FAQs basadas en feedback

---

## ✅ Checklist Final de Revisión

### Por Fase

- [ ] **Fase 1**: Modelos de base de datos aprobados
- [ ] **Fase 2**: Utilidades de seguridad revisadas y tests pasando
- [ ] **Fase 3**: Middleware de auditoría aprobado (decidir cuándo activar)
- [ ] **Fase 4**: Endpoints de integración probados
- [ ] **Fase 5**: WebSocket streaming funcional (con simulación o LangGraph real)
- [ ] **Fase 6**: Catálogos API validados
- [ ] **Fase 7**: Documentación revisada y completa

### Pre-Merge

- [ ] Todas las fases revisadas y aprobadas
- [ ] Tests ejecutados y pasando (21/21 unit tests)
- [ ] Migración de BD planificada y aprobada
- [ ] Backup de producción completado
- [ ] Staging deployment exitoso
- [ ] Security review completado
- [ ] Compliance checklist completado
- [ ] Aprobación final de @SalvadorCordova96

### Post-Merge

- [ ] Aplicar migración a producción
- [ ] Activar middleware de auditoría (si decidido)
- [ ] Integrar LangGraph real (reemplazar simulación)
- [ ] Configurar Gemini con function schemas
- [ ] Implementar política de retención
- [ ] Configurar alertas y monitoring
- [ ] User acceptance testing

---

## 📝 Notas de Revisión

### Para el Revisor

1. **No es necesario revisar todo a la vez**. Puedes aprobar fase por fase.
2. **Comenta directamente en este documento** marcando [ ] → [x] cuando apruebes.
3. **Haz preguntas** en las secciones específicas que necesiten clarificación.
4. **Sugiere cambios** directamente en el código si es más fácil.

### Proceso Sugerido

1. Revisar Fase 1 (modelos)
2. Si aprobada, revisar Fase 2 (security)
3. Ejecutar tests de Fase 2
4. Si aprobados, revisar Fase 3 (middleware)
5. Decidir: ¿activar middleware ahora o después?
6. Revisar Fase 4 (endpoints)
7. Probar endpoints en Postman/curl
8. Revisar Fase 5 (WebSocket)
9. Probar WebSocket con cliente de prueba
10. Revisar Fases 6 y 7 (catálogos + docs)
11. Aprobar merge completo

---

## 🚀 Próximos Pasos Después de Aprobación

1. **Merge a main**
2. **Aplicar migración** (ver MIGRATION_PLAN.md)
3. **Deploy a staging**
4. **Validar integración completa**
5. **Deploy a producción**
6. **Monitor y ajustar**

---

**Documento creado**: 2025-12-11  
**Última actualización**: 2025-12-11  
**Versión**: 1.0  
**Autor**: @copilot
