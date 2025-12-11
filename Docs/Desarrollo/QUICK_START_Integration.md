# Quick Start Guide: Voice Integration Features

This guide helps you quickly get started with the new voice-controlled frontend integration features.

## 🚀 Quick Overview

The PodoSkin API now supports voice-controlled frontend integration with:
- **User Context API**: Get personalized context for voice assistants
- **Transcript Storage**: Save and retrieve voice conversation history
- **WebSocket Streaming**: Real-time updates from LangGraph workflows
- **Security**: PII/PHI masking, response hashing, audit trails

## 📋 Prerequisites

1. ✅ Backend API running
2. ⚠️ Database migration applied (see MIGRATION_PLAN.md)
3. ✅ JWT authentication configured
4. ✅ User with valid credentials

## 🔑 Authentication

All integration endpoints require JWT authentication:

```bash
# 1. Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'

# Response contains access_token
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}

# 2. Use token in subsequent requests
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

## 🎯 Using Integration Endpoints

### 1. Get User Context

Perfect for personalizing voice assistant greetings:

```bash
curl -X GET http://localhost:8000/api/v1/integration/user-context \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "is_first_time": false,
  "user_name": "dr_lopez",
  "summary": "La última vez actualizó un tratamiento",
  "last_active": "2025-12-11T01:00:00Z"
}
```

**Frontend Usage**:
```javascript
// In your voice assistant initialization
const context = await fetch('/api/v1/integration/user-context', {
  headers: { 'Authorization': `Bearer ${token}` }
}).then(r => r.json());

if (context.is_first_time) {
  gemini.speak("Bienvenido a PodoSkin. Permíteme mostrarte cómo funciona...");
} else {
  gemini.speak(`Hola ${context.user_name}, ${context.summary}`);
}
```

### 2. Save Voice Transcripts

Store conversation history for audit and recovery:

```bash
curl -X POST http://localhost:8000/api/v1/integration/save-transcript \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "transcripts": [
      {
        "session_id": "session-abc-123",
        "user_text": "Muéstrame la agenda de mañana",
        "assistant_text": "Encontré 3 citas programadas para mañana",
        "timestamp": "2025-12-11T10:30:00Z",
        "langgraph_job_id": "job-xyz-456"
      }
    ]
  }'
```

**Response**:
```json
{
  "ok": true,
  "saved": 1
}
```

**Frontend Usage**:
```javascript
// After each voice exchange
const saveTranscript = async (sessionId, userText, assistantText) => {
  await fetch('/api/v1/integration/save-transcript', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      transcripts: [{
        session_id: sessionId,
        user_text: userText,
        assistant_text: assistantText,
        timestamp: new Date().toISOString(),
        langgraph_job_id: null
      }]
    })
  });
};

// Use in your voice handler
gemini.on('exchange', async (userText, assistantText) => {
  await saveTranscript(currentSessionId, userText, assistantText);
});
```

### 3. Retrieve Transcript History

Get conversation history for a session:

```bash
curl -X GET "http://localhost:8000/api/v1/integration/transcript-history?session_id=session-abc-123" \
  -H "Authorization: Bearer $TOKEN"
```

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

### 4. WebSocket Streaming (LangGraph)

Real-time communication with LangGraph workflows:

```javascript
// Connect to WebSocket
const ws = new WebSocket(`ws://localhost:8000/ws/langgraph-stream?token=${token}`);

ws.onopen = () => {
  console.log('Connected to LangGraph stream');
  
  // Start a job
  ws.send(JSON.stringify({
    action: 'start_job',
    session_id: 'session-123',
    user_id: 1,
    utterance: 'Muéstrame la agenda de mañana',
    job_metadata: {}
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'job_started':
      console.log('Job started:', message.job_id);
      showSpinner("Procesando...");
      break;
      
    case 'update':
      console.log('Update:', message.content);
      updateStatus(message.content);  // "Consultando disponibilidad..."
      gemini.speak(message.content);  // Read aloud
      break;
      
    case 'final':
      console.log('Final result:', message.data);
      hideSpinner();
      displayResult(message.data);
      break;
      
    case 'error':
      console.error('Error:', message.message);
      showError(message.message);
      break;
  }
};

// Cancel a job
const cancelJob = (jobId) => {
  ws.send(JSON.stringify({
    action: 'cancel',
    job_id: jobId
  }));
};

// Send follow-up
const followUp = (jobId, utterance) => {
  ws.send(JSON.stringify({
    action: 'followup',
    job_id: jobId,
    utterance: utterance
  }));
};
```

## 🔐 Security Features

### PII/PHI Masking (Automatic)

All sensitive data in audit logs is automatically masked:

```python
from backend.api.utils.security_utils import mask_sensitive_data

# In your endpoint
data = {
    "nombre": "Juan Pérez",
    "email": "juan@example.com",
    "telefono": "+52 123 456 7890"
}

# Before logging to audit
masked = mask_sensitive_data(data)
# {
#   "nombre": "Juan Pérez",
#   "email": "j***n@e***e.com",
#   "telefono": "+52 *** *** 7890"
# }
```

### Response Hashing (For Non-Repudiation)

Compute and store response hashes:

```python
from backend.api.utils.security_utils import compute_response_hash

# In your endpoint
response_data = {"id": 123, "nombre": "Juan Pérez"}
response_hash = compute_response_hash(response_data)

# Store in audit log
audit_log.response_hash = response_hash
```

### Source References (For Data Provenance)

Track where data comes from:

```python
from backend.api.utils.security_utils import create_source_refs

# When returning patient data
source_ref = create_source_refs(
    table="pacientes",
    record_id=123,
    fields=["nombre", "fecha_nacimiento"],
    confidence=1.0
)

# Include in response
return {
    "data": patient_data,
    "source_refs": [source_ref],
    "response_hash": compute_response_hash(patient_data)
}
```

## 📊 Using API Catalogs

### For LangGraph (endpoints.json)

```python
import json

# Load endpoint catalog
with open('backend/integration/endpoints.json') as f:
    catalog = json.load(f)

# Find endpoints for patient operations
patient_endpoints = [
    ep for ep in catalog['endpoints'] 
    if 'pacientes' in ep['path']
]

# Create LangGraph tools
from langchain.tools import Tool

tools = []
for endpoint in patient_endpoints:
    if endpoint['method'] == 'GET' and endpoint['path'].endswith('/pacientes'):
        tools.append(Tool(
            name='list_patients',
            description='Lista pacientes del sistema',
            func=lambda: call_api(endpoint)
        ))
```

### For Gemini (function_schema.json)

```python
import json

# Load function schemas
with open('backend/integration/function_schema.json') as f:
    schemas = json.load(f)

# Configure Gemini
import google.generativeai as genai

model = genai.GenerativeModel(
    model_name='gemini-pro',
    tools=schemas['functions']
)

# Gemini will now use these functions
response = model.generate_content(
    "Muéstrame el paciente 123",
    tool_config={'function_calling_config': 'AUTO'}
)
```

## 🧪 Testing

### Run Unit Tests

```bash
cd backend
python3 tests/test_security_utils.py
```

**Expected output**:
```
Running basic security utils tests...
✓ Email masking: john.doe@example.com -> j***e@e***e.com
✓ Phone masking: +52 123 456 7890 -> +52 *** *** 7890
✓ Data masking: ...
✓ Hash computation: ...
✓ Source refs: ...
✓ Hash order independence: True

✅ All basic tests passed!
```

### Test Endpoints with curl

```bash
# Set token
export TOKEN="your_jwt_token_here"

# Test user context
curl -X GET http://localhost:8000/api/v1/integration/user-context \
  -H "Authorization: Bearer $TOKEN" | jq

# Test save transcript
curl -X POST http://localhost:8000/api/v1/integration/save-transcript \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"transcripts":[{"session_id":"test","user_text":"Hola","assistant_text":"Hola!","timestamp":"2025-12-11T10:00:00Z"}]}' | jq

# Test transcript history
curl -X GET "http://localhost:8000/api/v1/integration/transcript-history?session_id=test" \
  -H "Authorization: Bearer $TOKEN" | jq
```

## 🐛 Troubleshooting

### Issue: 401 Unauthorized
**Solution**: Check that your JWT token is valid and not expired.

```bash
# Get a fresh token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your_password"}'
```

### Issue: WebSocket connection fails
**Solution**: Make sure to pass the token as query parameter:
```javascript
const ws = new WebSocket(`ws://localhost:8000/ws/langgraph-stream?token=${token}`);
```

### Issue: Database errors
**Solution**: Make sure migrations have been applied:
```bash
# Check if tables exist
docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db \
  -c "\dt auth.voice_transcripts"

# If not, apply migration
# See backend/integration/MIGRATION_PLAN.md
```

### Issue: Import errors
**Solution**: Make sure all dependencies are installed:
```bash
pip install -r backend/requirements.txt
```

## 📚 Additional Resources

- **Full Documentation**: `backend/integration/README.md`
- **Migration Guide**: `backend/integration/MIGRATION_PLAN.md`
- **Implementation Summary**: `IMPLEMENTATION_SUMMARY.md`
- **API Catalog**: `backend/integration/endpoints.json`
- **Function Schemas**: `backend/integration/function_schema.json`
- **Security Utils**: `backend/api/utils/security_utils.py`

## 🎯 Next Steps

1. ✅ Apply database migration
2. ✅ Test all endpoints
3. ✅ Integrate with Gemini Live
4. ✅ Integrate with LangGraph
5. ✅ Configure user consent mechanism
6. ✅ Set up retention policy for transcripts

## 💡 Examples

Check out these complete examples:

- **Voice Assistant Integration**: See WebSocket example above
- **Audit Trail Query**: See audit endpoint in main API
- **PII Masking**: See security_utils tests

## 🤝 Support

For questions or issues:
1. Check documentation in `backend/integration/`
2. Review implementation summary
3. Check test files for usage examples
4. Contact: @SalvadorCordova96

---

**Happy Coding! 🚀**
