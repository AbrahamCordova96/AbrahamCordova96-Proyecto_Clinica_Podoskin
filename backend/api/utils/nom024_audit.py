# =============================================================================
# backend/api/utils/nom024_audit.py
# NOM-024 Compliance: Immutable Audit and Access Logging Utilities
# =============================================================================
# Utilidades para registrar operaciones en audit_logs_inmutable y access_logs
# según requerimientos de NOM-024.
#
# Features:
#   - log_immutable_change(): Registra cambios (INSERT/UPDATE/DELETE) en audit inmutable
#   - log_access(): Registra accesos de lectura a datos sensibles
#   - Preserva estado completo antes y después de cada cambio
#   - No permite modificación de logs (append-only)
# =============================================================================

from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import Request
import json
import logging

from backend.schemas.auth.models import AuditLogInmutable, AccessLog

logger = logging.getLogger(__name__)


def log_immutable_change(
    db: Session,
    user_id: int,
    username: str,
    tabla_afectada: str,
    registro_id: int,
    accion: str,
    datos_antes: Optional[Dict[str, Any]] = None,
    datos_despues: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    razon_cambio: Optional[str] = None
) -> AuditLogInmutable:
    """
    Registra un cambio en el log de auditoría inmutable (NOM-024).
    
    Esta función crea una entrada append-only que NO puede ser modificada o eliminada.
    Registra el estado COMPLETO del registro antes y después del cambio.
    
    Args:
        db: Sesión de base de datos (auth_db)
        user_id: ID del usuario que realiza el cambio
        username: Nombre de usuario (snapshot para inmutabilidad)
        tabla_afectada: Nombre de la tabla modificada
        registro_id: ID del registro que se modifica
        accion: Tipo de acción: "INSERT", "UPDATE", "DELETE"
        datos_antes: Estado completo ANTES del cambio (dict/JSON). NULL para INSERT
        datos_despues: Estado completo DESPUÉS del cambio (dict/JSON). NULL para DELETE
        ip_address: Dirección IP del cliente
        razon_cambio: Razón opcional del cambio (para overrides manuales)
    
    Returns:
        AuditLogInmutable: Entrada de auditoría creada
    
    Example:
        >>> # Al actualizar un paciente
        >>> log_immutable_change(
        ...     db=db,
        ...     user_id=current_user.id_usuario,
        ...     username=current_user.nombre_usuario,
        ...     tabla_afectada="pacientes",
        ...     registro_id=123,
        ...     accion="UPDATE",
        ...     datos_antes={"nombres": "Juan", "telefono": "1234567890"},
        ...     datos_despues={"nombres": "Juan Carlos", "telefono": "1234567890"},
        ...     ip_address="192.168.1.100"
        ... )
    """
    try:
        # Crear entrada de auditoría inmutable
        audit_entry = AuditLogInmutable(
            user_id=user_id,
            username_snapshot=username,
            tabla_afectada=tabla_afectada,
            registro_id=registro_id,
            accion=accion.upper(),
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            ip_address=ip_address,
            razon_cambio=razon_cambio
        )
        
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)
        
        logger.info(f"Immutable audit log created: {accion} on {tabla_afectada}#{registro_id} by user {user_id}")
        
        return audit_entry
        
    except Exception as e:
        logger.error(f"Failed to create immutable audit log: {e}")
        db.rollback()
        # Re-raise because audit failures should not be silent
        raise


def log_access(
    db: Session,
    user_id: int,
    username: str,
    accion: str,
    recurso: str,
    ip_address: Optional[str] = None,
    metodo_http: Optional[str] = None,
    endpoint: Optional[str] = None
) -> AccessLog:
    """
    Registra un acceso de lectura a datos sensibles (NOM-024).
    
    Complementa el audit log de modificaciones registrando también las LECTURAS
    de datos clínicos, lo cual es requerido por NOM-024 y buenas prácticas
    de seguridad (similar a HIPAA).
    
    Args:
        db: Sesión de base de datos (auth_db)
        user_id: ID del usuario que accede
        username: Nombre de usuario (snapshot)
        accion: Descripción de la acción (ej: "consultar_expediente", "ver_citas")
        recurso: Recurso accedido (ej: "paciente_123", "tratamiento_456")
        ip_address: Dirección IP del cliente
        metodo_http: Método HTTP (GET, POST, etc.)
        endpoint: Ruta del endpoint accedido
    
    Returns:
        AccessLog: Entrada de log de acceso creada
    
    Example:
        >>> # Al consultar un expediente
        >>> log_access(
        ...     db=db,
        ...     user_id=current_user.id_usuario,
        ...     username=current_user.nombre_usuario,
        ...     accion="consultar_expediente",
        ...     recurso=f"paciente_{paciente_id}",
        ...     ip_address="192.168.1.100",
        ...     metodo_http="GET",
        ...     endpoint="/api/v1/pacientes/123"
        ... )
    """
    try:
        # Crear entrada de log de acceso
        access_entry = AccessLog(
            user_id=user_id,
            username_snapshot=username,
            accion=accion,
            recurso=recurso,
            ip_address=ip_address,
            metodo_http=metodo_http,
            endpoint=endpoint
        )
        
        db.add(access_entry)
        db.commit()
        db.refresh(access_entry)
        
        logger.info(f"Access log created: {accion} on {recurso} by user {user_id}")
        
        return access_entry
        
    except Exception as e:
        logger.error(f"Failed to create access log: {e}")
        db.rollback()
        # Re-raise because audit failures should not be silent
        raise


def serialize_model_for_audit(model_instance) -> Dict[str, Any]:
    """
    Serializa una instancia de SQLAlchemy a diccionario para guardar en audit.
    
    Convierte todos los campos del modelo a formato JSON-serializable,
    manejando tipos especiales (date, datetime, Decimal, etc.).
    
    Args:
        model_instance: Instancia de modelo SQLAlchemy
    
    Returns:
        Dict con todos los campos serializados
    
    Example:
        >>> paciente = db.query(Paciente).get(123)
        >>> datos = serialize_model_for_audit(paciente)
        >>> # datos = {"id_paciente": 123, "nombres": "Juan", ...}
    """
    from datetime import date, datetime
    from decimal import Decimal
    
    result = {}
    
    # Obtener columnas del modelo
    for column in model_instance.__table__.columns:
        value = getattr(model_instance, column.name)
        
        # Convertir tipos especiales a JSON-serializable
        if value is None:
            result[column.name] = None
        elif isinstance(value, (date, datetime)):
            result[column.name] = value.isoformat()
        elif isinstance(value, Decimal):
            result[column.name] = float(value)
        else:
            result[column.name] = value
    
    return result


def get_client_ip(request: Request) -> Optional[str]:
    """
    Obtiene la dirección IP del cliente desde el request.
    
    Maneja casos donde hay proxies reversos (X-Forwarded-For).
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Dirección IP del cliente o None
    """
    # Intentar obtener IP desde header X-Forwarded-For (si hay proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For puede tener múltiples IPs, tomar la primera
        return forwarded_for.split(",")[0].strip()
    
    # Intentar obtener IP desde header X-Real-IP (nginx)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback: IP directa del cliente
    if request.client:
        return request.client.host
    
    return None


# =============================================================================
# Decorators for automatic audit logging
# =============================================================================
# TODO: Implementar decoradores para facilitar el uso en endpoints
# Por ejemplo: @audit_changes("pacientes") que automáticamente llame a log_immutable_change
# =============================================================================
