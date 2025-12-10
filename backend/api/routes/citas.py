# =============================================================================
# backend/api/routes/citas.py
# CRUD de Citas (Agenda) con control de acceso por rol
# =============================================================================
# Este archivo implementa los endpoints de citas:
#   - GET /citas → Listar citas con filtros
#   - GET /citas/agenda/{fecha} → Agenda de un día
#   - GET /citas/disponibilidad → Horarios disponibles
#   - GET /citas/{id} → Detalle de cita
#   - POST /citas → Crear cita
#   - PUT /citas/{id} → Editar cita
#   - PATCH /citas/{id}/status → Cambiar estado
#   - DELETE /citas/{id} → Cancelar cita
#
# PERMISOS: Todos los roles pueden gestionar citas
# =============================================================================

from typing import List, Optional
from datetime import date, time, datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel, Field

from backend.api.deps.database import get_ops_db
from backend.api.deps.permissions import require_role, ALL_ROLES
from backend.schemas.auth.models import SysUsuario
from backend.schemas.ops.models import Cita, Podologo, CatalogoServicio, SolicitudProspecto


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/citas", tags=["Citas"])


# =============================================================================
# SCHEMAS
# =============================================================================

class CitaBase(BaseModel):
    """Campos base de cita"""
    paciente_id: Optional[int] = None
    solicitud_id: Optional[int] = None  # Para prospectos
    podologo_id: int
    servicio_id: int
    fecha_cita: date
    hora_inicio: time
    hora_fin: time
    notas_agendamiento: Optional[str] = None


class CitaCreate(CitaBase):
    """Request para crear cita"""
    pass


class CitaUpdate(BaseModel):
    """Request para actualizar cita"""
    podologo_id: Optional[int] = None
    servicio_id: Optional[int] = None
    fecha_cita: Optional[date] = None
    hora_inicio: Optional[time] = None
    hora_fin: Optional[time] = None
    notas_agendamiento: Optional[str] = None


class CitaStatusUpdate(BaseModel):
    """Request para cambiar estado"""
    status: str = Field(
        ..., 
        pattern="^(Pendiente|Confirmada|En Sala|Realizada|Cancelada|No Asistió)$",
        description="Nuevo estado de la cita"
    )


class CitaResponse(BaseModel):
    """Response de cita"""
    id_cita: int
    id_clinica: int
    paciente_id: Optional[int] = None
    solicitud_id: Optional[int] = None
    podologo_id: int
    servicio_id: int
    fecha_cita: date
    hora_inicio: time
    hora_fin: time
    status: str
    notas_agendamiento: Optional[str] = None
    
    # Datos relacionados (se agregan después)
    podologo_nombre: Optional[str] = None
    servicio_nombre: Optional[str] = None
    
    class Config:
        from_attributes = True


class DisponibilidadSlot(BaseModel):
    """Un slot de disponibilidad"""
    hora_inicio: time
    hora_fin: time
    disponible: bool


class DisponibilidadResponse(BaseModel):
    """Response de disponibilidad"""
    fecha: date
    podologo_id: int
    podologo_nombre: str
    slots: List[DisponibilidadSlot]


# =============================================================================
# HELPERS
# =============================================================================

def enrich_cita_response(cita: Cita, db: Session) -> dict:
    """Agrega nombres de podólogo y servicio a la respuesta"""
    response = CitaResponse.model_validate(cita).model_dump()
    
    # Agregar nombre del podólogo
    podologo = db.query(Podologo).filter(
        Podologo.id_podologo == cita.podologo_id
    ).first()
    if podologo:
        response["podologo_nombre"] = podologo.nombre_completo
    
    # Agregar nombre del servicio
    servicio = db.query(CatalogoServicio).filter(
        CatalogoServicio.id_servicio == cita.servicio_id
    ).first()
    if servicio:
        response["servicio_nombre"] = servicio.nombre_servicio
    
    return response


# =============================================================================
# ENDPOINT: GET /citas
# =============================================================================

@router.get("")
async def list_citas(
    fecha_inicio: Optional[date] = Query(None, description="Filtrar desde fecha"),
    fecha_fin: Optional[date] = Query(None, description="Filtrar hasta fecha"),
    podologo_id: Optional[int] = Query(None, description="Filtrar por podólogo"),
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Lista citas con filtros opcionales.
    
    **Permisos:** Todos los roles
    
    **Filtros:**
    - fecha_inicio, fecha_fin: Rango de fechas
    - podologo_id: Filtrar por podólogo
    - status: Filtrar por estado
    """
    query = db.query(Cita).filter(Cita.deleted_at.is_(None))
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(Cita.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if fecha_inicio:
        query = query.filter(Cita.fecha_cita >= fecha_inicio)
    if fecha_fin:
        query = query.filter(Cita.fecha_cita <= fecha_fin)
    if podologo_id:
        query = query.filter(Cita.podologo_id == podologo_id)
    if status:
        query = query.filter(Cita.status == status)
    
    # Ordenar por fecha y hora
    query = query.order_by(Cita.fecha_cita, Cita.hora_inicio)
    
    total = query.count()
    citas = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "citas": [enrich_cita_response(c, db) for c in citas]
    }


# =============================================================================
# ENDPOINT: GET /citas/agenda/{fecha}
# =============================================================================

@router.get("/agenda/{fecha}")
async def get_agenda_dia(
    fecha: date,
    podologo_id: Optional[int] = Query(None, description="Filtrar por podólogo"),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Obtiene la agenda de un día específico.
    
    **Permisos:** Todos los roles
    
    **Retorna:** Lista de citas ordenadas por hora
    """
    query = db.query(Cita).filter(
        Cita.fecha_cita == fecha,
        Cita.deleted_at.is_(None),
        Cita.status.notin_(["Cancelada", "No Asistió"])
    )
    
    if current_user.clinica_id:
        query = query.filter(Cita.id_clinica == current_user.clinica_id)
    
    if podologo_id:
        query = query.filter(Cita.podologo_id == podologo_id)
    
    citas = query.order_by(Cita.hora_inicio).all()
    
    return {
        "fecha": fecha,
        "total_citas": len(citas),
        "citas": [enrich_cita_response(c, db) for c in citas]
    }


# =============================================================================
# ENDPOINT: GET /citas/disponibilidad
# =============================================================================

@router.get("/disponibilidad")
async def get_disponibilidad(
    fecha: date = Query(..., description="Fecha a consultar"),
    podologo_id: int = Query(..., description="ID del podólogo"),
    duracion_minutos: int = Query(30, description="Duración del servicio"),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Consulta horarios disponibles para un podólogo en una fecha.
    
    **Permisos:** Todos los roles
    
    **Parámetros:**
    - fecha: Fecha a consultar
    - podologo_id: ID del podólogo
    - duracion_minutos: Duración del servicio a agendar
    
    **Retorna:** Lista de slots con disponibilidad
    """
    # Verificar que el podólogo existe
    podologo = db.query(Podologo).filter(
        Podologo.id_podologo == podologo_id,
        Podologo.activo == True
    ).first()
    
    if not podologo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podólogo no encontrado o inactivo"
        )
    
    # Obtener citas existentes del día
    citas_dia = db.query(Cita).filter(
        Cita.podologo_id == podologo_id,
        Cita.fecha_cita == fecha,
        Cita.deleted_at.is_(None),
        Cita.status.notin_(["Cancelada", "No Asistió"])
    ).all()
    
    # Definir horario de trabajo (9:00 AM - 7:00 PM)
    hora_inicio_dia = time(9, 0)
    hora_fin_dia = time(19, 0)
    
    # Generar slots de 30 minutos
    slots = []
    current_time = datetime.combine(fecha, hora_inicio_dia)
    end_time = datetime.combine(fecha, hora_fin_dia)
    
    while current_time + timedelta(minutes=duracion_minutos) <= end_time:
        slot_inicio = current_time.time()
        slot_fin = (current_time + timedelta(minutes=duracion_minutos)).time()
        
        # Verificar si el slot está disponible
        disponible = True
        for cita in citas_dia:
            # Verificar solapamiento
            if not (slot_fin <= cita.hora_inicio or slot_inicio >= cita.hora_fin):
                disponible = False
                break
        
        slots.append(DisponibilidadSlot(
            hora_inicio=slot_inicio,
            hora_fin=slot_fin,
            disponible=disponible
        ))
        
        current_time += timedelta(minutes=30)
    
    return DisponibilidadResponse(
        fecha=fecha,
        podologo_id=podologo_id,
        podologo_nombre=podologo.nombre_completo,
        slots=slots
    )


# =============================================================================
# ENDPOINT: GET /citas/{id}
# =============================================================================

@router.get("/{cita_id}")
async def get_cita(
    cita_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Obtiene detalle de una cita.
    
    **Permisos:** Todos los roles
    """
    cita = db.query(Cita).filter(
        Cita.id_cita == cita_id,
        Cita.deleted_at.is_(None)
    ).first()
    
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and cita.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta cita"
        )
    
    return enrich_cita_response(cita, db)


# =============================================================================
# ENDPOINT: POST /citas
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cita(
    data: CitaCreate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Crea una nueva cita.
    
    **Permisos:** Todos los roles
    
    **Validaciones:**
    - Debe tener paciente_id O solicitud_id (no ambos)
    - hora_fin debe ser después de hora_inicio
    - No puede haber solapamiento con otras citas del podólogo
    """
    # Validar que tiene paciente O prospecto
    if data.paciente_id and data.solicitud_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Una cita es para un paciente O un prospecto, no ambos"
        )
    
    if not data.paciente_id and not data.solicitud_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debe especificar paciente_id o solicitud_id"
        )
    
    # Validar horarios
    if data.hora_fin <= data.hora_inicio:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="hora_fin debe ser después de hora_inicio"
        )
    
    # Verificar disponibilidad (no solapamiento)
    conflicto = db.query(Cita).filter(
        Cita.podologo_id == data.podologo_id,
        Cita.fecha_cita == data.fecha_cita,
        Cita.deleted_at.is_(None),
        Cita.status.notin_(["Cancelada", "No Asistió"]),
        # Verificar solapamiento de horarios
        and_(
            Cita.hora_inicio < data.hora_fin,
            Cita.hora_fin > data.hora_inicio
        )
    ).first()
    
    if conflicto:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El podólogo ya tiene una cita de {conflicto.hora_inicio} a {conflicto.hora_fin}"
        )
    
    # Crear cita
    cita = Cita(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        status="Confirmada",
        created_by=current_user.id_usuario
    )
    
    db.add(cita)
    db.commit()
    db.refresh(cita)
    
    return enrich_cita_response(cita, db)


# =============================================================================
# ENDPOINT: PUT /citas/{id}
# =============================================================================

@router.put("/{cita_id}")
async def update_cita(
    cita_id: int,
    data: CitaUpdate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Actualiza una cita existente.
    
    **Permisos:** Todos los roles
    """
    cita = db.query(Cita).filter(
        Cita.id_cita == cita_id,
        Cita.deleted_at.is_(None)
    ).first()
    
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and cita.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta cita"
        )
    
    # Actualizar campos
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(cita, field, value)
    
    db.commit()
    db.refresh(cita)
    
    return enrich_cita_response(cita, db)


# =============================================================================
# ENDPOINT: PATCH /citas/{id}/status
# =============================================================================

@router.patch("/{cita_id}/status")
async def update_cita_status(
    cita_id: int,
    data: CitaStatusUpdate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Cambia el estado de una cita.
    
    **Permisos:** Todos los roles
    
    **Estados válidos:**
    - Pendiente → Confirmada → En Sala → Realizada
    - Cancelada, No Asistió (finales)
    """
    cita = db.query(Cita).filter(
        Cita.id_cita == cita_id,
        Cita.deleted_at.is_(None)
    ).first()
    
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and cita.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta cita"
        )
    
    cita.status = data.status
    db.commit()
    db.refresh(cita)
    
    return {
        "message": f"Estado actualizado a '{data.status}'",
        "cita": enrich_cita_response(cita, db)
    }


# =============================================================================
# ENDPOINT: DELETE /citas/{id}
# =============================================================================

@router.delete("/{cita_id}")
async def cancel_cita(
    cita_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Cancela una cita.
    
    **Permisos:** Todos los roles
    
    La cita no se elimina, solo cambia su estado a "Cancelada".
    """
    cita = db.query(Cita).filter(
        Cita.id_cita == cita_id,
        Cita.deleted_at.is_(None)
    ).first()
    
    if not cita:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cita no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and cita.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta cita"
        )
    
    # Cambiar a cancelada
    cita.status = "Cancelada"
    cita.deleted_at = datetime.now(timezone.utc)
    db.commit()
    
    return {"message": "Cita cancelada", "id": cita_id}
