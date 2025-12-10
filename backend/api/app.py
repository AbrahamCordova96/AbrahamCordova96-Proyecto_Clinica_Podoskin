# =============================================================================
# backend/api/app.py
# Aplicación principal FastAPI
# =============================================================================
# Este es el punto de entrada de la API. Aquí se configuran:
#   - La aplicación FastAPI
#   - CORS (Cross-Origin Resource Sharing)
#   - Los routers de cada módulo
#   - Middleware global
#   - Logging mejorado
#   - Rate limiting (protección contra abuso)
#
# PARA EJECUTAR LA API:
# cd backend
# uvicorn api.app:app --reload --host 0.0.0.0 --port 8000 --log-config backend/config/logging_config.py
# =============================================================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.api.core.config import get_settings
from backend.config.logging_config import setup_logging

# Configurar logging mejorado
setup_logging()
from backend.api.routes import auth
from backend.api.routes import pacientes
from backend.api.routes import citas
from backend.api.routes import tratamientos
from backend.api.routes import evoluciones
from backend.api.routes import evidencias
from backend.api.routes import servicios
from backend.api.routes import prospectos
from backend.api.routes import podologos
from backend.api.routes import usuarios
from backend.api.routes import audit
from backend.api.routes import examples_schemas
from backend.api.routes import finance
from backend.api.routes import historial_detalles
from backend.api.routes import chat


# =============================================================================
# CONFIGURACIÓN
# =============================================================================
settings = get_settings()

# =============================================================================
# RATE LIMITING
# =============================================================================
# Configure rate limiter to prevent API abuse
# Uses IP address as identifier
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# =============================================================================
# APLICACIÓN FASTAPI
# =============================================================================
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## 🦶 API de PodoSkin
    
    Sistema de gestión clínica podológica.
    
    ### Módulos disponibles:
    - **Autenticación**: Login, perfil, cambio de contraseña
    - **Pacientes**: CRUD de expedientes clínicos
    - **Citas**: Gestión de agenda
    - **Tratamientos**: Seguimiento de tratamientos
    - **Evoluciones**: Notas clínicas SOAP
    - **Evidencias**: Fotografías clínicas
    - **Servicios**: Catálogo de servicios
    - **Prospectos**: Leads y potenciales pacientes
    - **Podólogos**: Staff clínico
    - **Usuarios**: Gestión de accesos
    - **Auditoría**: Logs de cambios
    
    ### Autenticación:
    1. Hacer POST a `/auth/login` con username y password
    2. Copiar el `access_token` de la respuesta
    3. Usar el token en el header: `Authorization: Bearer {token}`
    
    ### Rate Limiting:
    - Default: 200 requests/minute per IP
    - Auth endpoints: 5 requests/minute per IP
    - Search endpoints: 30 requests/minute per IP
    """,
    docs_url="/docs",      # Swagger UI en /docs
    redoc_url="/redoc",    # ReDoc en /redoc
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# =============================================================================
# CORS (Cross-Origin Resource Sharing)
# =============================================================================
# Permite que el frontend (en otro dominio/puerto) haga requests a la API.
# En desarrollo usamos "*" (cualquier origen).
# En producción, limitar a los dominios específicos del frontend.

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ROUTERS
# =============================================================================
# Cada router agrupa endpoints por módulo.
# El prefix define la ruta base (ej: /auth/login, /pacientes/123)

# Autenticación
app.include_router(auth.router, prefix="/api/v1")

# Pacientes (CRUD + historial)
app.include_router(pacientes.router, prefix="/api/v1")

# Citas (agenda)
app.include_router(citas.router, prefix="/api/v1")

# Tratamientos (carpetas de problemas)
app.include_router(tratamientos.router, prefix="/api/v1")

# Evoluciones clínicas (notas SOAP)
app.include_router(evoluciones.router, prefix="/api/v1")

# Evidencias fotográficas
app.include_router(evidencias.router, prefix="/api/v1")

# Catálogo de servicios
app.include_router(servicios.router, prefix="/api/v1")

# Prospectos (leads)
app.include_router(prospectos.router, prefix="/api/v1")

# Podólogos (staff)
app.include_router(podologos.router, prefix="/api/v1")

# Usuarios del sistema
app.include_router(usuarios.router, prefix="/api/v1")

# Auditoría
app.include_router(audit.router, prefix="/api/v1")
# Ejemplos de schemas / endpoints de referencia
app.include_router(examples_schemas.router, prefix="/api/v1")
# Finanzas (pagos, transacciones, métodos de pago)
app.include_router(finance.router, prefix="/api/v1")
# Historial detalles (alergias, suplementos, antecedentes, conversaciones)
app.include_router(historial_detalles.router, prefix="/api/v1")
# Chat - Agente IA LangGraph
app.include_router(chat.router, prefix="/api/v1")


# =============================================================================
# HEALTH CHECK
# =============================================================================

@app.get("/", tags=["Health"])
async def root():
    """
    Endpoint de salud para verificar que la API está funcionando.
    
    Útil para:
    - Docker health checks
    - Monitoreo de uptime
    - Verificación rápida
    """
    return {
        "status": "online",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check detallado.
    
    Verifica:
    - Estado de la aplicación
    - Versión
    """
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": "development" if settings.DEBUG else "production"
    }
