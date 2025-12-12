# backend/api/services/gemini_validator.py
"""
Validador de API Keys de Google Gemini.
========================================

Este módulo verifica que una API Key de Gemini sea válida antes de almacenarla
en la base de datos, haciendo una llamada real a la API de Google.

¿Por qué validar?
-----------------
- Evitar almacenar API Keys incorrectas o expiradas
- Dar feedback inmediato al usuario si hay un error en la key
- Reducir errores cuando el chatbot intente usar la key más tarde

Flujo de validación:
--------------------
1. Usuario proporciona su API Key de Gemini en el frontend
2. Backend llama a validate_gemini_api_key()
3. Se hace una petición HTTP a la API de Google Gemini
4. Si la API responde con 200, la key es válida
5. Si responde con 400/401, la key es inválida
6. Si responde con 429, hay rate limit pero la key es válida

API Reference:
--------------
https://ai.google.dev/gemini-api/docs/api-key
"""

import logging
import httpx
from typing import Tuple

logger = logging.getLogger(__name__)

# URL base de la API de Google Generative AI (Gemini)
# Este endpoint lista los modelos disponibles y requiere una API Key válida
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"


async def validate_gemini_api_key(api_key: str) -> Tuple[bool, str]:
    """
    Valida una API Key de Gemini contra la API de Google.
    
    Hace una petición GET simple al endpoint de listado de modelos.
    Si la API Key es válida, Google responde con 200 OK.
    
    Args:
        api_key: API Key a validar (formato: "AIza..." con ~40 caracteres)
        
    Returns:
        Tuple (is_valid: bool, message: str)
        - is_valid: True si la API Key es válida, False en caso contrario
        - message: Descripción del resultado para mostrar al usuario
        
    Códigos de respuesta esperados:
        - 200: API Key válida y funcionando
        - 400: API Key inválida o con formato incorrecto
        - 401: API Key expirada o revocada
        - 403: API Key válida pero sin permisos para este endpoint (raro)
        - 429: Rate limit excedido (pero la key es válida)
        
    Ejemplo:
        >>> is_valid, msg = await validate_gemini_api_key("AIza...")
        >>> if is_valid:
        ...     print(f"✓ {msg}")
        ...     # Guardar en BD
        ... else:
        ...     print(f"✗ {msg}")
        ...     # Mostrar error al usuario
    """
    # Validación básica: longitud mínima
    # Las API Keys de Google suelen tener ~40 caracteres
    if not api_key or len(api_key) < 20:
        logger.warning("Intento de validar API Key demasiado corta o vacía")
        return False, "API Key demasiado corta o vacía"
    
    try:
        # Crear cliente HTTP asíncrono con timeout de 10 segundos
        # Timeout es importante para no bloquear el servidor si Google está lento
        async with httpx.AsyncClient(timeout=10.0) as client:
            
            # Hacer petición GET al endpoint de listado de modelos
            # NOTA DE SEGURIDAD: La API Key se pasa como query parameter porque
            # así lo requiere la API de Google Gemini. En un mundo ideal, se usaría
            # un header de autenticación, pero debemos seguir el diseño de Google.
            # Riesgo: La API Key puede quedar en logs del servidor web o proxies.
            # Mitigación: Esta validación solo se hace al configurar la key, no en cada uso.
            logger.info(f"Validando API Key de Gemini (empieza con: {api_key[:10]}...)")
            response = await client.get(
                f"{GEMINI_API_URL}?key={api_key}"
            )
            
            # Analizar código de respuesta
            if response.status_code == 200:
                # ✓ API Key válida y funcionando
                logger.info("✓ API Key de Gemini validada exitosamente")
                return True, "API Key válida"
                
            elif response.status_code == 400:
                # ✗ API Key con formato incorrecto o inválida
                logger.warning(f"API Key de Gemini inválida (400 Bad Request)")
                return False, "API Key inválida o con formato incorrecto"
                
            elif response.status_code == 401:
                # ✗ API Key expirada o revocada
                logger.warning(f"API Key de Gemini no autorizada (401 Unauthorized)")
                return False, "API Key expirada o revocada"
                
            elif response.status_code == 403:
                # ✗ API Key válida pero sin permisos (poco común)
                logger.warning(f"API Key de Gemini sin permisos (403 Forbidden)")
                return False, "API Key sin permisos necesarios"
                
            elif response.status_code == 429:
                # ⚠ Rate limit excedido, pero la key ES VÁLIDA
                # Google limita el número de requests por minuto
                # En este caso, asumimos que la key funciona
                logger.warning("Rate limit al validar Gemini, asumiendo API Key válida")
                return True, "API Key válida (rate limit temporal)"
                
            else:
                # Código de respuesta inesperado
                logger.warning(f"Respuesta inesperada de Gemini: {response.status_code}")
                return False, f"Error al validar API Key (código {response.status_code})"
                
    except httpx.TimeoutException:
        # Timeout: Google no respondió en 10 segundos
        # Puede ser un problema de red temporal
        logger.error("Timeout al validar API Key de Gemini")
        return False, "Timeout al validar API Key (intente de nuevo)"
        
    except httpx.ConnectError as e:
        # Error de conexión: no se pudo conectar a Google
        logger.error(f"Error de conexión al validar API Key de Gemini: {e}")
        return False, "Error de conexión al validar API Key"
        
    except Exception as e:
        # Error genérico: cualquier otra excepción
        logger.error(f"Error inesperado validando API Key de Gemini: {e}")
        return False, "Error al validar API Key"
