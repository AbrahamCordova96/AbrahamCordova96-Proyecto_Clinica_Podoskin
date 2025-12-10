# =============================================================================
# backend/api/core/config.py
# Configuración central de la API (variables de entorno, secrets, etc.)
# =============================================================================
# Este archivo centraliza TODA la configuración de la aplicación.
# Usa Pydantic Settings para validar que las variables de entorno existan.
#
# ANALOGÍA: Es como el "panel de control" de un edificio. Todos los
# interruptores importantes están aquí en un solo lugar.
# =============================================================================

from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings

# Calcular ruta absoluta al .env (relativa a este archivo)
_THIS_DIR = Path(__file__).resolve().parent  # backend/api/core/
_BACKEND_DIR = _THIS_DIR.parent.parent       # backend/
_ENV_FILE = _BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """
    Configuración de la aplicación.
    
    Pydantic Settings automáticamente lee variables de entorno.
    Si una variable no tiene default y no está en el entorno, lanza error.
    """
    
    # ========== Base de Datos ==========
    # URLs de conexión para cada base de datos
    # Formato: postgresql://usuario:password@host:puerto/nombre_bd
    AUTH_DB_URL: str = "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db"
    CORE_DB_URL: str = "postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db"
    OPS_DB_URL: str = "postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db"
    
    # ========== JWT (JSON Web Tokens) ==========
    # El SECRET_KEY es como la "llave maestra" para firmar tokens.
    # NUNCA compartas esto públicamente. Cámbialo en producción.
    JWT_SECRET_KEY: str = "tu-super-secreto-cambiar-en-produccion-1234567890"
    
    # Algoritmo de encriptación para JWT
    JWT_ALGORITHM: str = "HS256"
    
    # Tiempo de vida del token en minutos (8 horas por defecto)
    # Después de este tiempo, el usuario debe volver a hacer login
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    # ========== Aplicación ==========
    APP_NAME: str = "PodoSkin API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # ========== CORS (Cross-Origin Resource Sharing) ==========
    # Orígenes permitidos para hacer requests a la API
    # En producción, limitar a los dominios específicos del frontend
    CORS_ORIGINS: str = "*"
    
    # ========== LangGraph Agent - LLM Configuration ==========
    # Anthropic Claude Haiku 3.5 para el agente conversacional
    ANTHROPIC_API_KEY: str = ""  # REQUERIDO: Configurar en .env
    CLAUDE_MODEL: str = "claude-3-5-haiku-20241022"  # Claude Haiku 3.5
    CLAUDE_MAX_TOKENS: int = 4096
    CLAUDE_TEMPERATURE: float = 0.1  # Bajo para respuestas consistentes
    
    # ========== LangGraph Agent - Embeddings Configuration ==========
    # Modelo local all-MiniLM-L6-v2 (Sentence Transformers)
    # CPU-friendly, no requiere GPU
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384  # Dimensión de salida del modelo
    EMBEDDING_DEVICE: str = "cpu"   # Usar CPU (cambiar a "cuda" si hay GPU)
    
    # ========== LangGraph Agent - ChromaDB Configuration ==========
    # Almacén de vectores para embeddings de esquema
    CHROMA_PERSIST_DIR: str = "data/chroma_db"
    CHROMA_COLLECTION_NAME: str = "podoskin_schema"
    
    # ========== LangGraph Agent - Behavior Configuration ==========
    # Configuración del comportamiento del agente
    AGENT_MAX_RETRIES: int = 2           # Reintentos en caso de error
    AGENT_TIMEOUT_SECONDS: int = 30      # Timeout por consulta
    AGENT_MAX_RESULTS: int = 100         # Máximo de filas a devolver
    AGENT_FUZZY_THRESHOLD: float = 0.6   # Umbral de similitud para búsqueda difusa
    
    # ========== LangGraph Agent - Logging ==========
    AGENT_LOG_LEVEL: str = "INFO"        # DEBUG, INFO, WARNING, ERROR
    AGENT_LOG_QUERIES: bool = True       # Loguear queries SQL generadas
    AGENT_LOG_RESPONSES: bool = False    # Loguear respuestas (cuidado con PII)
    
    # ========== Email Notifications ==========
    # SMTP configuration for sending email notifications
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # Email address to send from (configure in .env)
    SMTP_PASSWORD: str = ""  # Email password or app-specific password (configure in .env)
    FROM_EMAIL: str = "noreply@podoskin.com"
    
    class Config:
        # Archivo .env - ruta absoluta calculada arriba
        env_file = str(_ENV_FILE)
        env_file_encoding = "utf-8"
        # Si hay variables extra en .env que no están definidas aquí, ignorarlas
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """
    Obtiene la configuración de la aplicación.
    
    @lru_cache() significa que solo se crea UNA instancia de Settings.
    Esto evita leer el archivo .env múltiples veces (optimización).
    
    Uso:
        from backend.api.core.config import get_settings
        settings = get_settings()
        print(settings.JWT_SECRET_KEY)
    """
    return Settings()
