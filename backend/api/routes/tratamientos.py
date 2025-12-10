# =============================================================================
# backend/api/routes/tratamientos.py
# CRUD de Tratamientos (Carpetas de problemas del paciente)
# =============================================================================
# Este archivo implementa los endpoints de tratamientos:
#   - GET /tratamientos → Listar tratamientos
#   - GET /pacientes/{id}/tratamientos → Tratamientos de un paciente
#   - GET /tratamientos/{id} → Detalle de tratamiento
#   - POST /tratamientos → Crear tratamiento
#   - PUT /tratamientos/{id} → Editar tratamiento
#   - PATCH /tratamientos/{id}/status → Cambiar estado
#   - DELETE /tratamientos/{id} → Soft delete
#
# PERMISOS: Solo Admin y Podologo (datos clínicos)
# =============================================================================

from typing import List, Optional
from datetime import date, datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api.deps.database import get_core_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Tratamiento, Paciente, EvolucionClinica


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/tratamientos", tags=["Tratamientos"])


# =============================================================================
# SCHEMAS
# =============================================================================

class TratamientoBase(BaseModel):
    """Campos base de tratamiento"""
    paciente_id: int
    motivo_consulta_principal: str = Field(..., min_length=3)
    diagnostico_inicial: Optional[str] = None
    fecha_inicio: Optional[date] = None
    estado_tratamiento: str = Field(
        default="En Curso",
        pattern="^(En Curso|Alta|Pausado|Abandonado)$"
    )
    plan_general: Optional[str] = None


class TratamientoCreate(TratamientoBase):
    """Request para crear tratamiento"""
    pass


class TratamientoUpdate(BaseModel):
    """Request para actualizar tratamiento"""
    motivo_consulta_principal: Optional[str] = Field(None, min_length=3)
    diagnostico_inicial: Optional[str] = None
    estado_tratamiento: Optional[str] = Field(
        None, pattern="^(En Curso|Alta|Pausado|Abandonado)$"
    )
    plan_general: Optional[str] = None


class TratamientoStatusUpdate(BaseModel):
    """Request para cambiar estado"""
    estado_tratamiento: str = Field(
        ..., pattern="^(En Curso|Alta|Pausado|Abandonado)$"
    )


class TratamientoResponse(BaseModel):
    """Response de tratamiento"""
    id_tratamiento: int
    id_clinica: int
    paciente_id: int
    motivo_consulta_principal: str
    diagnostico_inicial: Optional[str] = None
    fecha_inicio: Optional[date] = None
    estado_tratamiento: str
    plan_general: Optional[str] = None
    created_at: Optional[datetime] = None
    
    # Datos agregados
    paciente_nombre: Optional[str] = None
    total_evoluciones: Optional[int] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# HELPERS
# =============================================================================

def enrich_tratamiento_response(tratamiento: Tratamiento, db: Session) -> dict:
    """Agrega datos del paciente y conteo de evoluciones"""
    response = TratamientoResponse.model_validate(tratamiento).model_dump()
    
    # Agregar nombre del paciente
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == tratamiento.paciente_id
    ).first()
    if paciente:
        response["paciente_nombre"] = f"{paciente.nombres} {paciente.apellidos}"
    
    # Contar evoluciones
    total_evoluciones = db.query(EvolucionClinica).filter(
        EvolucionClinica.tratamiento_id == tratamiento.id_tratamiento
    ).count()
    response["total_evoluciones"] = total_evoluciones
    
    return response


# =============================================================================
# ENDPOINT: GET /tratamientos
# =============================================================================

@router.get("")
async def list_tratamientos(
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    paciente_id: Optional[int] = Query(None, description="Filtrar por paciente"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista todos los tratamientos.
    
    **Permisos:** Solo Admin y Podologo
    
    **Filtros:**
    - estado: Filtrar por estado del tratamiento
    - paciente_id: Filtrar por paciente
    """
    query = db.query(Tratamiento).filter(Tratamiento.deleted_at.is_(None))
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(Tratamiento.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if estado:
        query = query.filter(Tratamiento.estado_tratamiento == estado)
    if paciente_id:
        query = query.filter(Tratamiento.paciente_id == paciente_id)
    
    # Ordenar por más reciente
    query = query.order_by(Tratamiento.created_at.desc())
    
    total = query.count()
    tratamientos = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "tratamientos": [enrich_tratamiento_response(t, db) for t in tratamientos]
    }


# =============================================================================
# ENDPOINT: GET /tratamientos/{id}
# =============================================================================

@router.get("/{tratamiento_id}")
async def get_tratamiento(
    tratamiento_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Obtiene detalle de un tratamiento con sus evoluciones.
    
    **Permisos:** Solo Admin y Podologo
    """
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == tratamiento_id,
        Tratamiento.deleted_at.is_(None)
    ).first()
    
    if not tratamiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and tratamiento.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tratamiento"
        )
    
    response = enrich_tratamiento_response(tratamiento, db)
    
    # Agregar lista de evoluciones
    evoluciones = db.query(EvolucionClinica).filter(
        EvolucionClinica.tratamiento_id == tratamiento_id
    ).order_by(EvolucionClinica.fecha_visita.desc()).all()
    
    response["evoluciones"] = [
        {
            "id_evolucion": e.id_evolucion,
            "fecha_visita": e.fecha_visita,
            "nota_subjetiva": e.nota_subjetiva[:100] + "..." if e.nota_subjetiva and len(e.nota_subjetiva) > 100 else e.nota_subjetiva
        }
        for e in evoluciones
    ]
    
    return response


# =============================================================================
# ENDPOINT: POST /tratamientos
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tratamiento(
    data: TratamientoCreate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Crea un nuevo tratamiento para un paciente.
    
    **Permisos:** Solo Admin y Podologo
    
    **Nota:** Un paciente puede tener múltiples tratamientos activos.
    """
    # Verificar que el paciente existe
    paciente = db.query(Paciente).filter(
        Paciente.id_paciente == data.paciente_id,
        Paciente.deleted_at.is_(None)
    ).first()
    
    if not paciente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Paciente no encontrado"
        )
    
    # Crear tratamiento
    tratamiento = Tratamiento(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        fecha_inicio=data.fecha_inicio or date.today()
    )
    
    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)
    
    return enrich_tratamiento_response(tratamiento, db)


# =============================================================================
# ENDPOINT: PUT /tratamientos/{id}
# =============================================================================

@router.put("/{tratamiento_id}")
async def update_tratamiento(
    tratamiento_id: int,
    data: TratamientoUpdate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Actualiza un tratamiento existente.
    
    **Permisos:** Solo Admin y Podologo
    """
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == tratamiento_id,
        Tratamiento.deleted_at.is_(None)
    ).first()
    
    if not tratamiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and tratamiento.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tratamiento"
        )
    
    # Actualizar campos
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(tratamiento, field, value)
    
    tratamiento.updated_by = current_user.id_usuario
    db.commit()
    db.refresh(tratamiento)
    
    return enrich_tratamiento_response(tratamiento, db)


# =============================================================================
# ENDPOINT: PATCH /tratamientos/{id}/status
# =============================================================================

@router.patch("/{tratamiento_id}/status")
async def update_tratamiento_status(
    tratamiento_id: int,
    data: TratamientoStatusUpdate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Cambia el estado de un tratamiento.
    
    **Permisos:** Solo Admin y Podologo
    
    **Estados válidos:**
    - En Curso: Tratamiento activo
    - Alta: Paciente dado de alta (curado)
    - Pausado: Temporalmente detenido
    - Abandonado: El paciente dejó de asistir
    """
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == tratamiento_id,
        Tratamiento.deleted_at.is_(None)
    ).first()
    
    if not tratamiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and tratamiento.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tratamiento"
        )
    
    tratamiento.estado_tratamiento = data.estado_tratamiento
    tratamiento.updated_by = current_user.id_usuario
    db.commit()
    db.refresh(tratamiento)
    
    return {
        "message": f"Estado actualizado a '{data.estado_tratamiento}'",
        "tratamiento": enrich_tratamiento_response(tratamiento, db)
    }


# =============================================================================
# ENDPOINT: DELETE /tratamientos/{id}
# =============================================================================

@router.delete("/{tratamiento_id}")
async def soft_delete_tratamiento(
    tratamiento_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Desactiva un tratamiento (soft delete).
    
    **Permisos:** Solo Admin y Podologo
    """
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == tratamiento_id,
        Tratamiento.deleted_at.is_(None)
    ).first()
    
    if not tratamiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )
    
    # Verificar clínica
    if current_user.clinica_id and tratamiento.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este tratamiento"
        )
    
    # Soft delete
    tratamiento.deleted_at = datetime.now(timezone.utc)
    tratamiento.updated_by = current_user.id_usuario
    db.commit()
    
    return {"message": "Tratamiento desactivado", "id": tratamiento_id}
