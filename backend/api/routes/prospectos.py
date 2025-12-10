# =============================================================================
# backend/api/routes/prospectos.py
# CRUD de Prospectos (Solicitudes de personas que llaman)
# =============================================================================
# Este archivo implementa los endpoints de prospectos:
#   - GET /prospectos → Listar prospectos
#   - GET /prospectos/{id} → Detalle de prospecto
#   - POST /prospectos → Crear prospecto
#   - PUT /prospectos/{id} → Editar prospecto
#   - POST /prospectos/{id}/convertir → Convertir a paciente
#
# PERMISOS: Todos los roles (recepción puede gestionar prospectos)
# =============================================================================

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_ops_db, get_core_db
from backend.api.deps.permissions import require_role, ALL_ROLES
from backend.schemas.auth.models import SysUsuario
from backend.schemas.ops.models import SolicitudProspecto
from backend.schemas.core.models import Paciente


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/prospectos", tags=["Prospectos"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ProspectoBase(BaseModel):
    """Campos base de prospecto"""
    nombre_prospecto: str = Field(..., min_length=2, max_length=150)
    telefono_contacto: str = Field(..., min_length=10)
    email_contacto: Optional[EmailStr] = None
    interes_servicio_id: Optional[int] = None
    notas_adicionales: Optional[str] = None
    fecha_preferida: Optional[datetime] = None


class ProspectoCreate(ProspectoBase):
    """Request para crear prospecto"""
    pass


class ProspectoUpdate(BaseModel):
    """Request para actualizar prospecto"""
    nombre_prospecto: Optional[str] = Field(None, min_length=2, max_length=150)
    telefono_contacto: Optional[str] = Field(None, min_length=10)
    email_contacto: Optional[EmailStr] = None
    interes_servicio_id: Optional[int] = None
    notas_adicionales: Optional[str] = None
    fecha_preferida: Optional[datetime] = None
    status_solicitud: Optional[str] = Field(
        None, pattern="^(Pendiente|Contactado|Agendado|Convertido|Rechazado)$"
    )


class ProspectoResponse(BaseModel):
    """Response de prospecto"""
    id_solicitud: int
    id_clinica: int
    nombre_prospecto: str
    telefono_contacto: str
    email_contacto: Optional[str] = None
    interes_servicio_id: Optional[int] = None
    notas_adicionales: Optional[str] = None
    status_solicitud: str
    fecha_preferida: Optional[datetime] = None
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ConvertirProspectoRequest(BaseModel):
    """Request para convertir prospecto a paciente"""
    apellidos: str = Field(..., min_length=2)
    fecha_nacimiento: Optional[str] = None  # formato: YYYY-MM-DD
    sexo: Optional[str] = Field(None, pattern="^[MF]$")


# =============================================================================
# ENDPOINT: GET /prospectos
# =============================================================================

@router.get("")
async def list_prospectos(
    status_solicitud: Optional[str] = Query(None, description="Filtrar por estado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Lista los prospectos (solicitudes de contacto).
    
    **Permisos:** Todos los roles
    """
    query = db.query(SolicitudProspecto)
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(SolicitudProspecto.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if status_solicitud:
        query = query.filter(SolicitudProspecto.status_solicitud == status_solicitud)
    
    # Ordenar por más recientes
    query = query.order_by(SolicitudProspecto.fecha_solicitud.desc())
    
    total = query.count()
    prospectos = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "prospectos": [ProspectoResponse.model_validate(p) for p in prospectos]
    }


# =============================================================================
# ENDPOINT: GET /prospectos/{id}
# =============================================================================

@router.get("/{prospecto_id}")
async def get_prospecto(
    prospecto_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Obtiene detalle de un prospecto.
    
    **Permisos:** Todos los roles
    """
    prospecto = db.query(SolicitudProspecto).filter(
        SolicitudProspecto.id_solicitud == prospecto_id
    ).first()
    
    if not prospecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospecto no encontrado"
        )
    
    return ProspectoResponse.model_validate(prospecto)


# =============================================================================
# ENDPOINT: POST /prospectos
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_prospecto(
    data: ProspectoCreate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Registra un nuevo prospecto (persona que llamó preguntando).
    
    **Permisos:** Todos los roles
    """
    prospecto = SolicitudProspecto(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        status_solicitud="Pendiente"
    )
    
    db.add(prospecto)
    db.commit()
    db.refresh(prospecto)
    
    return ProspectoResponse.model_validate(prospecto)


# =============================================================================
# ENDPOINT: PUT /prospectos/{id}
# =============================================================================

@router.put("/{prospecto_id}")
async def update_prospecto(
    prospecto_id: int,
    data: ProspectoUpdate,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Actualiza un prospecto.
    
    **Permisos:** Todos los roles
    """
    prospecto = db.query(SolicitudProspecto).filter(
        SolicitudProspecto.id_solicitud == prospecto_id
    ).first()
    
    if not prospecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospecto no encontrado"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(prospecto, field, value)
    
    db.commit()
    db.refresh(prospecto)
    
    return ProspectoResponse.model_validate(prospecto)


# =============================================================================
# ENDPOINT: POST /prospectos/{id}/convertir
# =============================================================================

@router.post("/{prospecto_id}/convertir")
async def convertir_prospecto(
    prospecto_id: int,
    data: ConvertirProspectoRequest,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    ops_db: Session = Depends(get_ops_db),
    core_db: Session = Depends(get_core_db)
):
    """
    Convierte un prospecto en paciente.
    
    **Permisos:** Todos los roles
    
    **Proceso:**
    1. Busca el prospecto
    2. Crea un nuevo paciente con los datos
    3. Actualiza el status del prospecto a "Convertido"
    4. Retorna el nuevo paciente
    """
    from datetime import date
    
    # Buscar prospecto
    prospecto = ops_db.query(SolicitudProspecto).filter(
        SolicitudProspecto.id_solicitud == prospecto_id
    ).first()
    
    if not prospecto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prospecto no encontrado"
        )
    
    if prospecto.status_solicitud == "Convertido":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este prospecto ya fue convertido a paciente"
        )
    
    # Parsear nombre (asumiendo "Nombre Apellido" o solo "Nombre")
    nombre_parts = prospecto.nombre_prospecto.split(" ", 1)
    nombres = nombre_parts[0]
    
    # Crear paciente en core_db
    paciente = Paciente(
        nombres=nombres,
        apellidos=data.apellidos,
        telefono=prospecto.telefono_contacto,
        email=prospecto.email_contacto,
        fecha_nacimiento=date.fromisoformat(data.fecha_nacimiento) if data.fecha_nacimiento else date(1990, 1, 1),
        sexo=data.sexo,
        id_clinica=current_user.clinica_id or 1,
        created_by=current_user.id_usuario
    )
    
    core_db.add(paciente)
    core_db.commit()
    core_db.refresh(paciente)
    
    # Actualizar prospecto
    prospecto.status_solicitud = "Convertido"
    ops_db.commit()
    
    return {
        "message": "Prospecto convertido a paciente exitosamente",
        "paciente_id": paciente.id_paciente,
        "nombres": paciente.nombres,
        "apellidos": paciente.apellidos
    }
