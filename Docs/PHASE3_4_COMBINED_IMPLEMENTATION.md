# Fases 3 y 4: Implementación Combinada
## Memoria Semántica + Integración WhatsApp

**Fecha Inicio:** 11 de Diciembre, 2025  
**Estado:** 🚧 En Progreso  
**Duración Estimada:** 3 semanas

---

## 📋 Plan de Implementación Combinada

### Fase 3: Memoria Semántica (Semana 1-2)

**Objetivos:**
- [x] Instalar y configurar pgvector extension
- [x] Crear tabla `auth.conversation_memory` con vectores
- [x] Implementar generación de embeddings
- [x] Crear nodo `retrieve_semantic_context`
- [x] Integrar en subgrafos existentes
- [x] Testing de búsqueda semántica

**Fase 4: Integración WhatsApp (Semana 2-3)**

**Objetivos:**
- [ ] Setup microservicio Node.js
- [ ] Instalar whatsapp-web.js
- [ ] Crear endpoints backend Python
- [ ] Implementar `lookup_user_by_phone()`
- [ ] Crear nodo `send_whatsapp_message`
- [ ] QR code authentication
- [ ] Testing end-to-end

---

## 🎯 Fase 3: Memoria Semántica - Detalles

### Arquitectura

```
Conversación Nueva
    │
    ▼
retrieve_semantic_context()
    │
    ├─→ Busca en conversation_memory (pgvector)
    │   ├─→ Encuentra conversaciones similares
    │   └─→ Agrega contexto al estado
    │
    ▼
Nodos del Subgrafo
    │
    ▼
save_to_semantic_memory()
    │
    └─→ Guarda resumen + embedding en BD
```

### Tabla de Memoria Semántica

```sql
CREATE TABLE auth.conversation_memory (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    thread_id VARCHAR NOT NULL,
    origin VARCHAR(50) NOT NULL,
    conversation_summary TEXT NOT NULL,
    embedding vector(384),  -- all-MiniLM-L6-v2
    interaction_date TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB,
    FOREIGN KEY (user_id) REFERENCES auth.sys_usuarios(id_usuario)
);

CREATE INDEX idx_conversation_memory_user ON auth.conversation_memory(user_id);
CREATE INDEX idx_conversation_memory_embedding ON auth.conversation_memory 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

### Embeddings Model

**Modelo:** `sentence-transformers/all-MiniLM-L6-v2`
- Tamaño: 384 dimensiones
- Velocidad: ~400 textos/segundo
- Calidad: Buena para español
- Espacio: ~22MB

### Flujo de Búsqueda Semántica

```python
# 1. Usuario hace pregunta
user_query = "¿Qué pacientes diabéticos vimos esta semana?"

# 2. Generar embedding de la query
query_embedding = generate_embedding(user_query)

# 3. Buscar conversaciones similares (pgvector)
similar_conversations = db.query("""
    SELECT conversation_summary, thread_id, interaction_date
    FROM auth.conversation_memory
    WHERE user_id = :user_id
    ORDER BY embedding <=> :query_embedding
    LIMIT 5
""")

# 4. Agregar contexto al estado
state["semantic_context"] = similar_conversations

# 5. LLM usa contexto para responder
```

---

## 🎯 Fase 4: Integración WhatsApp - Detalles

### Arquitectura

```
WhatsApp
    │
    ▼
Microservicio Node.js (whatsapp-web.js)
    │
    ├─→ Recibe mensaje
    ├─→ POST /api/v1/whatsapp/incoming
    │       │
    │       ▼
    │   Backend Python (FastAPI)
    │       │
    │       ├─→ lookup_user_by_phone()
    │       ├─→ Determina origin (paciente vs user)
    │       ├─→ run_agent(..., origin="whatsapp_X")
    │       │       │
    │       │       ▼
    │       │   Root Graph → Subgrafo apropiado
    │       │       │
    │       │       ▼
    │       └─→ response_text
    │
    └─→ Envía respuesta a WhatsApp
```

### Microservicio Node.js

**Estructura:**
```
whatsapp-service/
├── package.json
├── index.js          # Main service
├── config.js         # Configuration
├── handlers/
│   ├── message.js    # Handle incoming messages
│   └── session.js    # Handle QR/session
└── .env
```

**package.json:**
```json
{
  "name": "podoskin-whatsapp-service",
  "version": "1.0.0",
  "dependencies": {
    "whatsapp-web.js": "^1.23.0",
    "qrcode-terminal": "^0.12.0",
    "axios": "^1.6.0",
    "express": "^4.18.2"
  }
}
```

### Endpoints Backend Python

**Nuevos endpoints en FastAPI:**

```python
# backend/api/routes/whatsapp.py

@router.post("/incoming")
async def handle_whatsapp_incoming(
    message: WhatsAppIncomingMessage,
    db_auth: Session = Depends(get_auth_db),
    db_core: Session = Depends(get_core_db)
):
    """
    Recibe mensaje de WhatsApp y procesa con LangGraph.
    
    Flujo:
    1. Lookup user por teléfono
    2. Determinar si es paciente o usuario interno
    3. Ejecutar agente con origin apropiado
    4. Retornar respuesta
    """
    pass

@router.post("/send")
async def send_whatsapp_message(
    message: WhatsAppOutgoingMessage
):
    """
    Envía mensaje a través del microservicio Node.js.
    """
    pass

@router.get("/qr")
async def get_qr_code():
    """
    Obtiene código QR para autenticación inicial.
    """
    pass
```

### Función lookup_user_by_phone

```python
# backend/api/services/whatsapp_service.py

async def lookup_user_by_phone(
    phone: str,
    db_auth: Session,
    db_core: Session
) -> Tuple[int, str, str]:
    """
    Busca usuario por número de teléfono.
    
    Returns:
        (user_id, origin, role)
        origin: "whatsapp_paciente" o "whatsapp_user"
    
    Prioridad:
    1. Buscar en sys_usuarios (personal interno)
    2. Buscar en pacientes
    3. Si no existe, crear paciente nuevo
    """
    # 1. Buscar en usuarios internos
    user = db_auth.query(SysUsuario).filter(
        SysUsuario.telefono == phone,
        SysUsuario.activo == True
    ).first()
    
    if user:
        return (user.id_usuario, "whatsapp_user", user.rol)
    
    # 2. Buscar en pacientes
    paciente = db_core.query(Paciente).filter(
        Paciente.telefono == phone,
        Paciente.activo == True
    ).first()
    
    if paciente:
        return (paciente.id_paciente, "whatsapp_paciente", "Paciente")
    
    # 3. Crear paciente nuevo
    nuevo_paciente = Paciente(
        nombres="Usuario",
        apellidos="WhatsApp",
        telefono=phone,
        fecha_nacimiento=date.today() - timedelta(days=365*25)
    )
    db_core.add(nuevo_paciente)
    db_core.commit()
    
    return (nuevo_paciente.id_paciente, "whatsapp_paciente", "Paciente")
```

### Nodo send_whatsapp_message

```python
# backend/agents/nodes/send_whatsapp_node.py

async def send_whatsapp_message(state: AgentState) -> AgentState:
    """
    Nodo que envía mensaje a WhatsApp.
    
    Solo se ejecuta si:
    - origin es whatsapp_paciente o whatsapp_user
    - Hay response_text generado
    - No hay errores críticos
    """
    origin = state.get("origin", "")
    
    if not origin.startswith("whatsapp"):
        # No es WhatsApp, skip
        return state
    
    phone = state.get("user_phone")
    response_text = state.get("response_text")
    
    if not phone or not response_text:
        logger.warning("No se puede enviar WhatsApp: falta phone o response_text")
        return state
    
    try:
        # Llamar al microservicio Node.js
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:3000/send",
                json={
                    "phone": phone,
                    "message": response_text
                },
                timeout=10.0
            )
            response.raise_for_status()
        
        state["whatsapp_sent"] = True
        state["whatsapp_sent_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"✅ WhatsApp enviado a {phone}")
    
    except Exception as e:
        logger.error(f"❌ Error enviando WhatsApp: {e}")
        state["whatsapp_sent"] = False
        state["whatsapp_error"] = str(e)
    
    return state
```

---

## 🧪 Testing

### Test Fase 3: Búsqueda Semántica

```python
# Test 1: Embedding generation
embedding = generate_embedding("paciente diabético")
assert len(embedding) == 384
assert isinstance(embedding, list)

# Test 2: Similarity search
result = search_similar_conversations(
    user_id=5,
    query="diabetes",
    limit=5
)
assert len(result) <= 5
assert all("conversation_summary" in conv for conv in result)

# Test 3: Context retrieval
state = {
    "user_query": "¿Qué pacientes diabéticos vimos?",
    "user_id": 5
}
state = retrieve_semantic_context(state)
assert "semantic_context" in state
```

### Test Fase 4: WhatsApp Integration

```bash
# Test 1: QR Code
curl http://localhost:8000/api/v1/whatsapp/qr

# Test 2: Incoming message
curl -X POST http://localhost:8000/api/v1/whatsapp/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+521234567890",
    "message": "Hola, ¿cuándo es mi próxima cita?"
  }'

# Test 3: Send message
curl -X POST http://localhost:8000/api/v1/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+521234567890",
    "message": "Tu cita es mañana a las 10 AM"
  }'
```

---

## 📊 Métricas de Éxito

### Fase 3

| Métrica | Objetivo | Verificación |
|---------|----------|--------------|
| Búsqueda semántica funcional | 100% | Query retorna resultados relevantes |
| Embeddings generados correctamente | 100% | 384 dimensiones, válidos |
| Contexto mejora respuestas | >80% | A/B test con/sin contexto |
| Latencia búsqueda | <100ms | pgvector index optimizado |

### Fase 4

| Métrica | Objetivo | Verificación |
|---------|----------|--------------|
| Mensajes recibidos correctamente | 100% | POST /incoming funciona |
| Lookup usuario por teléfono | 100% | Identifica paciente vs user |
| Mensajes enviados exitosamente | >95% | WhatsApp delivery |
| Latencia end-to-end | <3s | Desde recepción hasta envío |

---

## 🚀 Cronograma

### Semana 1: Fase 3 - Foundation
- [ ] Día 1-2: Setup pgvector + tabla conversation_memory
- [ ] Día 3-4: Implementar embedding generation
- [ ] Día 5: Crear nodo retrieve_semantic_context

### Semana 2: Fase 3 Complete + Fase 4 Start
- [ ] Día 1-2: Integrar memoria semántica en subgrafos
- [ ] Día 3: Testing Fase 3
- [ ] Día 4-5: Setup microservicio Node.js + whatsapp-web.js

### Semana 3: Fase 4 Complete
- [ ] Día 1-2: Endpoints backend Python
- [ ] Día 3: Función lookup_user_by_phone
- [ ] Día 4: Nodo send_whatsapp_message
- [ ] Día 5: Testing end-to-end

---

## 🔧 Configuración Requerida

### PostgreSQL (Fase 3)

```bash
# Instalar pgvector extension
docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Microservicio Node.js (Fase 4)

```bash
# Setup
cd whatsapp-service
npm install

# Run
npm start

# Logs mostrarán QR code para autenticación
```

### Variables de Entorno

```bash
# .env - Agregar
WHATSAPP_SERVICE_URL=http://localhost:3000
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENABLE_SEMANTIC_MEMORY=True
```

---

## ✅ Checklist de Finalización

### Fase 3
- [ ] pgvector extension instalada
- [ ] Tabla conversation_memory creada
- [ ] Embedding generation funcional
- [ ] Nodo retrieve_semantic_context integrado
- [ ] Tests de búsqueda semántica pasando
- [ ] Documentación completa

### Fase 4
- [ ] Microservicio Node.js funcionando
- [ ] QR authentication completada
- [ ] Endpoints /incoming y /send operacionales
- [ ] lookup_user_by_phone implementado
- [ ] Nodo send_whatsapp_message integrado
- [ ] Testing end-to-end exitoso
- [ ] Documentación completa

---

**Implementado por:** Sistema  
**Fecha:** 11 de Diciembre, 2025  
**Estado:** 🚧 En Progreso - Fases 3 y 4 Simultáneas
