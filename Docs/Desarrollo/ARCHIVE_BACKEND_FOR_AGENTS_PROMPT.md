# Prompt maestro para Agentes — Integración Backend segura para Frontend por voz (Gemini Live + LangGraph)

Propósito:
Este documento es un "prompt operativo" y una especificación técnica destinada a agentes automatizados (Copilot Agents, LangGraph agents, integraciones CI/CD) que deberán implementar o verificar las integraciones del backend necesarias para soportar una interfaz frontend controlada por voz (Gemini Live) y la orquestación (LangGraph). Contiene requisitos técnicos, contratos de API, reglas de auditoría y narraciones de uso en lenguaje natural (incluye traducciones en inglés entre paréntesis para términos técnicos).

INSTRUCCIÓN PRINCIPAL PARA EL AGENTE:
Actúa como un "ingeniero backend senior" responsable de:
1. Implementar nuevos endpoints y middleware descritos más abajo con máxima cautela.
2. No cambiar la estructura física (schema) de la base de datos en producción sin:
   - Crear migración (Alembic/DB migration) y
   - Tomar backup completo y validar restauración en staging.
3. Registrar todos los cambios en un PR con pruebas (unit + integration + contract tests) y documentación.
4. Marcar en el PR cualquier riesgo para compliance (PII/PHI) y pedir aprobación humana si aplica.
5. Cuando ejecutes acciones automáticas (push/PR), asegúrate de que el commit incluya tests y OpenAPI/contract updates.

---
Sección 1 — Resumen de Endpoints nuevos e imprescindibles (Contractos API)
Objetivo: añadir endpoints e integración que permitirán a LangGraph y Gemini operar sin que el LLM "invente" datos. Todos los endpoints deben incluir OpenAPI (FastAPI auto-generado) y esquemas Pydantic (JSON Schema).

1.1 GET /integration/user-context
- Propósito (purpose): devolver un resumen seguro (context card) sobre el usuario para inyectar en system_prompt (system prompt). No usar LLM para resumir en tiempo real; producir resumen derivado de registros (audit logs / sessions).
- Request:
  - Query: user_id (int, optional). Si no proveído usar token auth user.
- Response (200):
  - {
      "is_first_time": bool,
      "user_name": str,
      "summary": str | null,
      "last_active": str | null
    }
- Seguridad: requiere JWT (Bearer) (authentication).
- Narración de uso (UX): Cuando un profesional inicia sesión, el frontend llama a este endpoint; si is_first_time = true, el asistente (Gemini) reproducirá una bienvenida guiada, si false dará un saludo corto y mencionará el último tema trabajado. En la pestaña "Mi Perfil" o en el inicio del "Dashboard", el usuario verá un banner "Bienvenido de nuevo" o el tutorial inicial.

1.2 POST /integration/save-transcript
- Propósito: persistir pares (user_text, assistant_text) en batch desde el "sidecar" del frontend para historial, cumplimiento y posterior vectorización/summary (no para que LLM invente).
- Request Body: list<{
    "session_id": str,
    "user_text": str,
    "assistant_text": str | null,
    "timestamp": ISO-8601 str,
    "langgraph_job_id": str | null
  }>
- Response: { "ok": true, "saved": int }
- Restricciones: Guardar transcripciones solo si se cumplen flags de consentimiento del usuario (consentimiento previo). Transcripciones son PII/PHI — almacenar en tabla separada con retención configurable.
- Narración de uso (UX): El "taquígrafo" en frontend envía cada turno al backend tras cada intercambio. Esto permite auditar conversaciones y recuperar el historial para reanudar sesiones. En la pestaña "Asistente" el profesional podrá ver la transcripción sincronizada con la conversación de voz.

1.3 WebSocket /ws/langgraph-stream (skeleton)
- Propósito: canal bidireccional (WebSocket (WebSocket)) entre frontend y una capa proxy del backend que reenvíe eventos de streaming de LangGraph (streaming updates).
- Semántica:
  - Cliente -> servidor: "start_job" con { session_id, user_id, utterance, job_metadata }.
  - Servidor -> cliente: streaming messages { type: "update"|"final"|"error", content: str, chunk_meta: {...} }.
  - Cliente puede enviar "cancel" o "followup".
- Seguridad: autenticación por JWT + validate session_id.
- Resiliencia: incluir re-subscribe y job_id (persistente) para reconexión.
- Narración de uso (UX): Cuando el usuario pide "Muéstrame la agenda de mañana", el frontend abrirá WS con LangGraph, mostrará mensaje inmediato "Permítame un momento..." (bridge text), y recibirá updates parciales (por ejemplo: "Consultando disponibilidad..."). Estos updates se muestran en la pestaña "Agenda" y se leen en voz por Gemini mientras se prepara la lista final.

1.4 Endpoints para herramientas (Tools) que LangGraph usará como fuentes de verdad
- Requerimiento: exponer o confirmar que existen los endpoints CRUD ya implementados (ya revisados): pacientes, citas, tratamientos, evoluciones, evidencias, servicios, prospectos, usuarios, audit, finance, examples, statistics, notifications.
- El agente debe generar un "endpoints.json" machine-readable conteniendo:
  - method, path, function_name, file_path_in_repo, auth_required (bool), roles_allowed (list), query_params, body_schema_ref (Pydantic model reference)
- Narración de uso (UX): Este archivo endpoints.json será la "lista de herramientas" que LangGraph importará como Tools; el frontend lo usará para mapear botones/acciones con llamadas seguras; por ejemplo, el botón "Crear cita" en la pestaña "Agenda" disparará la función que LangGraph usará como herramienta para crear la cita.

---
Sección 2 — Auditoría, integridad y trazabilidad (contractos de datos)
Objetivo: garantizar que cada respuesta clínica tenga trazabilidad (provenance), sea reproducible y auditable.

2.1 Tabla audit_logs (AuditLog) (Modelo SQLAlchemy)
- Campos mínimos:
  - id (PK), timestamp, user_id (nullable), username, session_id, ip, method, endpoint, action, params (JSON), request_body (Text or JSON masked), response_hash (SHA-256), source_refs (JSON), note, created_at.
- Regla: NUNCA almacenar datos clínicos sensibles sin masking en request_body (por ejemplo: maskear números de identificación, tarjetas, datos de contacto completos).
- Ejemplo de source_refs:
  - [
      { "table": "pacientes", "id": 123, "excerpt": "nombre, fecha_nacimiento", "confidence": 1.0 }
    ]
- Narración de uso (UX): Cada vez que un asistente pregunta "¿Cuál es la última nota de Javier?", la respuesta en pantalla tendrá enlace "Ver fuente" que direcciona al registro original; además el registro del request queda en Auditoría para trazabilidad. En la pestaña "Auditoría", un admin podrá buscar acciones por usuario/session_id.

2.2 Middleware de auditoría (Audit Middleware)
- Requerimiento: registrar requests sensibles (modificaciones y lecturas clínicas críticas) automáticamente.
- Reglas:
  - Omitir almacenamiento completo del request body; en su lugar almacenar masked_body y response_hash.
  - Para los endpoints de solo lectura críticos (p. ej. GET paciente), registrar source_refs: los IDs consultados.
  - No interrumpir la request si la escritura de auditoría falla; registrar error en logs de infra.
- Narración de uso (UX): Si un usuario cancela una cita, el evento queda registrado con la razón y huella (response_hash), lo que permite a auditoría comprobar qué datos devolvió el sistema en ese momento.

2.3 Response Hash y Non-repudiation
- Por cada payload sensible devuelto a un assistant/tool, computear SHA-256 -> response_hash.
- Guardar en audit_logs junto con source_refs.
- Propósito: permitir verificar que el assistant no fabricó datos después del hecho.
- Narración de uso (UX): En procesos legales/regulatorios se puede pedir el "snapshot" del dato; con el response_hash y source_refs se puede reconstruir y validar la respuesta.

---
Sección 3 — Reglas de uso del LLM / Safe-LLM Policy
Objetivo: limitar la autoridad del LLM para evitar "hallucinations" (invenciones).

3.1 Principio: Single Source of Truth
- Cualquier dato clínico presentado POR EL ASSISTANT (LLM) debe estar etiquetado con source_refs y response_hash devuelto por una llamada real al backend.
- Si el agente no tiene un source para una afirmación clínica, debe responder: "No tengo registro en el sistema para esa consulta; ¿quieres que lo busque o lo cree?" (NO inventar).
- Narración de uso (UX): Si el profesional pregunta por una medicación que no está en el sistema, el asistente dirá "No tengo registro; ¿Deseas agregarla al historial?" en lugar de suponer dosis o diagnósticos.

3.2 Tool-only data retrieval
- El LLM solo está autorizado a razonar y pedir llamadas a Tools (endpoints) para obtener datos. No debe acceder arbitrariamente a bases de datos ni generar respuestas no respaldadas.
- Cada Tool debe devolver objects con shape { data, source_refs }.
- Narración de uso (UX): Al pedir "mostrar indicadores de podólogo", el asistente llamará a Tool estadístico y mostrará cards con números; cada card tiene "Fuente: DB report X".

3.3 Confirmación y acciones destructivas
- Acciones destructivas (DELETE/purge) requieren:
  - Confirmación interactiva (modal + por voz).
  - Registro en audit_logs antes de la ejecución (pre-audit).
  - Si aplica, 2FA o rol ROLE_ADMIN.
- Narración de uso (UX): Si un usuario pide "Eliminar paciente 123", el asistente responderá "Requiere confirmación. ¿Confirmas eliminar permanentemente? (Esto requiere privilegios de Admin)", mostrando diálogo con pista de auditoría.

---
Sección 4 — Workflows asíncronos y streaming (LangGraph + WebSocket)
Objetivo: ejecutar tareas que pueden tardar y mostrar progresos verbales y visuales para la UX por voz.

4.1 Streaming de LangGraph (stream_subgraphs)
- LangGraph tasks deben emitir updates parciales (streaming updates). Los chunks deben ser enviados al WS /ws/langgraph-stream con metadatos chunk_meta { step, node_id, partial=true/false }.
- El FE reproducirá bridge messages ("Permítame un momento...") mientras espera la respuesta final.
- Narración de uso (UX): Al solicitar un informe compuesto (ej. estadísticas y PDF), el asistente verbaliza cada paso: "Buscando registros", "Generando PDF", "Listo para descargar".

4.2 Job IDs y reconexión
- Cada job produciendo stream debe llevar job_id persistente (UUID). Si el WS se cae, el cliente puede reconectar y subscribirse al job_id para continuar recibiendo updates (idempotency).
- Narración de uso (UX): Si el profesional se desconecta durante una búsqueda larga y regresa, el sistema reconstruye el estado y resume: "La búsqueda continuó; estos son los resultados".

4.3 Sidecar de Transcripción
- El frontend guarda localmente los turnos y los envía por lotes a /integration/save-transcript en background.
- El backend procesa (vectoriza/resumes) en background y actualiza user-context.
- Narración de uso (UX): Las notas automáticas generadas durante la consulta aparecen como borrador en la ficha del paciente y el profesional las valida o edita manualmente.

---
Sección 5 — Seguridad, privacidad y compliance (PII/PHI)
Objetivo: cumplir normativa clínica (auditoría, protección de datos).

5.1 Autenticación y autorización
- JWT Bearer (OAuth2 or custom token) en todos endpoints no-publicos.
- Roles: ROLE_ADMIN, CLINICAL_ROLES (Admin+Podologos), RECEPCION, ALL_ROLES used as needed.
- Principle: Least privilege.
- Narración de uso (UX): En el frontend, botones y pestañas son visibles u ocultos según rol; por ejemplo, "Purgar paciente" solo aparece para Admin y requiere confirmación adicional.

5.2 Consentimiento y retención de transcripciones
- Transcripciones solo persistir con consentimiento explícito (consent flag in user profile).
- Retention policy configurable: e.g., 90 días por default, opción de extend para auditoría.
- Narración de uso (UX): Al habilitar grabación, el usuario ve aviso de consentimiento y dónde se guardará la transcripción; puede desactivar y borrar historial.

5.3 Data Loss Prevention (DLP) y Masking
- Implementar masking function antes de escribir request_body o transcripts en logs. Ejemplo: mask emails, phones, ssn.
- Narración de uso (UX): Los auditores ven registros con datos relevantes, pero los campos sensibles están parcialmente enmascarados.

---
Sección 6 — Integridad del esquema (DB schema safety) y migraciones
Objetivo: proteger estructura y relaciones de la BD clínica.

6.1 Reglas para cambios en schema
- Nunca modificar columnas claves (PKs, FKs), tipos o constraints en producción sin:
  1) Migración con Alembic (o herramienta de migración usada).
  2) Backup completo y restore test en staging.
  3) PR con plan de rollback y pruebas de integridad.
- Narración de uso (UX): A nivel de app, esto significa que una nueva versión no cambiará cómo se muestran los expedientes durante consulta clínica, evitando rupturas en el flujo de trabajo del profesional.

6.2 Read replicas y consultas analíticas
- Consultas pesadas de dashboard/statistics deben usar read-replica para no afectar OLTP.
- Narración de uso (UX): El dashboard responde rápido y no penaliza las consultas de agenda que usan la DB principal; el doctor ve métricas en tiempo real sin degradación.

6.3 Contract tests y OpenAPI
- Generar contract tests (pact/contract) y mantener OpenAPI actualizado en repo.
- Narración de uso (UX): El frontend confía en OpenAPI y genera forms/validators automáticamente; reduce errores en tiempo de uso.

---
Sección 7 — Function schemas (para Gemini function-calling) y Tools (para LangGraph)
Objetivo: describir cómo convertir endpoints en "functions" y Tools seguras.

7.1 Reglas para function schema
- Cada function tiene:
  - name: camelCase or snake_case.
  - description (ES) + english term in parentheses.
  - parameters: JSON Schema (types, required).
  - auth_required: bool
  - roles_allowed: list
  - response_mapping: path to fields to render in UI (e.g., response.total, response.items).
  - example_call: small JSON example.
- Narración de uso (UX): Gemini usará estas functions para pedir al frontend que abra modales, rellene formularios o ejecute acciones; ej.: function openFilePicker triggers frontend file dialog (no se sube archivo por voice).

7.2 Tools para LangGraph
- Cada Tool referencia a un endpoint y debe devolver { data, source_refs }.
- Tools deben validar responses y añadir campos de metadata: response_hash y provenance.
- Narración de uso (UX): Al pedir "¿Cuántas citas tiene el Dr. X hoy?", LangGraph invoca tool_get_citas_y_fecha, el Tool responde con data + source_refs, y el assistant presenta la lista con botón "Ver detalles".

---
Sección 8 — Tests y QA (imperativos)
Objetivo: asegurar que la integración sea robusta y segura.

8.1 Unit tests
- Cobertura para audit middleware, integration endpoints, masking functions y compute_response_hash.
- Narración de uso (UX): Menor probabilidad de fallos durante consultas críticas de un paciente en atención.

8.2 Integration tests
- Tests E2E para:
  - Crear/editar/leer paciente -> verify audit log entry.
  - Invocar LangGraph job a través del WS -> verify streaming chunks correctos.
- Narración de uso (UX): El flujo desde voz -> backend -> respuesta final está probado, garantizando que el profesional reciba información verificada.

8.3 Contract tests (OpenAPI / Pact)
- Validar que endpoints.json y function_schema.json coincidan con implementación.
- Narración de uso (UX): Los agentes y la plataforma Gemini / LangGraph usan esos contratos para generar llamadas correctas y evitar errores en producción.

---
Sección 9 — Checklist operativo para el Agent (tareas concretas)
Objetivo: instrucciones ejecutables por Copilot Agent.

9.1 Paso a paso (orden recomendado)
A. Crear en repo (NO en producción todavía):
   1. Archivo endpoints.json (full machine-readable) en /Docs or /integration (generate from routes).
   2. Implementar modelos AuditLog y tabla transcripts (migrations).
   3. Añadir middleware de auditoría (configurable via settings).
   4. Añadir endpoints /integration/user-context y /integration/save-transcript (incl. OpenAPI/Pydantic).
   5. Crear WebSocket skeleton /ws/langgraph-stream con job_id lifecycle.
   6. Add unit + integration tests.
B. Crear PRs separados por área:
   - PR1: audit model + middleware + tests.
   - PR2: integration endpoints + tests.
   - PR3: ws proxy skeleton + example client snippet.
   - PR4: endpoints.json + function_schema.json (draft).
C. En cada PR documentar:
   - Migration plan (if DB schema change).
   - Backups required.
   - Risk assessment for PII/PHI.
D. Notificar al equipo (via PR description) que se requiere revisión humana para aplicar migrations a producción.

9.2 Reglas de commit/PR
- Cada PR debe incluir:
  - Tests passing.
  - OpenAPI update.
  - Migration script (if applies).
  - Checklist en el PR template (backup done, owner approved, compliance OK).

9.3 Tareas adicionales opcionales
- Implementar background worker (Celery/RQ) para process transcripts -> vectorize.
- Add admin UI to manage retention and consents.

---
Sección 10 — Metadatos para indexación (Agents)
Este archivo debe estar indexado para agentes (Copilot Agents / "Agents" in GitHub) con las etiquetas:
- tags: ["backend", "integration", "langgraph", "gemini", "auditing", "security", "medical", "PHI", "voice", "agents"]
- entry_point: "ARCHIVE_BACKEND_FOR_AGENTS_PROMPT.md"
- priority: high
- owner: @SalvadorCordova96 (indica que la aprobación humana por Salvador/owner es necesaria antes de merges a main)

Narración de uso (UX final):
- Con todas las piezas en su lugar, el frontend controlado por voz será capaz de:
  - Inyectar contexto seguro al iniciar sesión,
  - Llamar a acciones (listados, crear, editar) mediante asistentes de voz con confianza (cada respuesta tendrá fuente),
  - Mostrar progreso de tareas largas con mensajes verbales y visuales,
  - Mantener trazabilidad completa para auditoría y cumplimiento.
Esto mejora la experiencia del profesional: menos clics, navegación rápida por voz, y seguridad de que la información mostrada es precisa y verificable.

---
Sección 11 — Ejemplos prácticos (payloads y utterances)
Incluyo 3 ejemplos en JSON para que los agents puedan usar como plantilla.

11.1 Example: endpoints.json entry (ejemplo partial)
```json
{
  "method": "GET",
  "path": "/api/v1/pacientes",
  "function_name": "list_pacientes",
  "file": "backend/api/routes/pacientes.py",
  "auth_required": true,
  "roles_allowed": ["Admin","Podologo","Recepcion"],
  "query_params": ["skip","limit"],
  "body_schema": null
}
```

Narración de uso: Esta entrada permitirá construir la Tool list para LangGraph y la function schema para Gemini, de forma que una petición de voz "Muéstrame pacientes" resuelva en la UI la tabla con paginación.

11.2 Example: function schema (simplified)
```json
{
  "name": "get_patient_by_id",
  "description": "Obtiene el detalle de un paciente por ID (Get patient by ID)",
  "parameters": {
    "type": "object",
    "properties": {
      "paciente_id": { "type": "integer" },
      "include_history": { "type": "boolean" }
    },
    "required": ["paciente_id"]
  },
  "auth_required": true,
  "roles_allowed": ["Admin","Podologo"]
}
```

Narración de uso: Gemini llamará a esta función cuando el usuario diga "abre expediente del paciente 123", la UI abrirá la ficha y mostrará secciones como "Evoluciones" y "Evidencias".

---
Sección 12 — Notas finales y restricciones (compliance)
- No dejar que un agente (Copilot) aplique migraciones sin aprobación humana.
- Cualquier dato sensible debe pasar por masking y control de retención.
- Mantener logs y pruebas para demostrar cumplimiento.

---
FIN del Prompt maestro (usa este archivo como entrada al agente Copilot/Agents)
Instrucciones para acción inmediata:
- Si estás listo para que haga la generación de endpoints.json y los primeros PRs con audit model + middleware + integration endpoints, responde: "Generar endpoints.json y PRs iniciales" y ejecutaré las tareas en el repo (creando PRs y archivos).
- Si prefieres solo el archivo indexado en la raíz para que un Agent lo consuma, indícalo y procederé a crear el archivo en la raíz del repo para su indexación.
