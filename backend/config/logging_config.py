# =============================================================================
# backend/config/logging_config.py
# Configuración de logging mejorada para uvicorn
# =============================================================================

import logging
import logging.config
from datetime import datetime
from typing import Any

# =============================================================================
# FORMATO PERSONALIZADO
# =============================================================================
class ColoredFormatter(logging.Formatter):
    """Formatter con colores y formato limpio para terminal."""
    
    # Códigos ANSI para colores
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Verde
        'WARNING': '\033[33m',    # Amarillo
        'ERROR': '\033[31m',      # Rojo
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m',       # Reset
    }
    
    # Símbolos para métodos HTTP (sin emojis para evitar encoding issues)
    HTTP_METHODS = {
        'GET': '[>]',
        'POST': '[+]',
        'PUT': '[*]',
        'PATCH': '[~]',
        'DELETE': '[-]'
    }
    
    # Colores para status codes
    STATUS_COLORS = {
        '2': '\033[92m',  # Verde brillante (200-299)
        '3': '\033[96m',  # Cyan brillante (300-399)
        '4': '\033[93m',  # Amarillo brillante (400-499)
        '5': '\033[91m',  # Rojo brillante (500-599)
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Timestamp compacto
        timestamp = datetime.fromtimestamp(record.created).strftime('%H:%M:%S')
        
        # Color según nivel
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Formatear mensaje según tipo
        message = record.getMessage()
        
        # Detectar requests HTTP (uvicorn.access logs)
        if 'HTTP/' in message:
            parts = message.split('"')
            if len(parts) >= 3:
                # Extraer: "GET /endpoint HTTP/1.1" 200 OK
                request_line = parts[1]
                status_info = parts[2].strip()
                
                # Parsear método y endpoint
                method_parts = request_line.split()
                if len(method_parts) >= 2:
                    method = method_parts[0]
                    endpoint = method_parts[1]
                    
                    # Parsear status code
                    status_parts = status_info.split()
                    status_code = status_parts[0] if status_parts else "???"
                    
                    # Color para status
                    status_first_digit = status_code[0] if status_code.isdigit() else '?'
                    status_color = self.STATUS_COLORS.get(status_first_digit, reset)
                    
                    # Símbolo para método
                    method_emoji = self.HTTP_METHODS.get(method, '[?]')
                    
                    # Formato compacto y limpio
                    formatted = (
                        f"{timestamp} {method_emoji} "
                        f"{method:6s} "
                        f"{status_color}{status_code:3s}{reset} "
                        f"{endpoint}"
                    )
                    
                    return formatted
        
        # Logs normales (no HTTP)
        return f"{timestamp} [{level_color}{record.levelname:8s}{reset}] {message}"


# =============================================================================
# CONFIGURACIÓN DE UVICORN
# =============================================================================
LOGGING_CONFIG: dict[str, Any] = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": ColoredFormatter,
        },
        "access": {
            "()": ColoredFormatter,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["default"],
            "level": "INFO",
        },
        "uvicorn.error": {
            "level": "INFO",
        },
        "uvicorn.access": {
            "handlers": ["access"],
            "level": "INFO",
            "propagate": False,
        },
    },
}


# =============================================================================
# APLICAR CONFIGURACIÓN
# =============================================================================
def setup_logging() -> None:
    """Aplica la configuración de logging."""
    logging.config.dictConfig(LOGGING_CONFIG)
