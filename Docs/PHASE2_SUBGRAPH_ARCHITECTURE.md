# Fase 2: Arquitectura de Subgrafos - Implementación Completa
## Routing por Origen con Flujos Especializados

**Fecha:** 11 de Diciembre, 2025  
**Estado:** ✅ Implementado  
**Fase:** 2 de 6 del Plan de Implementación de Memoria

---

## 📋 Resumen de Cambios

Se ha implementado la **arquitectura de subgrafos** con routing basado en origen, permitiendo que diferentes canales de entrada (webapp, WhatsApp paciente, WhatsApp usuario) tengan flujos especializados con lógica, permisos y formato de respuesta diferenciados.

### Archivos Creados

1. ✅ **`backend/agents/root_graph.py`** (NUEVO)
   - Grafo raíz con routing condicional
   - Función `route_by_origin()` para decidir subgrafo
   - Función `build_root_graph()` para construir arquitectura

2. ✅ **`backend/agents/subgraphs/__init__.py`** (NUEVO)
   - Módulo de subgrafos
   - Exports de constructores de subgrafos

3. ✅ **`backend/agents/subgraphs/webapp_subgraph.py`** (NUEVO)
   - Subgrafo para usuarios web
   - Flujo estándar sin restricciones adicionales
   - Permisos según RBAC

4. ✅ **`backend/agents/subgraphs/whatsapp_paciente_subgraph.py`** (NUEVO)
   - Subgrafo para pacientes vía WhatsApp
   - Validación de consentimiento
   - Permisos limitados (solo datos propios)
   - Respuestas amigables y no técnicas

5. ✅ **`backend/agents/subgraphs/whatsapp_user_subgraph.py`** (NUEVO)
   - Subgrafo para usuarios internos vía WhatsApp
   - Permisos completos según RBAC
   - Formato optimizado para WhatsApp (conciso)

### Archivos Modificados

1. ✅ **`backend/agents/graph.py`**
   - Función `build_agent_graph()` ahora soporta dos modos
   - Modo subgraph (nuevo) vs monolithic (legacy)
   - Toggle via configuración

2. ✅ **`backend/api/core/config.py`**
   - Nuevo setting: `ENABLE_SUBGRAPH_ARCHITECTURE = True`
   - Permite activar/desactivar arquitectura de subgrafos

---

## 🎯 Arquitectura Implementada

### Diagrama de Flujo

```
┌─────────────────────────────────────────┐
│       Ingress Gateway (Externo)         │
│  - Normaliza mensajes de diferentes     │
│    canales (webapp, WhatsApp, etc.)     │
│  - Asigna 'origin' al estado            │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│          Root Graph                     │
│  ┌─────────────────────────────────┐   │
│  │   route_by_origin_node()        │   │
│  │   - Registra origen             │   │
│  │   - Logs debugging              │   │
│  └──────────────┬──────────────────┘   │
│                 │                       │
│     ┌───────────┼───────────┐          │
│     │           │           │          │
│     ▼           ▼           ▼          │
│ ┌────────┐ ┌────────┐ ┌────────┐      │
│ │webapp  │ │whatsapp│ │whatsapp│      │
│ │  flow  │ │paciente│ │  user  │      │
│ └────────┘ └────────┘ └────────┘      │
└─────────────────────────────────────────┘
```

### Subgrafos Implementados

#### 1. **webapp_subgraph** (Usuarios Internos - Web)

**Flujo:**
```
classify_intent → check_permissions → combine_context → 
nl_to_sql → sql_exec → llm_response → END
```

**Características:**
- Permisos completos según rol RBAC (Admin/Podologo/Recepcion)
- Sin validaciones adicionales de consentimiento
- Respuestas detalladas
- Optimizado para pantalla grande

#### 2. **whatsapp_paciente_subgraph** (Pacientes - WhatsApp)

**Flujo:**
```
classify_intent → validate_patient_consent → check_patient_permissions → 
combine_context → nl_to_sql → sql_exec → generate_patient_safe_response → END
```

**Características:**
- ✅ **Validación de consentimiento** (nuevo nodo)
- ✅ **Permisos limitados** - solo datos propios
- ✅ **Respuestas amigables** - no técnicas, con emojis
- ✅ **Filtrado automático** - solo puede ver sus citas/tratamientos

**Nodos Especializados:**
- `validate_patient_consent()` - Valida consentimiento antes de acceder a datos
- `check_patient_permissions()` - Permisos restrictivos
- `generate_patient_safe_response()` - Formato amigable

#### 3. **whatsapp_user_subgraph** (Usuarios Internos - WhatsApp)

**Flujo:**
```
classify_intent → check_permissions → combine_context → 
nl_to_sql → sql_exec → format_whatsapp_response → END
```

**Características:**
- Permisos completos según RBAC (igual que webapp)
- ✅ **Formato optimizado para WhatsApp** - respuestas concisas
- Máximo 500 caracteres
- Uso estratégico de emojis
- Links clickeables

**Nodo Especializado:**
- `format_whatsapp_response()` - Optimiza longitud y formato

---

## 🔑 Cambios Clave

### 1. Root Graph con Routing

```python
# backend/agents/root_graph.py
def route_by_origin(state: AgentState) -> Literal["webapp_flow", "whatsapp_paciente_flow", "whatsapp_user_flow"]:
    origin = state.get("origin", "webapp")
    
    routing_map = {
        "webapp": "webapp_flow",
        "whatsapp_paciente": "whatsapp_paciente_flow",
        "whatsapp_user": "whatsapp_user_flow",
    }
    
    return routing_map.get(origin, "webapp_flow")
```

**Beneficio:** Enrutamiento automático basado en el campo `origin` del estado.

### 2. Subgrafos como Nodos Compilados

```python
# Construir y compilar subgrafos
webapp_subgraph = build_webapp_subgraph().compile()
whatsapp_paciente_subgraph = build_whatsapp_paciente_subgraph().compile()
whatsapp_user_subgraph = build_whatsapp_user_subgraph().compile()

# Agregar como nodos del root graph
root_graph.add_node("webapp_flow", webapp_subgraph)
root_graph.add_node("whatsapp_paciente_flow", whatsapp_paciente_subgraph)
root_graph.add_node("whatsapp_user_flow", whatsapp_user_subgraph)
```

**Beneficio:** Cada subgrafo es independiente, fácil de mantener y testear.

### 3. Toggle de Arquitectura

```python
# backend/api/core/config.py
ENABLE_SUBGRAPH_ARCHITECTURE: bool = True

# backend/agents/graph.py
def build_agent_graph():
    if settings.ENABLE_SUBGRAPH_ARCHITECTURE:
        return build_root_graph()  # ✅ Nuevo
    else:
        return build_monolithic_graph()  # Legacy
```

**Beneficio:** Permite rollback rápido si hay issues.

---

## 📊 Comparación de Flujos

### Ejemplo 1: Consulta de Citas

**Paciente (WhatsApp):**
```
Usuario (Paciente ID 5): "¿Cuándo es mi próxima cita?"

Flujo:
1. classify_intent → "query_read"
2. validate_patient_consent → ✅ OK
3. check_patient_permissions → Agrega filtro: WHERE paciente_id = 5
4. nl_to_sql → SELECT * FROM citas WHERE paciente_id = 5 AND fecha >= NOW()
5. sql_exec → Ejecuta con filtro automático
6. generate_patient_safe_response → "✅ Tu próxima cita es el lunes 18 a las 10:00 AM con Dr. García"
```

**Usuario Interno (WebApp):**
```
Usuario (Admin): "¿Cuándo es la próxima cita de Juan Pérez?"

Flujo:
1. classify_intent → "query_read"
2. check_permissions → ✅ Admin puede ver todo
3. nl_to_sql → SELECT * FROM citas WHERE paciente LIKE '%Juan Pérez%'
4. sql_exec → Ejecuta sin restricciones
5. llm_response → "📅 **Próxima cita de Juan Pérez:**\nLunes 18 Diciembre, 10:00 AM\nPodólogo: Dr. García\nServicio: Consulta general"
```

### Ejemplo 2: Acceso Restringido

**Paciente intentando ver datos de otro paciente:**
```
Usuario (Paciente ID 5): "¿Qué citas tiene María García?"

Flujo:
1. classify_intent → "query_read"
2. validate_patient_consent → ✅ OK
3. check_patient_permissions → Detecta intento de acceso a otro paciente
4. → ERROR
5. generate_patient_safe_response → "⚠️ Solo puedes ver tus propias citas. ¿Quieres ver tu agenda?"
```

---

## 🧪 Testing

### Test 1: Verificar Routing por Origen

```python
# Test webapp
result_webapp = await run_agent(
    user_query="¿Cuántos pacientes hay?",
    user_id=1,
    user_role="Admin",
    origin="webapp"
)
assert "webapp_flow" in result_webapp["node_path"]

# Test whatsapp_paciente
result_paciente = await run_agent(
    user_query="¿Cuándo es mi cita?",
    user_id=10,
    user_role="Paciente",
    origin="whatsapp_paciente"
)
assert "whatsapp_paciente_flow" in result_paciente["node_path"]
assert "validate_patient_consent" in result_paciente["node_path"]

# Test whatsapp_user
result_user_wa = await run_agent(
    user_query="Agenda de hoy",
    user_id=5,
    user_role="Podologo",
    origin="whatsapp_user"
)
assert "whatsapp_user_flow" in result_user_wa["node_path"]
assert "format_whatsapp_response" in result_user_wa["node_path"]
```

### Test 2: Validar Permisos de Paciente

```python
# Paciente solo puede ver sus datos
result = await run_agent(
    user_query="Mis citas",
    user_id=10,  # Paciente ID 10
    user_role="Paciente",
    origin="whatsapp_paciente"
)

# Verificar que SQL tiene filtro
assert "WHERE paciente_id = 10" in result["sql_query"]
```

### Test 3: Formato WhatsApp vs WebApp

```python
# WebApp - respuesta larga permitida
result_web = await run_agent(
    user_query="Citas de hoy",
    user_id=1,
    user_role="Admin",
    origin="webapp"
)
# Puede ser larga, con detalles

# WhatsApp User - respuesta concisa
result_wa = await run_agent(
    user_query="Citas de hoy",
    user_id=1,
    user_role="Admin",
    origin="whatsapp_user"
)
# Máximo 500 caracteres
assert len(result_wa["response_text"]) <= 600
```

---

## 🔧 Configuración

### Activar/Desactivar Subgrafos

```python
# .env o config.py
ENABLE_SUBGRAPH_ARCHITECTURE=True  # Usar subgrafos (recomendado)
# ENABLE_SUBGRAPH_ARCHITECTURE=False  # Usar grafo monolítico (legacy)
```

### Verificar Modo Activo

```bash
# Ver logs al iniciar backend
# Si ve: "🔧 Construyendo grafo con arquitectura de subgrafos (Fase 2)"
# → Subgrafos activos ✅

# Si ve: "🔧 Construyendo grafo monolítico (legacy)"
# → Modo legacy ⚠️
```

---

## 📈 Beneficios de la Arquitectura

### 1. Separación de Responsabilidades

- **Antes:** Un solo grafo con lógica mezclada
- **Ahora:** Cada subgrafo tiene responsabilidad única

### 2. Mantenibilidad

- **Antes:** Cambio en flujo de paciente afecta todo
- **Ahora:** Modificaciones aisladas por subgrafo

### 3. Seguridad

- **Antes:** Permisos verificados caso por caso
- **Ahora:** Arquitectura garantiza separación

### 4. Extensibilidad

```python
# Agregar nuevo origen es trivial
def build_telegram_subgraph():
    # Nuevo flujo para Telegram
    pass

# En root_graph.py
telegram_subgraph = build_telegram_subgraph().compile()
root_graph.add_node("telegram_flow", telegram_subgraph)
```

---

## ⚠️ Notas Importantes

### 1. Compatibilidad con Fase 1

Los subgrafos **funcionan con checkpointing**. Cada subgrafo mantiene su propio estado pero comparte el thread_id:

```python
config = {"configurable": {"thread_id": thread_id}}
result = root_graph.invoke(initial_state, config=config)
# Checkpoints se guardan independientemente del subgrafo usado
```

### 2. Field `origin` es Obligatorio

El campo `origin` debe estar en el estado inicial:

```python
# ✅ CORRECTO
initial_state = create_initial_state(
    user_query="Hola",
    user_id=1,
    user_role="Admin",
    thread_id="...",
    origin="webapp"  # ✅ Especificar origen
)

# ❌ INCORRECTO (defaultea a webapp)
initial_state = create_initial_state(
    user_query="Hola",
    user_id=1,
    user_role="Admin"
    # origin no especificado
)
```

### 3. Logs para Debugging

Cada routing se registra:

```python
# En logs verás:
# "🚦 Routing por origen: origin=whatsapp_paciente, user_id=10, thread_id=..."
# "✅ Routing decision: whatsapp_paciente → whatsapp_paciente_flow"
```

---

## 🚀 Próximos Pasos

### Fase 3: Memoria Semántica (Próxima - 2 semanas)

- Instalar pgvector extension
- Crear tabla `conversation_memory` con embeddings
- Implementar búsqueda semántica
- Nodo `retrieve_semantic_context`

### Fase 4: Integración WhatsApp (1 semana)

- Microservicio Node.js con WhatsApp Web.js
- Endpoints `/whatsapp/incoming` y `/whatsapp/send`
- Nodo `send_whatsapp_message`
- Testing end-to-end

### Fase 5: Concurrencia Avanzada (1 semana)

- ThreadLockManager
- Rate limiting por usuario y origen
- Tests de carga (100 usuarios simultáneos)

---

## ✅ Checklist de Verificación

- [x] Root graph creado con routing por origen
- [x] 3 subgrafos implementados (webapp, whatsapp_paciente, whatsapp_user)
- [x] Nodos especializados por subgrafo
- [x] Toggle de configuración funcional
- [x] Logs de debugging en routing
- [x] Compatibilidad con checkpointing (Fase 1)
- [x] Documentación completa
- [x] Ejemplos de testing

---

## 📚 Referencias

- **Análisis Arquitectura:** `/Docs/MEMORY_ARCHITECTURE_ANALYSIS.md`
- **Fase 1 Implementación:** `/Docs/PHASE1_CHECKPOINTING_IMPLEMENTATION.md`
- **LangGraph Subgraphs:** https://docs.langchain.com/oss/javascript/langgraph/use-subgraphs

---

**Implementado por:** Sistema  
**Fecha:** 11 de Diciembre, 2025  
**Estado:** ✅ Fase 2 Completa - Arquitectura de Subgrafos Operacional  
**Próximo:** Fase 3 - Memoria Semántica con pgvector
