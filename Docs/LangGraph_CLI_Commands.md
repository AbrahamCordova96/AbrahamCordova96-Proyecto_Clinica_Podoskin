# Guía LangGraph CLI - PodoSkin Agent

## Configuración Completada ✅

El proyecto ahora está configurado con LangGraph CLI siguiendo la documentación oficial.

### Archivo `langgraph.json` configurado con:

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": [
    ".",
    "anthropic"
  ],
  "graphs": {
    "podologia_agent": "./backend/agents/graph.py:graph"
  },
  "env": "./.env",
  "image_distro": "wolfi",
  "python_version": "3.11",
  "api_version": "0.3",
  "checkpointer": {
    "ttl": {
      "strategy": "delete",
      "sweep_interval_minutes": 60,
      "default_ttl": 43200
    }
  },
  "store": {
    "ttl": {
      "refresh_on_read": true,
      "sweep_interval_minutes": 60,
      "default_ttl": 10080
    }
  },
  "http": {
    "cors": {
      "allow_origins": ["*"],
      "allow_methods": ["GET", "POST", "PUT", "DELETE"],
      "allow_headers": ["*"],
      "allow_credentials": false
    }
  }
}
```

## Comandos CLI Disponibles

### Desarrollo Local
```powershell
# Iniciar servidor de desarrollo con hot reload
langgraph dev --port 2024 --no-browser

# Acceder a la documentación del API
# http://127.0.0.1:2024/docs

# Acceder a LangSmith Studio
# https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

### Construcción de Imágenes Docker
```powershell
# Construir imagen Docker del agente
langgraph build -t podoskin-agent:latest

# Generar Dockerfile personalizado
langgraph dockerfile -c langgraph.json Dockerfile

# Ejecutar con Docker
langgraph up --port 8000
```

### Comandos de Ayuda
```powershell
# Ver ayuda general
langgraph --help

# Ver opciones específicas
langgraph dev --help
langgraph build --help
langgraph up --help
```

## Configuraciones Destacadas

### TTL de Checkpoints
- **30 días** de retención de checkpoints
- Limpieza automática cada **60 minutos**

### TTL del Store  
- **7 días** de retención de datos del store
- Refresco automático en lectura habilitado

### Imagen Base
- **Wolfi Linux** (más segura y compacta)
- **Python 3.11**
- **API version 0.3**

### CORS
- Configurado para desarrollo con `allow_origins: ["*"]`
- Para producción, especificar dominios exactos

## URLs del Servidor

### Desarrollo Local (puerto 2024)
- **API Base**: `http://127.0.0.1:2024`
- **Documentación**: `http://127.0.0.1:2024/docs`
- **OpenAPI Schema**: `http://127.0.0.1:2024/openapi.json`
- **Studio UI**: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### Endpoints del Agente
- **Threads**: `http://127.0.0.1:2024/threads`
- **Runs**: `http://127.0.0.1:2024/threads/{thread_id}/runs`
- **Assistants**: `http://127.0.0.1:2024/assistants`

## Estado del Proyecto

✅ **LangGraph CLI instalado** con `langgraph-cli[inmem]`  
✅ **Configuración validada** según documentación oficial  
✅ **Grafo exportado** correctamente en `backend/agents/graph.py`  
✅ **Servidor funcionando** en desarrollo  
✅ **API documentada** y accesible  

## Próximos Pasos

1. **Producción**: Configurar LangSmith API key para deployment
2. **Autenticación**: Agregar `auth` configuration para producción
3. **Monitoring**: Configurar logging y métricas
4. **CI/CD**: Integrar `langgraph build` en pipeline

---
**Actualizado**: 9 de diciembre de 2025  
**Documentación**: https://docs.langchain.com/langsmith/cli