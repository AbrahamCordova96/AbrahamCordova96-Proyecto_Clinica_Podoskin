# Análisis de Arquitectura de Memoria para LangGraph
## Sistema de Mensajería Conversacional Multi-Canal

**Fecha:** 11 de Diciembre, 2025  
**Versión:** 1.0  
**Estado:** Análisis Técnico - Pendiente Implementación

---

## 📋 Resumen Ejecutivo

Este documento analiza la implementación de sistemas de memoria (semántica, episódica, corto y largo plazo) en el backend LangGraph del proyecto PodoSkin, siguiendo la arquitectura propuesta de orquestación centralizada. Se evalúan las capacidades actuales, se identifican gaps críticos y se propone una ruta de implementación alineada con las mejores prácticas de LangGraph y la retroalimentación oficial recibida.

### Hallazgos Clave

✅ **Infraestructura Lista:**
- `langgraph-checkpoint-postgres==3.0.1` instalado pero no utilizado
- Base de datos PostgreSQL con 3 schemas separados
- `voice_transcripts` table para almacenar conversaciones
- WebSocket endpoint para streaming en tiempo real

❌ **Gaps Críticos:**
- **NO hay checkpointer activo** - el grafo se compila sin persistencia de estado
- **NO hay memoria semántica** - sin vector store ni RAG
- **NO hay manejo de concurrencia** - riesgo de cruce de estados entre conversaciones
- **NO hay subgrafos por origen** - WhatsApp paciente vs usuario interno no están separados

---

## 1. Estado Actual del Sistema de Memoria

### 1.1 Análisis de Código Existente

#### Grafo LangGraph (`backend/agents/graph.py`)

```python
# LÍNEA 257 - PROBLEMA CRÍTICO
def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        workflow = build_agent_graph()
        _compiled_graph = workflow.compile()  # ❌ SIN CHECKPOINTER
        logger.info("Grafo del agente compilado exitosamente")
    return _compiled_graph
```

**Impacto:** Cada invocación del agente es completamente stateless. No hay persistencia de memoria episódica entre turnos de conversación.

#### Estado del Agente (`backend/agents/state.py`)

```python
class AgentState(TypedDict, total=False):
    # Input del usuario
    user_query: str
    user_id: int
    user_role: str
    session_id: str  # ⚠️ Generado pero no usado para persistencia
    
    # Clasificación
    intent: IntentType
    entities_extracted: Dict[str, Any]
    
    # ... más campos ...
    
    # ❌ FALTA: thread_id para checkpointing
    # ❌ FALTA: conversation_id único persistente
    # ❌ FALTA: origin (WhatsApp Paciente vs Usuario Interno)
```

**Gaps Identificados:**
1. No existe `thread_id` para identificar hilos de conversación
2. `session_id` es UUID temporal, no se persiste en BD
3. No hay campo `origin` para distinguir origen de la conversación
4. No hay campo `memory_context` para almacenar contexto recuperado

### 1.2 Infraestructura de Datos Existente

#### Tabla `auth.voice_transcripts`

```sql
CREATE TABLE auth.voice_transcripts (
    id_transcript BIGSERIAL PRIMARY KEY,
    session_id VARCHAR NOT NULL,           -- ⚠️ No es thread_id
    user_id BIGINT NOT NULL,
    user_text TEXT NOT NULL,
    assistant_text TEXT,
    timestamp TIMESTAMPTZ NOT NULL,
    langgraph_job_id VARCHAR,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Análisis:**
- ✅ Almacena transcripciones para auditoría
- ❌ No almacena estado completo del grafo (AgentState)
- ❌ No tiene estructura de threading (parent_id, thread_id)
- ❌ No distingue origen (WhatsApp paciente vs interno)

---

## 2. Tipos de Memoria: Análisis Detallado

### 2.1 Memoria Episódica (Checkpoints)

**Qué es:** Memoria de "timeline" que LangGraph usa para gestión de estado a corto plazo. Permite reanudar conversaciones exactamente donde se quedaron.

#### Estado Actual: ❌ NO IMPLEMENTADA

**Problema:** El grafo se compila sin `checkpointer`:
```python
# ACTUAL (INCORRECTO)
_compiled_graph = workflow.compile()

# DEBERÍA SER
from langgraph.checkpoint.postgres import PostgresSaver
checkpointer = PostgresSaver(connection_string)
_compiled_graph = workflow.compile(checkpointer=checkpointer)
```

**Impacto en Casos de Uso:**

```
Escenario: Agendar cita multi-turno

Turno 1:
Usuario: "Quiero agendar una cita"
Sistema: "¿Para qué día?" [Estado guardado: intent=AGENDAR]

Turno 2:
Usuario: "Mañana a las 3pm"
Sistema: ❌ ERROR - No recuerda que estábamos agendando
         (sin checkpointer, el estado se perdió)
```

#### Solución Propuesta

**Implementar PostgresSaver con tabla dedicada:**

```sql
-- Nueva tabla para checkpoints (manejada por LangGraph)
CREATE TABLE auth.langgraph_checkpoints (
    thread_id VARCHAR NOT NULL,
    checkpoint_id VARCHAR NOT NULL,
    parent_id VARCHAR,
    checkpoint JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread ON auth.langgraph_checkpoints(thread_id);
CREATE INDEX idx_checkpoints_parent ON auth.langgraph_checkpoints(parent_id);
```

**Código de Implementación:**

```python
# backend/agents/checkpoint_config.py
from langgraph.checkpoint.postgres import PostgresSaver
from backend.api.core.config import get_settings

def get_checkpointer():
    """Obtiene checkpointer PostgreSQL para memoria episódica."""
    settings = get_settings()
    
    # Usar AUTH_DB para checkpoints (donde están los usuarios)
    return PostgresSaver(
        connection_string=settings.AUTH_DB_URL,
        # LangGraph creará automáticamente la tabla si no existe
    )

# backend/agents/graph.py
def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        workflow = build_agent_graph()
        checkpointer = get_checkpointer()  # ✅ NUEVO
        _compiled_graph = workflow.compile(checkpointer=checkpointer)  # ✅ NUEVO
        logger.info("Grafo compilado con checkpointer PostgreSQL")
    return _compiled_graph
```

**Uso con thread_id:**

```python
# En el endpoint de chat
async def chat(request: ChatRequest, current_user: SysUsuario):
    # thread_id = formato: "{user_id}_{origin}_{conversation_uuid}"
    thread_id = f"{current_user.id_usuario}_webapp_{request.session_id}"
    
    result = await graph.ainvoke(
        initial_state,
        config={
            "configurable": {
                "thread_id": thread_id,  # ✅ Identificador único del hilo
            }
        }
    )
```

### 2.2 Memoria Semántica (Vector Store / RAG)

**Qué es:** Memoria "inteligente" a largo plazo basada en embeddings. Permite recuperar contexto relevante de interacciones pasadas usando similitud semántica.

#### Estado Actual: ❌ NO IMPLEMENTADA

**Infraestructura Parcial:**
```python
# backend/api/core/config.py (LÍNEAS 66-76)
# ✅ Configuración existe pero no se usa
EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION: int = 384
CHROMA_PERSIST_DIR: str = "data/chroma_db"
CHROMA_COLLECTION_NAME: str = "podoskin_schema"
```

**Problema:** Solo hay embeddings del **esquema de BD**, no de conversaciones pasadas ni documentos médicos.

#### Casos de Uso Críticos

**Caso 1: Continuidad Semántica Entre Sesiones**
```
Sesión 1 (Lunes):
Usuario: "El paciente Juan tiene diabetes tipo 2"
Sistema: [Guarda en vector store + registra tratamiento]

Sesión 2 (Viernes):
Usuario: "¿Qué pacientes con diabetes vimos esta semana?"
Sistema: ✅ Recupera contexto semántico de conversación del lunes
         "Juan Pérez, diagnosticado el lunes con diabetes tipo 2"
```

**Caso 2: RAG con Protocolos Médicos**
```
Usuario: "¿Cuál es el protocolo para pie diabético?"
Sistema: [Búsqueda en vector store de documentos médicos]
         ✅ Recupera protocolo de tratamiento
         ✅ Cita fuentes específicas del manual
```

#### Solución Propuesta: PostgreSQL + pgvector

**Por qué pgvector en lugar de ChromaDB:**
- Ya usamos PostgreSQL (3 bases de datos)
- Menor latencia (misma BD, sin servicio externo)
- Mejor para ACID y transacciones
- Soporte nativo de PostgreSQL 17

**Implementación:**

```sql
-- Instalar extensión en clinica_auth_db
CREATE EXTENSION IF NOT EXISTS vector;

-- Tabla para memoria semántica de conversaciones
CREATE TABLE auth.conversation_memory (
    id_memory BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth.sys_usuarios(id_usuario),
    origin VARCHAR(50) NOT NULL,  -- 'whatsapp_paciente', 'whatsapp_user', 'webapp'
    thread_id VARCHAR NOT NULL,
    turn_index INT NOT NULL,
    content TEXT NOT NULL,         -- Texto original
    embedding vector(384) NOT NULL, -- Embedding del contenido
    metadata JSONB,                -- Entidades, intent, etc.
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Índice para búsqueda vectorial
    UNIQUE(thread_id, turn_index)
);

CREATE INDEX idx_conversation_memory_user ON auth.conversation_memory(user_id);
CREATE INDEX idx_conversation_memory_origin ON auth.conversation_memory(origin);
CREATE INDEX idx_conversation_memory_embedding ON auth.conversation_memory 
    USING ivfflat (embedding vector_cosine_ops);

-- Tabla para documentos médicos (protocolos, guías)
CREATE TABLE auth.medical_knowledge (
    id_doc BIGSERIAL PRIMARY KEY,
    doc_type VARCHAR(50) NOT NULL,  -- 'protocol', 'guide', 'reference'
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_medical_knowledge_embedding ON auth.medical_knowledge
    USING ivfflat (embedding vector_cosine_ops);
```

**Código de Implementación:**

```python
# backend/agents/memory/semantic_memory.py
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from typing import List, Dict, Any
import numpy as np

class SemanticMemory:
    """Gestiona memoria semántica usando pgvector."""
    
    def __init__(self, db_session, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.db = db_session
        self.model = SentenceTransformer(model_name)
    
    def embed_text(self, text: str) -> List[float]:
        """Genera embedding de un texto."""
        embedding = self.model.encode(text)
        return embedding.tolist()
    
    def store_conversation_turn(
        self,
        user_id: int,
        origin: str,
        thread_id: str,
        turn_index: int,
        content: str,
        metadata: Dict[str, Any]
    ):
        """Almacena un turno de conversación en memoria semántica."""
        embedding = self.embed_text(content)
        
        query = text("""
            INSERT INTO auth.conversation_memory 
            (user_id, origin, thread_id, turn_index, content, embedding, metadata)
            VALUES (:user_id, :origin, :thread_id, :turn_index, :content, :embedding, :metadata)
            ON CONFLICT (thread_id, turn_index) DO NOTHING
        """)
        
        self.db.execute(query, {
            "user_id": user_id,
            "origin": origin,
            "thread_id": thread_id,
            "turn_index": turn_index,
            "content": content,
            "embedding": embedding,
            "metadata": metadata
        })
        self.db.commit()
    
    def search_similar_conversations(
        self,
        query_text: str,
        user_id: int,
        origin: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Busca conversaciones similares semánticamente."""
        query_embedding = self.embed_text(query_text)
        
        sql = text("""
            SELECT 
                id_memory,
                content,
                metadata,
                timestamp,
                embedding <=> :query_embedding AS distance
            FROM auth.conversation_memory
            WHERE user_id = :user_id
                AND (:origin IS NULL OR origin = :origin)
            ORDER BY embedding <=> :query_embedding
            LIMIT :limit
        """)
        
        results = self.db.execute(sql, {
            "query_embedding": query_embedding,
            "user_id": user_id,
            "origin": origin,
            "limit": limit
        }).fetchall()
        
        return [
            {
                "id": row.id_memory,
                "content": row.content,
                "metadata": row.metadata,
                "timestamp": row.timestamp,
                "similarity": 1 - row.distance
            }
            for row in results
        ]
```

**Integración con Nodo del Grafo:**

```python
# backend/agents/nodes/semantic_context_node.py
from backend.agents.memory.semantic_memory import SemanticMemory

def retrieve_semantic_context(state: AgentState) -> AgentState:
    """Nodo que recupera contexto semántico relevante."""
    
    semantic_memory = SemanticMemory(db_session)
    
    # Buscar conversaciones similares
    similar_convs = semantic_memory.search_similar_conversations(
        query_text=state["user_query"],
        user_id=state["user_id"],
        origin=state.get("origin"),
        limit=3
    )
    
    # Agregar al estado
    state["memory_context"] = {
        "similar_conversations": similar_convs,
        "retrieved_at": datetime.now(timezone.utc)
    }
    
    return state
```

### 2.3 Memoria de Corto Plazo (Working Memory)

**Qué es:** Contexto activo de la conversación actual, mantenido en el `AgentState` durante la ejecución del grafo.

#### Estado Actual: ✅ PARCIALMENTE IMPLEMENTADA

**Existe en `AgentState`:**
```python
class AgentState(TypedDict, total=False):
    user_query: str                      # ✅ Consulta actual
    entities_extracted: Dict[str, Any]   # ✅ Entidades de esta conversación
    sql_query: SQLQuery                  # ✅ Query generada
    execution_result: ExecutionResult    # ✅ Resultado de ejecución
    response_text: str                   # ✅ Respuesta formateada
```

**Gaps:**
- ❌ No se preserva entre invocaciones (sin checkpointer)
- ❌ No hay `messages` list para contexto multi-turno
- ❌ No hay `pending_actions` para flujos interrumpibles

#### Mejoras Propuestas

```python
class AgentState(TypedDict, total=False):
    # ... campos existentes ...
    
    # ✅ NUEVO: Lista de mensajes para contexto
    messages: List[Dict[str, str]]  # [{"role": "user", "content": "..."}, ...]
    
    # ✅ NUEVO: Acciones pendientes (para flujos interrumpibles)
    pending_actions: List[Dict[str, Any]]  # [{"type": "consent", "data": {...}}]
    
    # ✅ NUEVO: Contexto recuperado de memoria semántica
    memory_context: Dict[str, Any]
    
    # ✅ NUEVO: Origen de la conversación
    origin: str  # "whatsapp_paciente", "whatsapp_user", "webapp"
    
    # ✅ NUEVO: Thread ID para checkpointing
    thread_id: str
```

### 2.4 Memoria de Largo Plazo (User Preferences & Patterns)

**Qué es:** Aprendizaje de patrones de uso, preferencias del usuario, comportamientos históricos.

#### Estado Actual: ❌ NO IMPLEMENTADA

**Casos de Uso:**
```
Patrón detectado:
- Usuario siempre pregunta por "citas de hoy" los lunes a las 9am

Acción proactiva:
- Sistema ofrece automáticamente el reporte sin esperar pregunta
- "Buenos días Dr. López, tienes 5 citas hoy. ¿Quieres ver los detalles?"
```

#### Solución Propuesta

```sql
CREATE TABLE auth.user_behavior_patterns (
    id_pattern BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES auth.sys_usuarios(id_usuario),
    pattern_type VARCHAR(50) NOT NULL,  -- 'frequent_query', 'schedule', 'preference'
    pattern_data JSONB NOT NULL,
    frequency INT DEFAULT 1,
    last_occurrence TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, pattern_type, pattern_data)
);

CREATE INDEX idx_user_patterns ON auth.user_behavior_patterns(user_id, pattern_type);
```

**Ejemplo de datos:**
```json
{
    "user_id": 5,
    "pattern_type": "frequent_query",
    "pattern_data": {
        "query_intent": "GET_APPOINTMENTS",
        "time_pattern": "monday_morning",
        "frequency": 15
    }
}
```

---

## 3. Arquitectura de Subgrafos por Origen

### 3.1 Problema Actual: Monolítico

**Análisis del grafo actual (`backend/agents/graph.py`):**

```python
# ACTUAL: Un solo grafo para todos los orígenes
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("check_permissions", check_permissions)
workflow.add_node("generate_sql", generate_sql)
# ... etc ...
```

**Problemas:**
1. Misma lógica para WhatsApp paciente y usuario interno
2. No hay separación de permisos por origen
3. No hay flujos especializados (ej: consentimiento solo para pacientes)
4. Difícil mantener y extender

### 3.2 Arquitectura Propuesta: Subgrafos Especializados

```
┌─────────────────────────────────────────────────────┐
│          Ingress Gateway (Punto de Entrada)         │
│  - Normaliza mensajes de WhatsApp, WebApp, etc.    │
│  - Asigna origin y thread_id                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│       LangGraph Orchestrator (Root Graph)           │
│  - Recibe mensaje normalizado                       │
│  - Determina subgrafo según origin                  │
│  - Gestiona estado global (checkpoints)             │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│  Subgraph:       │  │  Subgraph:       │
│  WhatsApp        │  │  WhatsApp        │
│  Paciente        │  │  Usuario Interno │
├──────────────────┤  ├──────────────────┤
│ - Consent UI     │  │ - No consent     │
│ - Permisos       │  │ - Permisos full  │
│   limitados      │  │ - Herramientas   │
│ - Flujo citas    │  │   administrativas│
│ - Info pública   │  │ - Gestión de BD  │
└──────────────────┘  └──────────────────┘
```

### 3.3 Implementación de Subgrafos

```python
# backend/agents/subgraphs/whatsapp_paciente.py
from langgraph.graph import StateGraph

def build_paciente_subgraph() -> StateGraph:
    """Subgrafo para interacciones con pacientes vía WhatsApp."""
    
    subgraph = StateGraph(AgentState)
    
    # Nodos específicos de paciente
    subgraph.add_node("validate_consent", validate_consent_node)
    subgraph.add_node("check_patient_permissions", check_patient_permissions_node)
    subgraph.add_node("fetch_appointments", fetch_appointments_node)
    subgraph.add_node("request_appointment", request_appointment_node)
    subgraph.add_node("send_whatsapp", send_whatsapp_message_node)
    
    # Flujo de decisión con consent obligatorio
    subgraph.set_entry_point("validate_consent")
    subgraph.add_conditional_edges(
        "validate_consent",
        route_after_consent,
        {
            "consent_granted": "check_patient_permissions",
            "consent_denied": "send_whatsapp",
            "request_consent": "send_whatsapp"
        }
    )
    
    # ... más edges ...
    
    return subgraph


# backend/agents/subgraphs/whatsapp_user.py
def build_user_subgraph() -> StateGraph:
    """Subgrafo para usuarios internos vía WhatsApp."""
    
    subgraph = StateGraph(AgentState)
    
    # Nodos específicos de usuario interno
    subgraph.add_node("check_admin_permissions", check_admin_permissions_node)
    subgraph.add_node("query_database", query_database_node)
    subgraph.add_node("manage_appointments", manage_appointments_node)
    subgraph.add_node("view_analytics", view_analytics_node)
    subgraph.add_node("send_whatsapp", send_whatsapp_message_node)
    
    # NO hay validación de consent (usuarios internos)
    subgraph.set_entry_point("check_admin_permissions")
    
    # ... más edges ...
    
    return subgraph


# backend/agents/graph.py (Root Graph)
from backend.agents.subgraphs.whatsapp_paciente import build_paciente_subgraph
from backend.agents.subgraphs.whatsapp_user import build_user_subgraph

def build_root_graph() -> StateGraph:
    """Grafo raíz que orquesta subgrafos."""
    
    root_graph = StateGraph(AgentState)
    
    # Registrar subgrafos
    root_graph.add_node("paciente_flow", build_paciente_subgraph().compile())
    root_graph.add_node("user_flow", build_user_subgraph().compile())
    
    # Nodo de routing
    root_graph.add_node("route_by_origin", route_by_origin_node)
    
    # Entry point
    root_graph.set_entry_point("route_by_origin")
    
    # Routing condicional
    root_graph.add_conditional_edges(
        "route_by_origin",
        lambda state: state.get("origin", "webapp"),
        {
            "whatsapp_paciente": "paciente_flow",
            "whatsapp_user": "user_flow",
            "webapp": "user_flow"  # Default a flujo de usuario
        }
    )
    
    return root_graph


# Nodo de routing
def route_by_origin_node(state: AgentState) -> AgentState:
    """Determina el origen y asigna metadata."""
    
    origin = state.get("origin")
    
    # Logging para debugging
    state["logs"] = state.get("logs", [])
    state["logs"].append({
        "node": "route_by_origin",
        "origin": origin,
        "user_id": state.get("user_id"),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return state
```

---

## 4. Manejo de Concurrencia

### 4.1 Problema Crítico: Aislamiento de Estado

**Escenario:**
```
Thread 1 (Dr. López, WhatsApp):
10:00:00 - "Muéstrame citas de hoy"
10:00:01 - [Procesando...]
10:00:02 - [Estado: user_id=5, citas=[A, B, C]]

Thread 2 (Recepcionista María, WebApp):
10:00:01 - "Agenda cita para Juan"
10:00:02 - [Procesando...]
10:00:03 - [Estado: user_id=8, paciente=Juan]

RIESGO: Sin aislamiento, el estado de Thread 2 puede sobrescribir Thread 1
```

### 4.2 Estrategia de Aislamiento

#### Particionamiento por `thread_id`

```python
# Formato de thread_id
def generate_thread_id(user_id: int, origin: str, conversation_uuid: str) -> str:
    """
    Genera thread_id único para aislamiento de estado.
    
    Formato: {user_id}_{origin}_{uuid}
    Ejemplo: 5_whatsapp_user_a1b2c3d4
    """
    return f"{user_id}_{origin}_{conversation_uuid}"


# Uso en invocación del grafo
async def invoke_agent_with_isolation(
    user_query: str,
    user_id: int,
    user_role: str,
    origin: str,
    session_id: str
):
    # Generar thread_id único
    thread_id = generate_thread_id(user_id, origin, session_id)
    
    # Configuración con aislamiento
    config = {
        "configurable": {
            "thread_id": thread_id,  # ✅ Cada thread tiene su propio estado
        }
    }
    
    graph = get_compiled_graph()
    result = await graph.ainvoke(initial_state, config=config)
    
    return result
```

#### Locks por Thread (Opcional)

Para prevenir race conditions si el mismo usuario inicia múltiples conversaciones simultáneas:

```python
# backend/agents/concurrency.py
import asyncio
from typing import Dict

class ThreadLockManager:
    """Gestiona locks por thread_id para evitar race conditions."""
    
    def __init__(self):
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def acquire_thread_lock(self, thread_id: str) -> asyncio.Lock:
        """Adquiere lock para un thread específico."""
        if thread_id not in self._locks:
            self._locks[thread_id] = asyncio.Lock()
        return self._locks[thread_id]
    
    async def invoke_with_lock(self, thread_id: str, graph, state, config):
        """Invoca el grafo con lock por thread."""
        lock = await self.acquire_thread_lock(thread_id)
        async with lock:
            return await graph.ainvoke(state, config=config)


# Uso global
thread_lock_manager = ThreadLockManager()


# En endpoint
async def chat_with_concurrency_control(request, user):
    thread_id = generate_thread_id(user.id_usuario, "webapp", request.session_id)
    
    config = {"configurable": {"thread_id": thread_id}}
    
    # Invocar con lock
    result = await thread_lock_manager.invoke_with_lock(
        thread_id,
        get_compiled_graph(),
        initial_state,
        config
    )
    
    return result
```

### 4.3 Límites de Tasa por Usuario

```python
# backend/api/middleware/rate_limit_user.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter por usuario (además del global por IP)
user_limiter = Limiter(key_func=lambda: f"user_{current_user.id_usuario}")

@router.post("/chat")
@user_limiter.limit("60/minute")  # 60 mensajes por minuto por usuario
async def chat(request, current_user):
    ...
```

---

## 5. Integración con WhatsApp Web.js

### 5.1 Análisis de Dependencias

**Librería Propuesta:** `whatsapp-web.js`
- Documentación: https://docs.wwebjs.dev/
- Node.js library (requiere bridge con Python backend)

**Opciones de Integración:**

#### Opción A: Microservicio Node.js + REST API (Recomendada)

```
┌──────────────────┐         HTTP          ┌──────────────────┐
│  WhatsApp Web.js │ ────────────────────> │  Python FastAPI  │
│  (Node.js)       │ <──────────────────── │  (LangGraph)     │
└──────────────────┘         JSON          └──────────────────┘
```

**Ventajas:**
- Separación de responsabilidades
- WhatsApp Web.js corre en Node.js (ambiente nativo)
- Backend Python no se contamina con Node
- Fácil escalar independientemente

**Implementación:**

```javascript
// whatsapp-service/server.js
const { Client, LocalAuth } = require('whatsapp-web.js');
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

// Cliente WhatsApp
const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { headless: true }
});

client.on('qr', (qr) => {
    console.log('QR Code:', qr);
    // TODO: Enviar QR a endpoint para mostrar en UI
});

client.on('ready', () => {
    console.log('WhatsApp Client Ready');
});

client.on('message', async (message) => {
    console.log('Mensaje recibido:', message.body);
    
    // Determinar origen (paciente vs usuario)
    const origin = await determineOrigin(message.from);
    
    // Enviar a backend LangGraph
    try {
        const response = await axios.post('http://localhost:8000/api/v1/integration/whatsapp-message', {
            from: message.from,
            message: message.body,
            origin: origin,
            timestamp: new Date().toISOString()
        });
        
        // Enviar respuesta de vuelta
        if (response.data.reply) {
            await message.reply(response.data.reply);
        }
    } catch (error) {
        console.error('Error al procesar mensaje:', error);
        await message.reply('Disculpa, hubo un error al procesar tu mensaje.');
    }
});

// Endpoint para enviar mensajes (llamado por backend)
app.post('/send-message', async (req, res) => {
    const { to, message } = req.body;
    
    try {
        const chat = await client.getChatById(to);
        await chat.sendMessage(message);
        res.json({ ok: true });
    } catch (error) {
        res.status(500).json({ ok: false, error: error.message });
    }
});

// Iniciar cliente
client.initialize();

// Iniciar servidor
app.listen(3000, () => {
    console.log('WhatsApp service running on port 3000');
});
```

**Endpoints Backend Python:**

```python
# backend/api/routes/whatsapp_integration.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/integration", tags=["WhatsApp"])


class WhatsAppIncomingMessage(BaseModel):
    """Mensaje entrante de WhatsApp"""
    from_number: str  # Renombrado de 'from' (palabra reservada)
    message: str
    origin: str  # 'whatsapp_paciente' o 'whatsapp_user'
    timestamp: str


class WhatsAppOutgoingMessage(BaseModel):
    """Mensaje saliente a WhatsApp"""
    to: str
    message: str


@router.post("/whatsapp-message")
async def handle_whatsapp_message(
    msg: WhatsAppIncomingMessage,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """
    Recibe mensaje de WhatsApp desde Node.js service.
    Procesa con LangGraph y retorna respuesta.
    """
    from backend.agents.graph import run_agent
    
    # Determinar user_id basado en número de teléfono
    # TODO: Implementar lookup de usuario por teléfono
    user_id = lookup_user_by_phone(msg.from_number)
    
    # Generar thread_id
    thread_id = generate_thread_id(user_id, msg.origin, str(uuid.uuid4()))
    
    # Invocar agente
    result = await run_agent(
        user_query=msg.message,
        user_id=user_id,
        user_role="Paciente" if msg.origin == "whatsapp_paciente" else "Podologo",
        session_id=thread_id
    )
    
    # Guardar transcripción
    save_transcript(
        user_id=user_id,
        origin=msg.origin,
        user_text=msg.message,
        assistant_text=result.get("response_text"),
        thread_id=thread_id
    )
    
    return {
        "reply": result.get("response_text"),
        "thread_id": thread_id
    }


@router.post("/send-whatsapp")
async def send_whatsapp_message(
    msg: WhatsAppOutgoingMessage,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """
    Envía mensaje a WhatsApp vía Node.js service.
    Usado por nodos del grafo (WhatsApp Sender Node).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:3000/send-message",
            json={"to": msg.to, "message": msg.message},
            timeout=10.0
        )
        response.raise_for_status()
    
    return {"ok": True}
```

#### Opción B: Twilio API (Producción)

Para ambiente de producción, usar Twilio API en lugar de WhatsApp Web.js:

```python
# backend/api/routes/twilio_integration.py
from twilio.rest import Client
from fastapi import APIRouter, Request

router = APIRouter(prefix="/twilio", tags=["Twilio"])

twilio_client = Client(account_sid, auth_token)


@router.post("/webhook")
async def twilio_webhook(request: Request):
    """Recibe webhooks de Twilio para mensajes entrantes."""
    form_data = await request.form()
    
    from_number = form_data.get("From")
    message_body = form_data.get("Body")
    
    # Procesar con LangGraph
    result = await process_whatsapp_message(from_number, message_body)
    
    # Twilio espera TwiML response
    return Response(
        content=f"<Response><Message>{result['reply']}</Message></Response>",
        media_type="application/xml"
    )


def send_whatsapp_via_twilio(to: str, message: str):
    """Envía mensaje vía Twilio API."""
    message = twilio_client.messages.create(
        from_='whatsapp:+14155238886',  # Número de Twilio
        body=message,
        to=f'whatsapp:{to}'
    )
    return message.sid
```

### 5.2 Tabla de Decisión: WhatsApp Web.js vs Twilio

| Criterio | WhatsApp Web.js | Twilio API |
|----------|-----------------|------------|
| **Costo** | ✅ Gratis | ❌ $0.005/mensaje |
| **Estabilidad** | ⚠️ Requiere sesión activa | ✅ Altamente confiable |
| **Escalabilidad** | ❌ Limitado (1 sesión) | ✅ Ilimitado |
| **Desarrollo** | ✅ Ideal | ❌ Requiere cuenta |
| **Producción** | ❌ No recomendado | ✅ Recomendado |
| **Configuración** | ⚠️ Requiere QR scan | ✅ API key |

**Recomendación:**
- **Desarrollo:** WhatsApp Web.js (gratis, rápido de probar)
- **Producción:** Twilio API (confiable, escalable)

---

## 6. Actualización de AgentState

### 6.1 Estado Propuesto Completo

```python
# backend/agents/state.py
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timezone

class OriginType(str, Enum):
    """Origen de la conversación"""
    WHATSAPP_PACIENTE = "whatsapp_paciente"
    WHATSAPP_USER = "whatsapp_user"
    WEBAPP = "webapp"
    WEBSOCKET = "websocket"


class AgentState(TypedDict, total=False):
    """Estado mejorado con memoria y concurrencia."""
    
    # ========== Identificación y Origen ==========
    user_id: int                         # ID del usuario autenticado
    user_role: str                       # Rol: Admin, Podologo, Recepcion, Paciente
    origin: OriginType                   # Origen de la conversación
    
    # ========== Threading y Persistencia ==========
    thread_id: str                       # ID único para checkpointing (NUEVO)
    session_id: str                      # ID de sesión (legacy, deprecar?)
    conversation_id: str                 # ID de conversación (UUID persistente)
    
    # ========== Mensajes y Contexto ==========
    user_query: str                      # Consulta actual del usuario
    messages: List[Dict[str, str]]       # Historial de mensajes (NUEVO)
    # Formato: [{"role": "user"|"assistant"|"system", "content": "..."}]
    
    # ========== Memoria ==========
    memory_context: Dict[str, Any]       # Contexto recuperado de memoria semántica (NUEVO)
    # Formato: {"similar_conversations": [...], "medical_knowledge": [...]}
    
    # ========== Clasificación de Intención ==========
    intent: IntentType                   # Tipo de intención detectada
    intent_confidence: float             # Confianza (0.0 a 1.0)
    entities_extracted: Dict[str, Any]   # Entidades extraídas
    
    # ========== Flujo de Trabajo ==========
    current_node: str                    # Nodo actual en ejecución (NUEVO)
    node_path: List[str]                 # Nodos visitados
    pending_actions: List[Dict[str, Any]]  # Acciones pendientes (NUEVO)
    # Formato: [{"type": "consent", "data": {...}, "resolved": False}]
    
    # ========== Generación SQL ==========
    target_database: DatabaseTarget      # BD objetivo
    sql_query: SQLQuery                  # Query generada
    sql_is_valid: bool                   # ¿Pasó validación?
    sql_validation_errors: List[str]     # Errores de validación
    
    # ========== Ejecución ==========
    execution_result: ExecutionResult    # Resultado de la query
    retry_count: int                     # Intentos de reintento
    max_retries: int                     # Máximo de reintentos
    
    # ========== Búsqueda Difusa ==========
    fuzzy_matches: List[FuzzyMatch]      # Coincidencias difusas encontradas
    fuzzy_suggestions: List[str]         # Sugerencias para el usuario
    
    # ========== Respuesta ==========
    response_text: str                   # Respuesta formateada para el usuario
    response_data: Dict[str, Any]        # Datos estructurados (para UI)
    response_sent: bool                  # ¿Respuesta ya enviada? (NUEVO)
    
    # ========== Manejo de Errores ==========
    error_type: ErrorType                # Tipo de error (si hay)
    error_internal_message: str          # Mensaje técnico (para logs)
    error_user_message: str              # Mensaje amigable (para usuario)
    error_suggestions: List[str]         # Sugerencias de acción
    
    # ========== Metadata y Logging ==========
    started_at: datetime                 # Timestamp inicio
    completed_at: datetime               # Timestamp fin
    logs: List[Dict[str, Any]]           # Logs internos para debugging


def create_initial_state(
    user_query: str,
    user_id: int,
    user_role: str,
    origin: OriginType,
    thread_id: str,
    conversation_id: Optional[str] = None
) -> AgentState:
    """Crea el estado inicial mejorado con threading."""
    import uuid
    
    return AgentState(
        # Identificación
        user_id=user_id,
        user_role=user_role,
        origin=origin,
        
        # Threading
        thread_id=thread_id,
        session_id=thread_id,  # Legacy compatibility
        conversation_id=conversation_id or str(uuid.uuid4()),
        
        # Mensajes
        user_query=user_query,
        messages=[{"role": "user", "content": user_query}],
        
        # Memoria
        memory_context={},
        
        # Defaults
        intent=IntentType.CLARIFICATION,
        intent_confidence=0.0,
        entities_extracted={},
        
        current_node="",
        node_path=[],
        pending_actions=[],
        
        target_database=DatabaseTarget.CORE,
        sql_is_valid=False,
        sql_validation_errors=[],
        
        retry_count=0,
        max_retries=2,
        
        fuzzy_matches=[],
        fuzzy_suggestions=[],
        
        response_text="",
        response_data={},
        response_sent=False,
        
        error_type=ErrorType.NONE,
        error_internal_message="",
        error_user_message="",
        error_suggestions=[],
        
        started_at=datetime.now(timezone.utc),
        node_path=[],
        logs=[],
    )
```

---

## 7. Endpoints Requeridos/Modificados

### 7.1 Nuevos Endpoints

```python
# backend/api/routes/memory.py
router = APIRouter(prefix="/memory", tags=["Memory"])

@router.get("/conversation-history/{thread_id}")
async def get_conversation_history(
    thread_id: str,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """Recupera historial completo de una conversación."""
    # Usar checkpointer para obtener historial
    pass


@router.post("/search-similar")
async def search_similar_conversations(
    query: str,
    limit: int = 5,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """Busca conversaciones similares semánticamente."""
    semantic_memory = SemanticMemory(db)
    results = semantic_memory.search_similar_conversations(
        query_text=query,
        user_id=current_user.id_usuario,
        limit=limit
    )
    return results


@router.delete("/thread/{thread_id}")
async def delete_conversation_thread(
    thread_id: str,
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """Elimina un thread de conversación (GDPR compliance)."""
    # Eliminar checkpoints y memoria semántica
    pass


# backend/api/routes/whatsapp_integration.py
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp"])

@router.post("/incoming")
async def handle_incoming_whatsapp(msg: WhatsAppIncomingMessage):
    """Recibe mensaje de WhatsApp desde Node.js service."""
    pass


@router.post("/send")
async def send_whatsapp_message(msg: WhatsAppOutgoingMessage):
    """Envía mensaje a WhatsApp vía Node.js service."""
    pass


@router.get("/qr-code")
async def get_whatsapp_qr():
    """Obtiene QR code para autenticación de WhatsApp Web."""
    pass
```

### 7.2 Endpoints Modificados

```python
# backend/api/routes/chat.py
@router.post("")
async def chat(
    request: ChatRequest,
    current_user: SysUsuario = Depends(get_current_active_user),
):
    """Endpoint modificado con soporte para threading."""
    
    # Generar thread_id
    thread_id = generate_thread_id(
        user_id=current_user.id_usuario,
        origin="webapp",
        conversation_uuid=request.session_id or str(uuid.uuid4())
    )
    
    # Configuración con checkpointer
    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }
    
    # Invocar con config
    graph = get_compiled_graph()
    result = await graph.ainvoke(
        create_initial_state(
            user_query=request.message,
            user_id=current_user.id_usuario,
            user_role=current_user.rol,
            origin=OriginType.WEBAPP,
            thread_id=thread_id
        ),
        config=config
    )
    
    return ChatResponse(
        success=result.get("success"),
        message=result.get("response_text"),
        thread_id=thread_id,  # ✅ Retornar para continuidad
        # ... rest ...
    )
```

---

## 8. Plan de Implementación por Fases

### Fase 1: Memoria Episódica (Checkpointing) ⏱️ 1 semana

**Objetivo:** Habilitar persistencia de estado entre turnos de conversación.

**Tareas:**
1. ✅ Instalar/verificar `langgraph-checkpoint-postgres==3.0.1`
2. ✅ Crear tabla `auth.langgraph_checkpoints` (LangGraph lo hace automático)
3. ✅ Modificar `backend/agents/graph.py` para usar `PostgresSaver`
4. ✅ Actualizar `AgentState` con `thread_id` y `messages`
5. ✅ Modificar endpoints para pasar `config` con thread_id
6. ✅ Testing: Verificar continuidad multi-turno

**Criterios de Aceptación:**
```python
# Test: Conversación multi-turno
thread_id = "test_thread_123"

# Turno 1
result1 = await graph.ainvoke(
    {"user_query": "Quiero agendar una cita", ...},
    config={"configurable": {"thread_id": thread_id}}
)
# Sistema: "¿Para qué día?"

# Turno 2 (debe recordar contexto)
result2 = await graph.ainvoke(
    {"user_query": "Mañana a las 3pm", ...},
    config={"configurable": {"thread_id": thread_id}}
)
# Sistema: ✅ "Perfecto, agendando cita para mañana 3pm"
```

### Fase 2: Arquitectura de Subgrafos ⏱️ 2 semanas

**Objetivo:** Separar flujos por origen (Paciente vs Usuario Interno).

**Tareas:**
1. ✅ Crear `backend/agents/subgraphs/`
2. ✅ Implementar `whatsapp_paciente.py` con consent flow
3. ✅ Implementar `whatsapp_user.py` con permisos full
4. ✅ Crear root graph con routing por `origin`
5. ✅ Actualizar `AgentState` con `origin` field
6. ✅ Testing: Verificar routing correcto

**Criterios de Aceptación:**
- Mensaje de paciente → subgrafo paciente (requiere consent)
- Mensaje de usuario → subgrafo usuario (sin consent)
- Permisos diferenciados por subgrafo

### Fase 3: Memoria Semántica (Vector Store) ⏱️ 2 semanas

**Objetivo:** Habilitar recuperación de contexto histórico relevante.

**Tareas:**
1. ✅ Instalar pgvector extension en PostgreSQL
2. ✅ Crear tablas `conversation_memory` y `medical_knowledge`
3. ✅ Implementar `backend/agents/memory/semantic_memory.py`
4. ✅ Crear nodo `retrieve_semantic_context`
5. ✅ Integrar nodo en subgrafos
6. ✅ Poblar vector store con datos de prueba
7. ✅ Testing: Verificar recuperación relevante

**Criterios de Aceptación:**
```python
# Test: Recuperación semántica
# Conversación pasada: "Juan Pérez tiene diabetes tipo 2"

# Nueva consulta
result = await graph.ainvoke({
    "user_query": "¿Qué pacientes diabéticos tenemos?",
    ...
})

# El sistema debe recuperar contexto de "Juan Pérez diabetes"
assert "Juan Pérez" in result["response_text"]
```

### Fase 4: Integración WhatsApp ⏱️ 1-2 semanas

**Objetivo:** Conectar WhatsApp Web.js al backend LangGraph.

**Tareas:**
1. ✅ Setup microservicio Node.js con WhatsApp Web.js
2. ✅ Implementar endpoints `/whatsapp/incoming` y `/whatsapp/send`
3. ✅ Crear `lookup_user_by_phone()` function
4. ✅ Implementar nodo `send_whatsapp_message`
5. ✅ Testing end-to-end con número de prueba

**Criterios de Aceptación:**
- Mensaje de WhatsApp → procesado por LangGraph → respuesta enviada
- Estado persistido con checkpointer
- Transcripción guardada en `voice_transcripts`

### Fase 5: Manejo de Concurrencia ⏱️ 1 semana

**Objetivo:** Asegurar aislamiento de estado entre conversaciones simultáneas.

**Tareas:**
1. ✅ Implementar `ThreadLockManager`
2. ✅ Agregar rate limiting por usuario
3. ✅ Testing de concurrencia (100 usuarios simultáneos)
4. ✅ Monitoring y alertas

**Criterios de Aceptación:**
```python
# Test: 100 usuarios simultáneos
async def test_concurrency():
    tasks = [
        invoke_agent(user_id=i, query=f"Query {i}")
        for i in range(100)
    ]
    results = await asyncio.gather(*tasks)
    
    # Verificar que no hay cruce de estados
    for i, result in enumerate(results):
        assert f"Query {i}" in result["logs"]
```

### Fase 6: Memoria de Largo Plazo (Opcional) ⏱️ 1 semana

**Objetivo:** Aprender patrones de uso y preferencias.

**Tareas:**
1. ✅ Crear tabla `user_behavior_patterns`
2. ✅ Implementar tracking de patrones frecuentes
3. ✅ Crear endpoint de análisis de patrones
4. ✅ Sugerencias proactivas basadas en patrones

---

## 9. Métricas y Monitoreo

### 9.1 Métricas Clave

```python
# backend/agents/monitoring.py
from prometheus_client import Counter, Histogram, Gauge

# Checkpointer metrics
checkpoint_saves = Counter('langgraph_checkpoint_saves_total', 'Total checkpoints saved')
checkpoint_loads = Counter('langgraph_checkpoint_loads_total', 'Total checkpoints loaded')

# Memory metrics
semantic_searches = Counter('semantic_memory_searches_total', 'Total semantic searches')
semantic_search_latency = Histogram('semantic_memory_search_seconds', 'Semantic search latency')

# Concurrency metrics
active_threads = Gauge('langgraph_active_threads', 'Number of active conversation threads')
thread_lock_wait_time = Histogram('thread_lock_wait_seconds', 'Time waiting for thread lock')

# Origin metrics
messages_by_origin = Counter('messages_by_origin_total', 'Messages by origin', ['origin'])
```

### 9.2 Dashboards Grafana

**Dashboard 1: Memoria**
- Checkpoints creados/hora
- Latencia de semantic search
- Hit rate de memoria semántica

**Dashboard 2: Concurrencia**
- Threads activos
- Tiempo de espera de locks
- Mensajes por origen (WhatsApp vs WebApp)

---

## 10. Riesgos y Mitigación

### 10.1 Riesgos Técnicos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Checkpoints crecen sin control | Alta | Alto | Implementar retention policy (30 días) |
| Vector store lento en búsquedas | Media | Medio | Usar índices IVFFLAT, limitar resultados |
| WhatsApp Web.js inestable | Alta | Alto | Usar Twilio en producción |
| Race conditions en concurrencia | Media | Alto | Implementar locks + testing exhaustivo |
| Memoria semántica recupera contexto irrelevante | Media | Medio | Ajustar threshold de similitud |

### 10.2 Riesgos de Negocio

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Usuarios rechazan WhatsApp como canal | Baja | Alto | Ofrecer múltiples canales |
| Costo de almacenamiento de memoria | Media | Medio | Retention policies + compresión |
| GDPR: derecho al olvido | Alta | Alto | Implementar endpoints de eliminación |

---

## 11. Preguntas Pendientes para el Equipo

### 11.1 Decisiones de Arquitectura

1. **¿Usamos pgvector o ChromaDB para memoria semántica?**
   - Recomendación: pgvector (menor latencia, misma BD)
   
2. **¿Cuánto tiempo mantenemos checkpoints?**
   - Propuesta: 30 días para usuarios activos, 7 días para inactivos
   
3. **¿Implementamos memoria semántica desde el inicio o en fase posterior?**
   - Propuesta: Fase 3 (después de checkpointing y subgrafos)

### 11.2 Decisiones de Producto

1. **¿Qué mensajes de consent mostramos a pacientes?**
   - Necesitamos texto legal aprobado
   
2. **¿Permitimos que pacientes agenden citas directamente o solo solicitan?**
   - Impacta diseño de subgrafo paciente
   
3. **¿Qué información puede ver un paciente en WhatsApp?**
   - Solo sus citas o también historial médico?

---

## 12. Recursos y Referencias

### 12.1 Documentación Oficial

- **LangGraph Checkpointing:** https://docs.langchain.com/oss/python/langgraph/persistence
- **LangGraph Subgraphs:** https://docs.langchain.com/oss/javascript/langgraph/use-subgraphs
- **PostgreSQL pgvector:** https://github.com/pgvector/pgvector
- **WhatsApp Web.js:** https://docs.wwebjs.dev/

### 12.2 Retroalimentación Oficial Recibida

**Puntos Validados:**
✅ Arquitectura de subgrafos por origen  
✅ Memoria episódica con checkpoints  
✅ Memoria semántica con vector store  
✅ Desacoplamiento de generación y envío  

**Recomendaciones Adicionales:**
- Definir esquema de State concreto ✅ (ver sección 6.1)
- Especificar políticas de concurrencia ✅ (ver sección 4)
- Usar ABAC para control de acceso ⚠️ (pendiente diseñar)
- Namespacing de memoria para evitar fugas ✅ (thread_id único)

---

## 13. Conclusiones y Próximos Pasos

### 13.1 Resumen

Este análisis identifica **4 gaps críticos** en la arquitectura actual:

1. ❌ **NO hay checkpointer** - memoria episódica inexistente
2. ❌ **NO hay subgrafos** - flujos monolíticos no especializados
3. ❌ **NO hay memoria semántica** - sin recuperación de contexto histórico
4. ❌ **NO hay manejo de concurrencia** - riesgo de cruce de estados

### 13.2 Ruta Crítica (MVP)

**Para tener un sistema funcional mínimo:**

1. **Fase 1: Checkpointing** (1 semana) - CRÍTICO
2. **Fase 2: Subgrafos** (2 semanas) - CRÍTICO
3. **Fase 4: WhatsApp** (1 semana) - CRÍTICO

**Total MVP: 4 semanas**

Fases 3 (memoria semántica), 5 (concurrencia avanzada) y 6 (largo plazo) pueden implementarse después del MVP.

### 13.3 Próximos Pasos Inmediatos

1. **Revisión con stakeholders** - Aprobar plan y fases
2. **Inicio Fase 1** - Implementar checkpointing
3. **Setup WhatsApp dev environment** - Preparar Node.js service
4. **Definir textos de consent** - Legal/producto

---

**Documento preparado por:** Equipo de Desarrollo  
**Fecha:** 11 de Diciembre, 2025  
**Versión:** 1.0 - Análisis Completo  
**Estado:** ✅ Listo para revisión y aprobación
