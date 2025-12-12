# backend/api/core/encryption.py
"""
Servicio de encriptación para API Keys y datos sensibles.
==========================================================

Este módulo proporciona funciones para encriptar y desencriptar API Keys
de forma segura usando Fernet (symmetric encryption) de la librería cryptography.

Fernet garantiza que:
- Los datos no pueden ser manipulados sin ser detectados
- Los datos no pueden ser leídos sin la clave correcta
- Usa AES-128 en modo CBC con PKCS7 padding
- Incluye timestamp para detectar tokens expirados

Uso típico:
-----------
    from backend.api.core.encryption import encrypt_api_key, decrypt_api_key
    
    # Encriptar antes de guardar en BD
    api_key_plain = "AIzaSyC1234567890abcdefghijklmnopqrstuv"
    api_key_encrypted = encrypt_api_key(api_key_plain)
    # Guardar api_key_encrypted en la base de datos
    
    # Desencriptar al recuperar de BD
    api_key_plain = decrypt_api_key(api_key_encrypted)
    # Usar api_key_plain para hacer llamadas a la API

Seguridad:
----------
- NUNCA loguear API Keys en texto plano
- NUNCA retornar API Keys completas en responses (máximo primeros 10 caracteres)
- SIEMPRE validar la API Key antes de guardar
- Rotar la ENCRYPTION_KEY periódicamente (cada 6-12 meses)
"""

import logging
from cryptography.fernet import Fernet, InvalidToken
from backend.api.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Inicializar el cipher de Fernet con la clave de configuración
# El cipher es la "máquina de encriptación/desencriptación"
try:
    _cipher = Fernet(settings.ENCRYPTION_KEY.encode())
    logger.info("✓ Cipher de encriptación inicializado correctamente")
except Exception as e:
    logger.critical(f"✗ ERROR CRÍTICO: No se pudo inicializar el cipher de encriptación: {e}")
    logger.critical("⚠ ENCRYPTION_KEY no está configurada correctamente en .env")
    logger.critical("⚠ Generar una clave con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
    logger.critical("⚠ La aplicación no puede continuar sin una clave de encriptación válida")
    # En producción, la aplicación DEBE fallar aquí
    # NO usar una clave aleatoria porque haría irrecuperables las API Keys existentes
    raise RuntimeError(
        "ENCRYPTION_KEY no configurada o inválida. "
        "La aplicación no puede iniciar sin una clave de encriptación válida. "
        "Ver logs arriba para instrucciones."
    )


def encrypt_api_key(plain_key: str) -> str:
    """
    Encripta una API Key en texto plano usando Fernet.
    
    Proceso:
    1. Convierte el string a bytes
    2. Aplica encriptación Fernet (AES-128-CBC + HMAC)
    3. Convierte el resultado a string base64
    
    Args:
        plain_key: API Key en texto plano (ej: "AIzaSyC1234...")
        
    Returns:
        API Key encriptada en formato string base64
        
    Raises:
        ValueError: Si la API Key está vacía o solo contiene espacios
        Exception: Si falla el proceso de encriptación
        
    Ejemplo:
        >>> encrypted = encrypt_api_key("AIzaSyC1234567890")
        >>> print(encrypted)
        'gAAAAABf...' (string largo encriptado)
    """
    # Validación: la API Key no puede estar vacía
    if not plain_key or not plain_key.strip():
        raise ValueError("La API Key no puede estar vacía")
    
    try:
        # Encriptar: texto -> bytes -> encriptar -> base64 string
        encrypted_bytes = _cipher.encrypt(plain_key.encode())
        encrypted_str = encrypted_bytes.decode()
        
        # Log seguro: solo los primeros 10 caracteres de la key original
        logger.info(f"✓ API Key encriptada correctamente (empieza con: {plain_key[:10]}...)")
        return encrypted_str
        
    except Exception as e:
        logger.error(f"✗ Error encriptando API Key: {e}")
        raise Exception("Error al encriptar la API Key")


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Desencripta una API Key previamente encriptada con encrypt_api_key().
    
    Proceso:
    1. Convierte el string base64 a bytes
    2. Aplica desencriptación Fernet
    3. Verifica la integridad (HMAC)
    4. Convierte el resultado a string
    
    Args:
        encrypted_key: API Key encriptada (resultado de encrypt_api_key)
        
    Returns:
        API Key en texto plano
        
    Raises:
        ValueError: Si la API Key encriptada está vacía
        InvalidToken: Si la API Key no puede desencriptarse porque:
                      - Fue encriptada con una clave diferente
                      - Está corrupta o fue manipulada
                      - El formato es inválido
        
    Ejemplo:
        >>> plain = decrypt_api_key("gAAAAABf...")
        >>> print(plain)
        'AIzaSyC1234567890'
    """
    # Validación: el string encriptado no puede estar vacío
    if not encrypted_key or not encrypted_key.strip():
        raise ValueError("La API Key encriptada no puede estar vacía")
    
    try:
        # Desencriptar: base64 string -> bytes -> desencriptar -> texto
        decrypted_bytes = _cipher.decrypt(encrypted_key.encode())
        decrypted_str = decrypted_bytes.decode()
        
        logger.debug("✓ API Key desencriptada correctamente")
        return decrypted_str
        
    except InvalidToken:
        # Error específico: el token no pudo ser desencriptado
        # Esto sucede cuando:
        # - La ENCRYPTION_KEY cambió desde que se encriptó
        # - Los datos están corruptos
        # - Alguien intentó manipular el token
        logger.error("✗ Token inválido al desencriptar API Key (posiblemente corrupta o clave incorrecta)")
        raise InvalidToken("La API Key no pudo ser desencriptada (posiblemente corrupta)")
        
    except Exception as e:
        logger.error(f"✗ Error desencriptando API Key: {e}")
        raise Exception("Error al desencriptar la API Key")


def validate_encryption_key() -> bool:
    """
    Valida que la clave de encriptación (ENCRYPTION_KEY) funcione correctamente.
    
    Realiza un test de "round-trip": encripta un texto de prueba y luego
    lo desencripta, verificando que el resultado sea idéntico al original.
    
    Esta función es útil para:
    - Verificar al iniciar la aplicación que la clave está configurada
    - Testing automatizado
    - Health checks
    
    Returns:
        True si la encriptación/desencriptación funciona correctamente
        False si hay algún error
        
    Ejemplo:
        >>> if validate_encryption_key():
        ...     print("Encriptación funcionando correctamente")
        ... else:
        ...     print("ERROR: Problema con la clave de encriptación")
    """
    try:
        # Texto de prueba
        test_data = "test_api_key_validation_12345"
        
        # Round-trip: encriptar -> desencriptar -> comparar
        encrypted = encrypt_api_key(test_data)
        decrypted = decrypt_api_key(encrypted)
        
        # Verificar que el resultado sea idéntico al original
        if decrypted == test_data:
            logger.info("✓ Validación de clave de encriptación exitosa")
            return True
        else:
            logger.error("✗ Los datos desencriptados no coinciden con el original")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error validando clave de encriptación: {e}")
        return False
