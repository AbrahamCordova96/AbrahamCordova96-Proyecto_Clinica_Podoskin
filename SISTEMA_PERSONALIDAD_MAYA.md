# 🎭 Sistema de Personalidad Maya - Integración

**Fecha:** 14 de Diciembre de 2024  
**Versión:** 1.0

---

## 📋 Resumen

Se ha integrado el **Sistema de Personalidad Maya** al chatbot de PodoSkin, basado en el sistema de personalidad de proyectos anteriores. Maya es la asistente virtual con personalidad definida, cálida, irónica y profesional.

---

## ✨ ¿Qué es Maya?

**Maya** (abreviatura de **Mayéutica** - método socrático) es la asistente virtual de PodoSkin con:

### Características de Personalidad

- ✅ **Segura** - Afirma con convicción, nunca "creo que..."
- ✅ **Cálida** - Amable pero directa, sin rodeos innecesarios
- ✅ **Irónica** - Comentarios ingeniosos y humor sutil
- ✅ **Curiosa** - Pregunta para entender mejor (Mayéutica)
- ✅ **Honesta** - Si no sabe algo, lo dice con confianza
- ✅ **Proactiva** - Sugiere antes de que le pidan

### Forma de Hablar

- **Español mexicano natural** ("mira", "oye", "fíjate")
- Nunca robótica ("como IA no puedo..." ❌)
- Emojis con moderación
- Respuestas con ritmo natural

---

## 🔧 Integración Técnica

### Archivos Creados

#### `backend/agents/maya_personality.py`

Módulo principal que define:

```python
# System prompt principal de Maya
MAYA_SYSTEM_PROMPT  # Personalidad completa

# Prompts contextuales
MAYA_GREETING_KNOWN_USER  # Para usuarios conocidos
MAYA_GREETING_NEW_USER    # Para usuarios nuevos
MAYA_ERROR_RECOVERY       # Para recuperación de errores
MAYA_OUT_OF_SCOPE        # Para consultas fuera de alcance

# Funciones principales
get_maya_system_prompt()  # Construye prompt con contexto
get_maya_greeting_prompt()  # Saludos personalizados
get_maya_error_prompt()    # Manejo de errores
get_maya_out_of_scope_prompt()  # Fuera de alcance
enhance_prompt_with_maya_personality()  # Mejora prompts técnicos
```

### Archivos Modificados

#### `backend/agents/nodes/classify_intent_node.py`

- ✅ Importa `enhance_prompt_with_maya_personality`
- ✅ Usa personalidad de Maya en clasificación de intenciones
- ✅ Prompt mejorado con personalidad

```python
# Antes
system=CLASSIFICATION_SYSTEM_PROMPT

# Después
enhanced_system_prompt = enhance_prompt_with_maya_personality(
    CLASSIFICATION_SYSTEM_PROMPT_BASE,
    user_name=user_name,
    user_role=user_role
)
system=enhanced_system_prompt
```

#### `backend/agents/nodes/llm_response_node.py`

- ✅ Importa todas las funciones de personalidad de Maya
- ✅ Saludos con personalidad de Maya
- ✅ Manejo de errores con estilo de Maya
- ✅ Respuestas fuera de alcance con personalidad
- ✅ Formateo de resultados con system prompt completo

```python
# Saludos personalizados por hora del día
def _get_greeting_response(query: str) -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "¡Buenos días! Soy Maya..."

# Errores con humor de Maya
def _get_clarification_response(state: AgentState) -> str:
    return "🤔 Hmm, creo que no te entendí bien. ¿Podrías decirlo 
            de otra forma? Y sé específico, que leer mentes todavía 
            no me sale, jaja."

# Formateo con personalidad completa
def _format_with_llm(state: AgentState, result: ExecutionResult) -> str:
    system_prompt = get_maya_system_prompt(
        user_name=user_name,
        user_role=user_role
    )
    system_prompt += "\n\n" + RESPONSE_SYSTEM_PROMPT_BASE
```

---

## 💬 Ejemplos de Personalidad

### Antes (Sin Personalidad)

```
Usuario: "Hola"
Bot: "Hola. ¿En qué puedo ayudarte?"

Usuario: "Cuántos pacientes hay"
Bot: "Hay 234 pacientes registrados."

Usuario: "¿Qué clima hay?"
Bot: "Esa consulta está fuera de mi especialidad."
```

### Después (Con Maya)

```
Usuario: "Hola"
Maya: "¡Buenos días! Soy Maya, tu asistente en PodoSkin. ¿En qué te ayudo hoy?"

Usuario: "Cuántos pacientes hay"
Maya: "Mira, tienes 234 pacientes registrados. ¿Quieres ver alguno en específico o necesitas estadísticas?"

Usuario: "¿Qué clima hay?"
Maya: "Mmm, tu pregunta no está relacionada con la clínica, ¿verdad? Pero si tienes algo de la clínica, ahí sí te echo la mano sin problema."
```

### Errores con Personalidad

```
Usuario: "buscar paciente xyz"
Maya: "Ups, parece que malentendí. ¿Podrías ser más específico con el nombre? Y échame la mano siendo claro, que leer mentes todavía no me sale, jaja."
```

---

## 🎯 Casos de Uso

### 1. Saludos Contextuales

Si Maya conoce al usuario:

```python
prompt = get_maya_system_prompt(
    user_name="Dr. Santiago Ornelas",
    user_role="Podologo",
    is_known_user=True,
    context={
        "citas_hoy": 5,
        "citas_pendientes": 2
    }
)

# Maya saluda:
# "¡Qué tal, Dr. Ornelas! Tienes 5 citas hoy y 2 pendientes. 
#  ¿Empezamos por revisar la agenda?"
```

### 2. Mejora de Prompts Técnicos

```python
# Prompt técnico sin personalidad
technical_prompt = "Clasifica la intención del usuario..."

# Mejorado con Maya
enhanced = enhance_prompt_with_maya_personality(
    technical_prompt,
    user_name="María",
    user_role="Admin"
)

# Resultado: Prompt técnico + reglas de personalidad Maya
```

### 3. Manejo de Errores

```python
# Automáticamente usa personalidad de Maya
error_prompt = get_maya_error_prompt()

# Respuesta con humor e ironía:
# "Hmm, creo que no te entendí bien. ¿Podrías decirlo de otra forma?
#  Y sé específico, que leer mentes todavía no me sale, jaja."
```

---

## 🔄 Flujo de Integración

```
1. Usuario envía mensaje
         ↓
2. Middleware (PromptController, Guardrails)
         ↓
3. classify_intent_node
   └─ Usa enhance_prompt_with_maya_personality()
   └─ Claude clasifica CON personalidad Maya
         ↓
4. execute_sql / generate_response
   └─ Usa get_maya_system_prompt()
   └─ Claude responde CON personalidad Maya
         ↓
5. Respuesta al usuario
   └─ Tono natural, cálido, irónico
   └─ Español mexicano natural
   └─ Proactiva y útil
```

---

## 📊 Comparación: Antes vs Después

| Aspecto | Antes | Después (Maya) |
|---------|-------|----------------|
| **Tono** | Robótico, técnico | Natural, cálido |
| **Lenguaje** | Formal | Español mexicano |
| **Errores** | Disculpas formales | Humor irónico |
| **Saludos** | Genéricos | Contextuales |
| **Proactividad** | Pasiva | Sugiere acciones |
| **Personalidad** | Ninguna | Definida y consistente |

---

## 🚀 Uso en Código

### Opción 1: System Prompt Completo

```python
from backend.agents.maya_personality import get_maya_system_prompt

system_prompt = get_maya_system_prompt(
    user_name="Dr. Santiago",
    user_role="Podologo",
    is_known_user=True,
    context={
        "citas_hoy": 3,
        "ultima_interaccion": "Preguntó por estadísticas"
    }
)

# Usar en llamada a LLM
response = client.messages.create(
    model="claude-3-5-haiku",
    system=system_prompt,
    messages=[...]
)
```

### Opción 2: Mejorar Prompt Técnico

```python
from backend.agents.maya_personality import enhance_prompt_with_maya_personality

technical_prompt = "Eres un clasificador de intenciones..."

enhanced = enhance_prompt_with_maya_personality(
    technical_prompt,
    user_name="María",
    user_role="Admin"
)

# Resultado: Prompt técnico + personalidad Maya
```

### Opción 3: Prompts Específicos

```python
from backend.agents.maya_personality import (
    get_maya_greeting_prompt,
    get_maya_error_prompt,
    get_maya_out_of_scope_prompt
)

# Para saludos
greeting = get_maya_greeting_prompt("Santiago", is_known_user=True)

# Para errores
error_handling = get_maya_error_prompt()

# Para fuera de alcance
out_of_scope = get_maya_out_of_scope_prompt()
```

---

## ✅ Beneficios

1. **Consistencia** - Personalidad uniforme en todas las respuestas
2. **Naturalidad** - Conversación más humana y fluida
3. **Engagement** - Usuarios más cómodos interactuando
4. **Profesionalismo** - Mantiene tono apropiado para clínica
5. **Diferenciación** - Maya no es "otro chatbot genérico"
6. **Extensibilidad** - Fácil agregar más contextos

---

## 📝 Notas de Implementación

### Contexto de Usuario

El sistema está preparado para contexto pero por ahora usa valores por defecto:

```python
# Actualmente
user_name = state.get("user_name")  # Puede ser None
is_known_user = False  # Por defecto

# Futuro: Integrar con sistema de sesiones
# user_name = session_service.get_user_name()
# is_known_user = session_service.has_previous_interactions()
```

### Temperatura de LLM

- **Clasificación**: temperatura=0.0 (determinístico)
- **Respuestas**: temperatura=0.3 (natural pero consistente)

### Compatibilidad

- ✅ Compatible con middleware existente
- ✅ Compatible con guardrails
- ✅ Compatible con observabilidad
- ✅ No rompe funcionalidad existente

---

## 🔮 Próximos Pasos

1. **Integrar Sistema de Sesiones**
   - Detectar si usuario es conocido
   - Recuperar contexto de interacciones previas

2. **Ampliar Contexto**
   - Citas pendientes del usuario
   - Adeudos o notificaciones
   - Preferencias guardadas

3. **Personalización por Rol**
   - Admin: Información más técnica
   - Podólogo: Enfoque clínico
   - Recepción: Enfoque administrativo

4. **A/B Testing**
   - Medir engagement con vs sin personalidad
   - Ajustar tono según feedback

---

## 📚 Referencias

- Código fuente: `backend/agents/maya_personality.py`
- Integración: `backend/agents/nodes/classify_intent_node.py`
- Integración: `backend/agents/nodes/llm_response_node.py`
- Documentación principal: `ARQUITECTURA_CHATBOT_NATURAL.md`

---

**Implementado por:** Sistema de IA Copilot  
**Fecha:** 14 de Diciembre de 2024  
**Basado en:** Sistema de personalidad de proyectos anteriores del usuario
