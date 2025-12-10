# =============================================================================
# backend/api/routes/notifications.py
# Endpoints para envío de notificaciones y recordatorios
# =============================================================================
"""
This module provides endpoints for sending notifications.

Includes:
- Appointment reminder emails
- Manual notifications
- Bulk reminder sending
"""

from typing import Optional, List
from datetime import date, time, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_core_db, get_ops_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES, ALL_ROLES
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Paciente
from backend.schemas.ops.models import Cita, Podologo, CatalogoServicio
from backend.api.utils.notifications import send_appointment_reminder


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AppointmentReminderRequest(BaseModel):
    """Request to send appointment reminder"""
    cita_id: int


class BulkReminderRequest(BaseModel):
    """Request to send reminders for multiple appointments"""
    days_ahead: int = Field(default=1, ge=0, le=7, description="Días de anticipación (0-7)")
    send_email: bool = Field(default=True, description="Enviar por email")
    send_sms: bool = Field(default=False, description="Enviar por SMS")


class NotificationResponse(BaseModel):
    """Response for notification sending"""
    success: bool
    message: str
    sent_count: Optional[int] = None
    failed_count: Optional[int] = None


# =============================================================================
# ENDPOINT: POST /notifications/appointment-reminder
# =============================================================================

@router.post("/appointment-reminder", response_model=NotificationResponse)
async def send_appointment_reminder_endpoint(
    request: AppointmentReminderRequest,
    background_tasks: BackgroundTasks,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Envía recordatorio de cita a un paciente.
    
    **Permisos:** Todos los roles
    
    **Parámetros:**
    - cita_id: ID de la cita
    
    **Funcionalidad:**
    - Envía email con recordatorio de cita
    - Verifica que la cita exista y tenga email del paciente
    - Envío asíncrono en segundo plano
    """
    # Get appointment
    cita = ops_db.query(Cita).filter(
        Cita.id_cita == request.cita_id
    ).first()
    
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )
    
    # Verify clinic access
    if current_user.clinica_id and cita.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta cita"
        )
    
    # Check if appointment is in the future
    appointment_datetime = datetime.combine(cita.fecha_cita, cita.hora_inicio)
    if appointment_datetime < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden enviar recordatorios para citas pasadas"
        )
    
    # Get patient
    if not cita.paciente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cita no tiene paciente asignado"
        )
    
    paciente = core_db.query(Paciente).filter(
        Paciente.id_paciente == cita.paciente_id
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    if not paciente.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El paciente no tiene email registrado"
        )
    
    # Get podiatrist
    podologo = ops_db.query(Podologo).filter(
        Podologo.id_podologo == cita.podologo_id
    ).first()
    
    podiatrist_name = podologo.nombre_completo if podologo else "Podólogo"
    
    # Get service
    servicio = ops_db.query(CatalogoServicio).filter(
        CatalogoServicio.id_servicio == cita.servicio_id
    ).first()
    
    service_name = servicio.nombre if servicio else "Consulta"
    
    # Send reminder asynchronously
    patient_name = f"{paciente.nombres} {paciente.apellidos}"
    
    try:
        # Send in background task to avoid blocking
        background_tasks.add_task(
            send_appointment_reminder,
            patient_name=patient_name,
            patient_email=paciente.email,
            appointment_date=cita.fecha_cita,
            appointment_time=cita.hora_inicio,
            podiatrist_name=podiatrist_name,
            service_name=service_name,
            notes=cita.notas_agendamiento
        )
        
        return NotificationResponse(
            success=True,
            message=f"Recordatorio enviado a {paciente.email}"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error enviando recordatorio: {str(e)}"
        )


# =============================================================================
# ENDPOINT: POST /notifications/bulk-reminders
# =============================================================================

@router.post("/bulk-reminders", response_model=NotificationResponse)
async def send_bulk_reminders(
    request: BulkReminderRequest,
    background_tasks: BackgroundTasks,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Envía recordatorios masivos para citas próximas.
    
    **Permisos:** Admin y Podologo
    
    **Parámetros:**
    - days_ahead: Días de anticipación (0-7)
    - send_email: Enviar por email
    - send_sms: Enviar por SMS (no implementado aún)
    
    **Funcionalidad:**
    - Busca citas en el rango de fechas especificado
    - Envía recordatorios solo a citas confirmadas o pendientes
    - Envío asíncrono en segundo plano
    
    **Ejemplo:**
    ```json
    {
        "days_ahead": 1,
        "send_email": true,
        "send_sms": false
    }
    ```
    """
    # Calculate target date
    target_date = date.today() + timedelta(days=request.days_ahead)
    
    # Get appointments for target date
    query = ops_db.query(Cita).filter(
        Cita.fecha_cita == target_date,
        Cita.status.in_(["Pendiente", "Confirmada"])
    )
    
    # Filter by clinic if user has one
    if current_user.clinica_id:
        query = query.filter(Cita.id_clinica == current_user.clinica_id)
    
    citas = query.all()
    
    if not citas:
        return NotificationResponse(
            success=True,
            message=f"No hay citas para {target_date.strftime('%d/%m/%Y')}",
            sent_count=0,
            failed_count=0
        )
    
    sent_count = 0
    failed_count = 0
    
    # Send reminders for each appointment
    for cita in citas:
        try:
            # Skip if no patient
            if not cita.paciente_id:
                failed_count += 1
                continue
            
            # Get patient
            paciente = core_db.query(Paciente).filter(
                Paciente.id_paciente == cita.paciente_id
            ).first()
            
            if not paciente or not paciente.email:
                failed_count += 1
                continue
            
            # Get podiatrist
            podologo = ops_db.query(Podologo).filter(
                Podologo.id_podologo == cita.podologo_id
            ).first()
            
            podiatrist_name = podologo.nombre_completo if podologo else "Podólogo"
            
            # Get service
            servicio = ops_db.query(CatalogoServicio).filter(
                CatalogoServicio.id_servicio == cita.servicio_id
            ).first()
            
            service_name = servicio.nombre if servicio else "Consulta"
            
            # Send reminder
            patient_name = f"{paciente.nombres} {paciente.apellidos}"
            
            if request.send_email:
                background_tasks.add_task(
                    send_appointment_reminder,
                    patient_name=patient_name,
                    patient_email=paciente.email,
                    appointment_date=cita.fecha_cita,
                    appointment_time=cita.hora_inicio,
                    podiatrist_name=podiatrist_name,
                    service_name=service_name,
                    notes=cita.notas_agendamiento
                )
                sent_count += 1
            
        except Exception as e:
            print(f"Error sending reminder for cita {cita.id_cita}: {e}")
            failed_count += 1
    
    return NotificationResponse(
        success=True,
        message=f"Recordatorios enviados para {target_date.strftime('%d/%m/%Y')}",
        sent_count=sent_count,
        failed_count=failed_count
    )


# =============================================================================
# ENDPOINT: GET /notifications/upcoming-reminders
# =============================================================================

@router.get("/upcoming-reminders")
async def get_upcoming_reminders(
    days_ahead: int = Query(1, ge=0, le=7, description="Días de anticipación"),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Lista citas que necesitan recordatorios.
    
    **Permisos:** Admin y Podologo
    
    **Parámetros:**
    - days_ahead: Días de anticipación (0-7)
    
    **Retorna:**
    Lista de citas con información de paciente para enviar recordatorios.
    """
    target_date = date.today() + timedelta(days=days_ahead)
    
    # Get appointments
    query = ops_db.query(Cita).filter(
        Cita.fecha_cita == target_date,
        Cita.status.in_(["Pendiente", "Confirmada"])
    )
    
    if current_user.clinica_id:
        query = query.filter(Cita.id_clinica == current_user.clinica_id)
    
    citas = query.all()
    
    result = []
    for cita in citas:
        if not cita.paciente_id:
            continue
        
        paciente = core_db.query(Paciente).filter(
            Paciente.id_paciente == cita.paciente_id
        ).first()
        
        if not paciente:
            continue
        
        result.append({
            "cita_id": cita.id_cita,
            "fecha": cita.fecha_cita,
            "hora": cita.hora_inicio,
            "paciente_id": paciente.id_paciente,
            "paciente_nombre": f"{paciente.nombres} {paciente.apellidos}",
            "paciente_email": paciente.email,
            "paciente_telefono": paciente.telefono,
            "has_email": bool(paciente.email),
            "status": cita.status
        })
    
    return {
        "target_date": target_date,
        "total_appointments": len(result),
        "with_email": sum(1 for r in result if r["has_email"]),
        "appointments": result
    }
