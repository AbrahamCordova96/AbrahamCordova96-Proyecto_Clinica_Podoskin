"""
Configuración del Checkpointer para Memoria Episódica
=====================================================

Implementa PostgresSaver para persistencia de estado del grafo LangGraph.
Permite que las conversaciones multi-turno mantengan contexto entre invocaciones.

Autor: Sistema
Fecha: 11 de Diciembre, 2025
"""

import logging
from typing import Optional
from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection

logger = logging.getLogger(__name__)


# =============================================================================
# CHECKPOINTER SINGLETON
# =============================================================================

_checkpointer_instance: Optional[PostgresSaver] = None


def get_checkpointer() -> PostgresSaver:
    """
    Obtiene o crea la instancia del checkpointer PostgreSQL.
    
    El checkpointer usa la base de datos AUTH para almacenar los checkpoints
    de conversación. LangGraph creará automáticamente la tabla necesaria
    si no existe.
    
    Returns:
        PostgresSaver: Instancia del checkpointer para memoria episódica
        
    Note:
        La tabla se llama 'checkpoints' por defecto y será creada en el schema 'public'.
        Contiene: thread_id, checkpoint_id, parent_id, checkpoint (JSONB), metadata (JSONB)
    """
    global _checkpointer_instance
    
    if _checkpointer_instance is None:
        from backend.api.core.config import get_settings
        
        settings = get_settings()
        
        try:
            # Crear checkpointer con conexión a AUTH_DB
            # LangGraph usará esta BD para almacenar estados de conversación
            _checkpointer_instance = PostgresSaver.from_conn_string(
                settings.AUTH_DB_URL
            )
            
            # Setup: Crear tabla de checkpoints si no existe
            # Esto debe llamarse una vez al iniciar la aplicación
            _checkpointer_instance.setup()
            
            logger.info(
                "✅ Checkpointer PostgreSQL inicializado correctamente"
                f" (BD: clinica_auth_db)"
            )
            
        except Exception as e:
            logger.error(f"❌ Error al inicializar checkpointer: {e}")
            raise RuntimeError(
                f"No se pudo inicializar el checkpointer PostgreSQL: {e}"
            ) from e
    
    return _checkpointer_instance


def create_thread_id(user_id: int, origin: str, conversation_uuid: str) -> str:
    """
    Genera un thread_id único para identificar hilos de conversación.
    
    El thread_id sirve para:
    1. Aislar estados entre diferentes conversaciones
    2. Permitir múltiples conversaciones del mismo usuario
    3. Diferenciar origen (webapp vs whatsapp_paciente vs whatsapp_user)
    
    Args:
        user_id: ID del usuario autenticado
        origin: Origen de la conversación ('webapp', 'whatsapp_paciente', 'whatsapp_user')
        conversation_uuid: UUID único de la conversación
        
    Returns:
        str: Thread ID en formato "{user_id}_{origin}_{uuid}"
        
    Examples:
        >>> create_thread_id(5, "webapp", "a1b2c3d4")
        "5_webapp_a1b2c3d4"
        
        >>> create_thread_id(10, "whatsapp_user", "x9y8z7")
        "10_whatsapp_user_x9y8z7"
    """
    return f"{user_id}_{origin}_{conversation_uuid}"


# =============================================================================
# FUNCIONES DE LIMPIEZA (OPCIONAL)
# =============================================================================

async def cleanup_old_checkpoints(days: int = 30):
    """
    Limpia checkpoints antiguos para gestión de almacenamiento.
    
    Esta función debe ejecutarse periódicamente (ej: cron job) para
    eliminar checkpoints de conversaciones antiguas y evitar crecimiento
    infinito de la tabla.
    
    Args:
        days: Número de días a mantener (default: 30)
        
    Note:
        Esta es una función de mantenimiento opcional. Implementar según
        políticas de retención de datos de la organización.
    """
    # TODO: Implementar cuando se requiera retention policy
    logger.warning(
        f"cleanup_old_checkpoints no implementado (days={days}). "
        "Implementar según política de retención."
    )
    pass
