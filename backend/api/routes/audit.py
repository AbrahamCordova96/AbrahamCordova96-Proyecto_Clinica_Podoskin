# =============================================================================
# backend/api/routes/audit.py
# Endpoints de Auditoría
# =============================================================================
# Este archivo implementa los endpoints de auditoría:
#   - GET /audit → Listar logs de auditoría
#   - GET /audit/{tabla}/{id} → Historial de un registro
#   - GET /audit/export → Exportar logs (Solo Admin)
#
# PERMISOS:
#   - Lectura: Admin y Podologo
#   - Exportación: Solo Admin
# =============================================================================

from typing import Optional
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import csv
import io

from backend.api.deps.database import get_auth_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES, ROLE_ADMIN
from backend.schemas.auth.models import SysUsuario, AuditLog


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/audit", tags=["Auditoría"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AuditLogResponse(BaseModel):
    """Response de log de auditoría"""
    id_log: int
    tabla_afectada: str
    registro_id: Optional[int] = None
    accion: str
    usuario_id: Optional[int] = None
    datos_anteriores: Optional[dict] = None
    datos_nuevos: Optional[dict] = None
    ip_address: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT: GET /audit
# =============================================================================

@router.get("")
async def list_audit_logs(
    tabla: Optional[str] = Query(None, description="Filtrar por tabla"),
    accion: Optional[str] = Query(None, description="Filtrar por acción (INSERT/UPDATE/DELETE)"),
    usuario_id: Optional[int] = Query(None, description="Filtrar por usuario"),
    fecha_inicio: Optional[date] = Query(None, description="Desde fecha"),
    fecha_fin: Optional[date] = Query(None, description="Hasta fecha"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_auth_db)
):
    """
    Lista los logs de auditoría.
    
    **Permisos:** Admin y Podologo
    
    **Filtros:**
    - tabla: Nombre de la tabla afectada
    - accion: INSERT, UPDATE, DELETE
    - usuario_id: ID del usuario que hizo la acción
    - fecha_inicio, fecha_fin: Rango de fechas
    """
    query = db.query(AuditLog)
    
    # Aplicar filtros
    if tabla:
        query = query.filter(AuditLog.tabla_afectada == tabla)
    if accion:
        query = query.filter(AuditLog.accion == accion)
    if usuario_id:
        query = query.filter(AuditLog.usuario_id == usuario_id)
    if fecha_inicio:
        query = query.filter(AuditLog.timestamp_accion >= datetime.combine(fecha_inicio, datetime.min.time()))
    if fecha_fin:
        query = query.filter(AuditLog.timestamp_accion <= datetime.combine(fecha_fin, datetime.max.time()))
    
    # Ordenar por más reciente
    query = query.order_by(AuditLog.timestamp_accion.desc())
    
    total = query.count()
    logs = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "logs": [AuditLogResponse.model_validate(log) for log in logs]
    }


# =============================================================================
# ENDPOINT: GET /audit/{tabla}/{registro_id}
# =============================================================================

@router.get("/{tabla}/{registro_id}")
async def get_registro_history(
    tabla: str,
    registro_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_auth_db)
):
    """
    Obtiene el historial de cambios de un registro específico.
    
    **Permisos:** Admin y Podologo
    
    **Ejemplo:**
    - GET /audit/pacientes/123 → Historial de cambios del paciente 123
    """
    logs = db.query(AuditLog).filter(
        AuditLog.tabla_afectada == tabla,
        AuditLog.registro_id == registro_id
    ).order_by(AuditLog.timestamp_accion.desc()).all()
    
    if not logs:
        return {
            "tabla": tabla,
            "registro_id": registro_id,
            "message": "No hay historial de cambios para este registro",
            "logs": []
        }
    
    return {
        "tabla": tabla,
        "registro_id": registro_id,
        "total_cambios": len(logs),
        "logs": [AuditLogResponse.model_validate(log) for log in logs]
    }


# =============================================================================
# ENDPOINT: GET /audit/export
# =============================================================================

@router.get("/export")
async def export_audit_logs(
    fecha_inicio: Optional[date] = Query(None, description="Desde fecha"),
    fecha_fin: Optional[date] = Query(None, description="Hasta fecha"),
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_auth_db)
):
    """
    Exporta los logs de auditoría a CSV.
    
    **Permisos:** Solo Admin
    
    **Retorna:** Archivo CSV para descargar
    """
    query = db.query(AuditLog)
    
    # Aplicar filtros de fecha
    if fecha_inicio:
        query = query.filter(AuditLog.timestamp_accion >= datetime.combine(fecha_inicio, datetime.min.time()))
    if fecha_fin:
        query = query.filter(AuditLog.timestamp_accion <= datetime.combine(fecha_fin, datetime.max.time()))
    
    logs = query.order_by(AuditLog.timestamp_accion.desc()).all()
    
    # Crear CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Tabla", "Registro ID", "Acción", 
        "Usuario ID", "IP", "Timestamp"
    ])
    
    # Datos
    for log in logs:
        writer.writerow([
            log.id_log,
            log.tabla_afectada,
            log.registro_id,
            log.accion,
            log.usuario_id,
            log.ip_address,
            log.timestamp_accion.isoformat() if log.timestamp_accion else ""
        ])
    
    output.seek(0)
    
    # Generar nombre de archivo
    filename = f"audit_log_{date.today().isoformat()}.csv"
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
