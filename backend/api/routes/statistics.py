# =============================================================================
# backend/api/routes/statistics.py
# Endpoints de estadísticas agregadas
# =============================================================================
"""
This module provides aggregated statistics endpoints for the clinic.

Includes metrics such as:
- Patient statistics (total, new, by demographics)
- Appointment statistics (total, by status, by month)
- Treatment statistics (active, completed, by type)
- Financial statistics (revenue, expenses)
- Podiatrist performance metrics
"""

from typing import Optional, Dict, Any
from datetime import date, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_, or_
from pydantic import BaseModel, Field

from backend.api.deps.database import get_core_db, get_ops_db, get_auth_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES, ROLE_ADMIN
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Paciente, Tratamiento, EvolucionClinica, EvidenciaFotografica
from backend.schemas.ops.models import Cita, Podologo, Transaccion, Gasto


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/statistics", tags=["Estadísticas"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PatientStatistics(BaseModel):
    """Patient-related statistics"""
    total_patients: int
    active_patients: int
    new_patients_this_month: int
    new_patients_last_month: int
    patients_by_sex: Dict[str, int]
    average_age: Optional[float] = None


class AppointmentStatistics(BaseModel):
    """Appointment-related statistics"""
    total_appointments: int
    appointments_today: int
    appointments_this_week: int
    appointments_this_month: int
    appointments_by_status: Dict[str, int]
    completion_rate: float = Field(description="Percentage of completed appointments")


class TreatmentStatistics(BaseModel):
    """Treatment-related statistics"""
    total_treatments: int
    active_treatments: int
    completed_treatments: int
    treatments_this_month: int
    average_duration_days: Optional[float] = None


class FinancialStatistics(BaseModel):
    """Financial statistics"""
    total_revenue_this_month: float
    total_revenue_last_month: float
    total_expenses_this_month: float
    pending_payments: float
    paid_amount_this_month: float


class PodiatristStatistics(BaseModel):
    """Podiatrist performance statistics"""
    total_podiatrists: int
    active_podiatrists: int
    appointments_per_podiatrist: Dict[str, int]
    busiest_podiatrist: Optional[str] = None


class DashboardStatistics(BaseModel):
    """Complete dashboard statistics"""
    patients: PatientStatistics
    appointments: AppointmentStatistics
    treatments: TreatmentStatistics
    financial: FinancialStatistics
    podiatrists: PodiatristStatistics
    generated_at: datetime


# =============================================================================
# ENDPOINT: GET /statistics/dashboard
# =============================================================================

@router.get("/dashboard", response_model=DashboardStatistics)
async def get_dashboard_statistics(
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Get aggregated statistics for dashboard.
    
    **Permisos:** Admin y Podologo
    
    Returns comprehensive statistics including:
    - Patient metrics
    - Appointment metrics
    - Treatment metrics
    - Financial metrics (Admin only)
    - Podiatrist performance
    """
    # Calculate date ranges
    now = datetime.now(timezone.utc)
    today = now.date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # Filter by clinic if user has one
    clinic_filter_core = Paciente.id_clinica == current_user.clinica_id if current_user.clinica_id else True
    clinic_filter_ops = Cita.id_clinica == current_user.clinica_id if current_user.clinica_id else True
    
    # =============================================================================
    # PATIENT STATISTICS
    # =============================================================================
    
    total_patients = core_db.query(func.count(Paciente.id_paciente)).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core
    ).scalar() or 0
    
    active_patients = core_db.query(func.count(Paciente.id_paciente)).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core,
        Paciente.fecha_registro >= month_start
    ).scalar() or 0
    
    new_patients_this_month = core_db.query(func.count(Paciente.id_paciente)).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core,
        func.date(Paciente.fecha_registro) >= month_start
    ).scalar() or 0
    
    new_patients_last_month = core_db.query(func.count(Paciente.id_paciente)).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core,
        func.date(Paciente.fecha_registro) >= last_month_start,
        func.date(Paciente.fecha_registro) < month_start
    ).scalar() or 0
    
    # Patients by sex
    sex_stats = core_db.query(
        Paciente.sexo,
        func.count(Paciente.id_paciente)
    ).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core,
        Paciente.sexo.isnot(None)
    ).group_by(Paciente.sexo).all()
    
    patients_by_sex = {sex: count for sex, count in sex_stats}
    
    # Average age - calculate using database-agnostic approach
    # Get birth dates and calculate age in Python for better compatibility
    patients_with_birth = core_db.query(Paciente.fecha_nacimiento).filter(
        Paciente.deleted_at.is_(None),
        clinic_filter_core,
        Paciente.fecha_nacimiento.isnot(None)
    ).all()
    
    if patients_with_birth:
        from datetime import date as date_type
        today = date_type.today()
        ages = []
        for (birth_date,) in patients_with_birth:
            if birth_date:
                age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                ages.append(age)
        avg_age = sum(ages) / len(ages) if ages else None
    else:
        avg_age = None
    
    patient_stats = PatientStatistics(
        total_patients=total_patients,
        active_patients=active_patients,
        new_patients_this_month=new_patients_this_month,
        new_patients_last_month=new_patients_last_month,
        patients_by_sex=patients_by_sex,
        average_age=avg_age
    )
    
    # =============================================================================
    # APPOINTMENT STATISTICS
    # =============================================================================
    
    total_appointments = ops_db.query(func.count(Cita.id_cita)).filter(
        clinic_filter_ops
    ).scalar() or 0
    
    appointments_today = ops_db.query(func.count(Cita.id_cita)).filter(
        clinic_filter_ops,
        Cita.fecha_cita == today
    ).scalar() or 0
    
    appointments_this_week = ops_db.query(func.count(Cita.id_cita)).filter(
        clinic_filter_ops,
        Cita.fecha_cita >= week_start
    ).scalar() or 0
    
    appointments_this_month = ops_db.query(func.count(Cita.id_cita)).filter(
        clinic_filter_ops,
        Cita.fecha_cita >= month_start
    ).scalar() or 0
    
    # Appointments by status
    status_stats = ops_db.query(
        Cita.status,
        func.count(Cita.id_cita)
    ).filter(
        clinic_filter_ops
    ).group_by(Cita.status).all()
    
    appointments_by_status = {status: count for status, count in status_stats}
    
    # Completion rate
    completed = appointments_by_status.get("Realizada", 0)
    completion_rate = (completed / total_appointments * 100) if total_appointments > 0 else 0.0
    
    appointment_stats = AppointmentStatistics(
        total_appointments=total_appointments,
        appointments_today=appointments_today,
        appointments_this_week=appointments_this_week,
        appointments_this_month=appointments_this_month,
        appointments_by_status=appointments_by_status,
        completion_rate=round(completion_rate, 2)
    )
    
    # =============================================================================
    # TREATMENT STATISTICS
    # =============================================================================
    
    total_treatments = core_db.query(func.count(Tratamiento.id_tratamiento)).filter(
        clinic_filter_core
    ).scalar() or 0
    
    active_treatments = core_db.query(func.count(Tratamiento.id_tratamiento)).filter(
        clinic_filter_core,
        Tratamiento.estado == "activo"
    ).scalar() or 0
    
    completed_treatments = core_db.query(func.count(Tratamiento.id_tratamiento)).filter(
        clinic_filter_core,
        Tratamiento.estado == "completado"
    ).scalar() or 0
    
    treatments_this_month = core_db.query(func.count(Tratamiento.id_tratamiento)).filter(
        clinic_filter_core,
        func.date(Tratamiento.fecha_inicio) >= month_start
    ).scalar() or 0
    
    # Average treatment duration
    avg_duration = core_db.query(
        func.avg(
            func.extract('day', Tratamiento.fecha_fin - Tratamiento.fecha_inicio)
        )
    ).filter(
        clinic_filter_core,
        Tratamiento.fecha_fin.isnot(None),
        Tratamiento.estado == "completado"
    ).scalar()
    
    treatment_stats = TreatmentStatistics(
        total_treatments=total_treatments,
        active_treatments=active_treatments,
        completed_treatments=completed_treatments,
        treatments_this_month=treatments_this_month,
        average_duration_days=float(avg_duration) if avg_duration else None
    )
    
    # =============================================================================
    # FINANCIAL STATISTICS (Admin only)
    # =============================================================================
    
    if current_user.rol == ROLE_ADMIN:
        # Revenue this month
        revenue_this_month = ops_db.query(
            func.coalesce(func.sum(Transaccion.monto), 0)
        ).filter(
            Transaccion.tipo_transaccion == "ingreso",
            func.date(Transaccion.fecha_transaccion) >= month_start
        ).scalar() or 0.0
        
        # Revenue last month
        revenue_last_month = ops_db.query(
            func.coalesce(func.sum(Transaccion.monto), 0)
        ).filter(
            Transaccion.tipo_transaccion == "ingreso",
            func.date(Transaccion.fecha_transaccion) >= last_month_start,
            func.date(Transaccion.fecha_transaccion) < month_start
        ).scalar() or 0.0
        
        # Expenses this month
        expenses_this_month = ops_db.query(
            func.coalesce(func.sum(Gasto.monto), 0)
        ).filter(
            func.date(Gasto.fecha_gasto) >= month_start
        ).scalar() or 0.0
        
        # Pending payments
        pending_payments = ops_db.query(
            func.coalesce(func.sum(Transaccion.monto), 0)
        ).filter(
            Transaccion.tipo_transaccion == "ingreso",
            Transaccion.estado == "pendiente"
        ).scalar() or 0.0
        
        # Paid amount this month
        paid_this_month = ops_db.query(
            func.coalesce(func.sum(Transaccion.monto), 0)
        ).filter(
            Transaccion.tipo_transaccion == "ingreso",
            Transaccion.estado == "completado",
            func.date(Transaccion.fecha_transaccion) >= month_start
        ).scalar() or 0.0
    else:
        # Non-admin users don't see financial data
        revenue_this_month = 0.0
        revenue_last_month = 0.0
        expenses_this_month = 0.0
        pending_payments = 0.0
        paid_this_month = 0.0
    
    financial_stats = FinancialStatistics(
        total_revenue_this_month=float(revenue_this_month),
        total_revenue_last_month=float(revenue_last_month),
        total_expenses_this_month=float(expenses_this_month),
        pending_payments=float(pending_payments),
        paid_amount_this_month=float(paid_this_month)
    )
    
    # =============================================================================
    # PODIATRIST STATISTICS
    # =============================================================================
    
    total_podiatrists = ops_db.query(func.count(Podologo.id_podologo)).filter(
        Podologo.estado == "activo"
    ).scalar() or 0
    
    active_podiatrists = ops_db.query(func.count(Podologo.id_podologo)).filter(
        Podologo.estado == "activo"
    ).scalar() or 0
    
    # Appointments per podiatrist
    podo_stats = ops_db.query(
        Podologo.nombre_completo,
        func.count(Cita.id_cita)
    ).join(
        Cita, Podologo.id_podologo == Cita.podologo_id
    ).filter(
        clinic_filter_ops
    ).group_by(Podologo.nombre_completo).all()
    
    appointments_per_podo = {name: count for name, count in podo_stats}
    busiest_podo = max(podo_stats, key=lambda x: x[1])[0] if podo_stats else None
    
    podiatrist_stats = PodiatristStatistics(
        total_podiatrists=total_podiatrists,
        active_podiatrists=active_podiatrists,
        appointments_per_podiatrist=appointments_per_podo,
        busiest_podiatrist=busiest_podo
    )
    
    # =============================================================================
    # RETURN COMPLETE DASHBOARD
    # =============================================================================
    
    return DashboardStatistics(
        patients=patient_stats,
        appointments=appointment_stats,
        treatments=treatment_stats,
        financial=financial_stats,
        podiatrists=podiatrist_stats,
        generated_at=now
    )


# =============================================================================
# ENDPOINT: GET /statistics/summary
# =============================================================================

@router.get("/summary")
async def get_statistics_summary(
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    core_db: Session = Depends(get_core_db),
    ops_db: Session = Depends(get_ops_db)
):
    """
    Get a quick summary of key statistics.
    
    **Permisos:** Admin y Podologo
    
    Returns a lightweight summary with the most important metrics.
    """
    today = date.today()
    clinic_filter_core = Paciente.id_clinica == current_user.clinica_id if current_user.clinica_id else True
    clinic_filter_ops = Cita.id_clinica == current_user.clinica_id if current_user.clinica_id else True
    
    return {
        "total_patients": core_db.query(func.count(Paciente.id_paciente)).filter(
            Paciente.deleted_at.is_(None), clinic_filter_core
        ).scalar() or 0,
        "appointments_today": ops_db.query(func.count(Cita.id_cita)).filter(
            clinic_filter_ops, Cita.fecha_cita == today
        ).scalar() or 0,
        "active_treatments": core_db.query(func.count(Tratamiento.id_tratamiento)).filter(
            clinic_filter_core, Tratamiento.estado == "activo"
        ).scalar() or 0,
        "generated_at": datetime.now(timezone.utc)
    }
