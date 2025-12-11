# Integration for Voice-Controlled Frontend (Gemini Live + LangGraph)

This directory contains the implementation of backend integrations to support a voice-controlled frontend using Gemini Live and LangGraph orchestration.

## 📁 Files

- **endpoints.json**: Machine-readable catalog of all API endpoints (82+ endpoints)
- **function_schema.json**: Function schemas for Gemini function calling
- **README.md**: This file

## 🎯 Purpose

These integrations enable:

1. **Voice Interface**: Real-time voice interaction with clinical data
2. **LangGraph Orchestration**: Structured workflow execution with streaming updates
3. **Audit & Traceability**: Complete audit trail for all AI-assisted operations
4. **Source Verification**: Every AI response includes source references (no hallucinations)

## 📚 Key Endpoints

### Integration Endpoints

#### `GET /api/v1/integration/user-context`
Returns secure user context for system prompt injection.

**Response:**
```json
{
  "is_first_time": false,
  "user_name": "dr_lopez",
  "summary": "La última vez actualizó un tratamiento",
  "last_active": "2025-12-11T01:00:00Z"
}
```

**Use Case**: When a professional logs in, the frontend calls this endpoint. If `is_first_time` is true, Gemini plays a guided welcome. Otherwise, it gives a short greeting and mentions the last topic worked on.

#### `POST /api/v1/integration/save-transcript`
Saves voice conversation transcripts in batch.

**Request:**
```json
{
  "transcripts": [
    {
      "session_id": "session-123",
      "user_text": "Muéstrame la agenda de mañana",
      "assistant_text": "Encontré 3 citas programadas...",
      "timestamp": "2025-12-11T01:30:00Z",
      "langgraph_job_id": "job-abc-123"
    }
  ]
}
```

**Response:**
```json
{
  "ok": true,
  "saved": 1
}
```

**Use Case**: The frontend "stenographer" sends each turn to the backend after each exchange. This allows auditing conversations and recovering history to resume sessions.

#### `GET /api/v1/integration/transcript-history?session_id=session-123`
Retrieves transcript history for a session.

**Response:**
```json
{
  "session_id": "session-123",
  "transcripts": [
    {
      "user_text": "Muéstrame la agenda",
      "assistant_text": "Encontré 3 citas...",
      "timestamp": "2025-12-11T01:30:00Z"
    }
  ]
}
```

### WebSocket Endpoint

#### `WS /ws/langgraph-stream?token=<jwt>`
Bidirectional WebSocket for LangGraph streaming updates.

**Client -> Server Messages:**

```json
{
  "action": "start_job",
  "session_id": "session-123",
  "user_id": 1,
  "utterance": "Muéstrame la agenda de mañana"
}
```

**Server -> Client Messages:**

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

**Use Case**: When user asks "Muéstrame la agenda de mañana", the frontend opens WS with LangGraph, shows immediate "Permítame un momento..." bridge text, and receives partial updates. These updates are shown in the "Agenda" tab and read aloud by Gemini while the final list is being prepared.

## 🔐 Security Features

### PII/PHI Masking
All sensitive data in audit logs is automatically masked using `mask_sensitive_data()`:

- **Emails**: `john.doe@example.com` → `j***e@e***e.com`
- **Phones**: `+52 123 456 7890` → `+52 *** *** 7890`
- **IDs**: `123-45-6789` → `***-6789`
- **Passwords**: Always masked as `***MASKED***`

### Response Hashing
Every sensitive response includes a SHA-256 hash for non-repudiation:

```python
from backend.api.utils.security_utils import compute_response_hash

response_hash = compute_response_hash(data)
# Store in audit log for verification
```

### Source References
Every AI response must include source references:

```python
from backend.api.utils.security_utils import create_source_refs

source_ref = create_source_refs(
    table="pacientes",
    record_id=123,
    fields=["nombre", "fecha_nacimiento"],
    confidence=1.0
)
```

## 🔍 Audit Middleware

Automatic logging is enabled for sensitive endpoints via `AuditMiddleware`:

**Audited paths:**
- `/api/v1/pacientes`
- `/api/v1/tratamientos`
- `/api/v1/evoluciones`
- `/api/v1/citas`
- `/api/v1/usuarios`
- `/api/v1/finance`

**What gets logged:**
- User ID, username, session ID
- IP address
- HTTP method and endpoint
- Masked request body
- Response hash
- Source references

**Note**: Audit middleware does NOT interrupt requests if logging fails - it logs errors and continues.

## 📊 Database Models

### VoiceTranscript
```sql
CREATE TABLE auth.voice_transcripts (
    id_transcript BIGSERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,
    user_id BIGINT NOT NULL REFERENCES auth.sys_usuarios(id_usuario),
    user_text TEXT NOT NULL,
    assistant_text TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    langgraph_job_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_voice_transcripts_session ON auth.voice_transcripts(session_id);
```

### Enhanced AuditLog
```sql
ALTER TABLE auth.audit_log ADD COLUMN username VARCHAR;
ALTER TABLE auth.audit_log ADD COLUMN session_id VARCHAR;
ALTER TABLE auth.audit_log ADD COLUMN method VARCHAR;
ALTER TABLE auth.audit_log ADD COLUMN endpoint VARCHAR;
ALTER TABLE auth.audit_log ADD COLUMN request_body TEXT;
ALTER TABLE auth.audit_log ADD COLUMN response_hash VARCHAR;
ALTER TABLE auth.audit_log ADD COLUMN source_refs JSONB;
ALTER TABLE auth.audit_log ADD COLUMN note TEXT;
```

## 🛠️ Usage Examples

### Using endpoints.json in LangGraph

```python
import json

# Load endpoint catalog
with open('backend/integration/endpoints.json') as f:
    catalog = json.load(f)

# Find endpoint for creating appointments
for endpoint in catalog['endpoints']:
    if endpoint['path'] == '/api/v1/citas' and endpoint['method'] == 'POST':
        print(f"Use: {endpoint['function_name']}")
        print(f"Auth required: {endpoint['auth_required']}")
        print(f"Roles: {endpoint['roles_allowed']}")
```

### Using function_schema.json for Gemini

```python
import json

# Load function schemas
with open('backend/integration/function_schema.json') as f:
    schemas = json.load(f)

# Configure Gemini with available functions
gemini_functions = schemas['functions']
```

### Masking Sensitive Data

```python
from backend.api.utils.security_utils import mask_sensitive_data

data = {
    "nombre": "Juan Pérez",
    "email": "juan.perez@example.com",
    "telefono": "+52 123 456 7890",
    "password": "secret123"
}

masked = mask_sensitive_data(data)
# {
#   "nombre": "Juan Pérez",
#   "email": "j***z@e***e.com",
#   "telefono": "+52 *** *** 7890",
#   "password": "***MASKED***"
# }
```

## 📝 Development Notes

### Migration Required
The following database changes require migrations:

1. Add new columns to `auth.audit_log`
2. Create `auth.voice_transcripts` table

**Migration steps:**
1. Create Alembic migration script
2. Backup production database
3. Test migration in staging
4. Apply to production with approval

### Testing
- Unit tests: Test masking functions, hash computation
- Integration tests: Test WebSocket flow, transcript saving
- Contract tests: Validate endpoints.json matches implementation

### Compliance
- Transcripts are PII/PHI - implement retention policy
- Require user consent before saving transcripts
- Implement data export for GDPR/user rights

## 🚀 Deployment Checklist

- [ ] Create database migrations
- [ ] Backup production database
- [ ] Test migrations in staging
- [ ] Update OpenAPI documentation
- [ ] Add unit tests for security utilities
- [ ] Add integration tests for WebSocket
- [ ] Configure retention policy for transcripts
- [ ] Implement user consent mechanism
- [ ] Review with security team
- [ ] Get approval for PII/PHI handling
- [ ] Deploy to staging
- [ ] Validate in staging
- [ ] Deploy to production
- [ ] Monitor audit logs

## 📖 References

- Main prompt: `/ARCHIVE_BACKEND_FOR_AGENTS_PROMPT.md`
- Security utils: `/backend/api/utils/security_utils.py`
- Audit middleware: `/backend/api/middleware/audit_middleware.py`
- Integration routes: `/backend/api/routes/integration.py`
- WebSocket routes: `/backend/api/routes/websocket_langgraph.py`

## 🤝 Support

For questions or issues, refer to the main prompt document or contact the development team.

---

**Generated**: 2025-12-11
**Version**: 1.0.0
**Status**: Implementation Complete (requires database migrations)
