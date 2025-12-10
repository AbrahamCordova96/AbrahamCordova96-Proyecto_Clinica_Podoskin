# =============================================================================
# backend/api/routes/servicios.py
# CRUD del Catálogo de Servicios
# =============================================================================
# Este archivo implementa los endpoints del catálogo de servicios:
#   - GET /servicios → Listar servicios
#   - GET /servicios/{id} → Detalle de servicio
#   - POST /servicios → Crear servicio (Admin/Podologo)
#   - PUT /servicios/{id} → Editar servicio (Admin/Podologo)
#   - DELETE /servicios/{id} → Desactivar servicio (Solo Admin)
#
# PERMISOS:
#   - Lectura: Todos los roles
#   - Escritura: Admin y Podologo
#   - Eliminación: Solo Admin
# =============================================================================

from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api.deps.database import get_ops_db
from backend.api.deps.permissions import require_role, ALL_ROLES, CLINICAL_ROLES, ROLE_ADMIN
from backend.schemas.auth.models import SysUsuario
from backend.schemas.ops.models import CatalogoServicio


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/servicios", tags=["Catálogo de Servicios"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ServicioBase(BaseModel):
    """Campos base de servicio"""
    nombre_servicio: str = Field(..., min_length=3, max_length=100)
    descripcion: Optional[str] = None
    precio_base: Decimal = Field(..., gt=0)
    duracion_minutos: int = Field(default=30, ge=15, le=180)
    categoria: Optional[str] = None


class ServicioCreate(ServicioBase):
    """Request para crear servicio"""
    pass


class ServicioUpdate(BaseModel):
    """Request para actualizar servicio"""
    nombre_servicio: Optional[str] = Field(None, min_length=3, max_length=100)
    descripcion: Optional[str] = None
    precio_base: Optional[Decimal] = Field(None, gt=0)
    duracion_estimada_min: Optional[int] = Field(None, ge=15, le=180)
    categoria: Optional[str] = None


class ServicioResponse(BaseModel):
    """Response de servicio"""
    id_servicio: int
    id_clinica: int
    nombre_servicio: str
    descripcion: Optional[str] = None
    precio_base: Decimal
    duracion_minutos: int
    categoria: Optional[str] = None
    activo: bool
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT: GET /servicios
# =============================================================================

@router.get("")
async def list_servicios(
    activo: Optional[bool] = Query(True, description="Filtrar por activos"),
    categoria: Optional[str] = Query(None, description="Filtrar por categoría"),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Lista el catálogo de servicios.
    
    **Permisos:** Todos los roles
    """
    query = db.query(CatalogoServicio)
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(CatalogoServicio.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if activo is not None:
        query = query.filter(CatalogoServicio.activo == activo)
    if categoria:
        query = query.filter(CatalogoServicio.categoria == categoria)
    
    servicios = query.order_by(CatalogoServicio.nombre_servicio).all()
    
    return {
        "total": len(servicios),
        "servicios": [ServicioResponse.model_validate(s) for s in servicios]
    }


# =============================================================================
# ENDPOINT: GET /servicios/{id}
# =============================================================================

@router.get("/{servicio_id}")
async def get_servicio(
    servicio_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Obtiene detalle de un servicio.
    
    **Permisos:** Todos los roles
    """
    servicio = db.query(CatalogoServicio).filter(
        CatalogoServicio.id_servicio == servicio_id
    ).first()
    
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )
    
    return ServicioResponse.model_validate(servicio)


# =============================================================================
# ENDPOINT: POST /servicios
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_servicio(
    data: ServicioCreate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Crea un nuevo servicio en el catálogo.
    
    **Permisos:** Solo Admin y Podologo
    """
    servicio = CatalogoServicio(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        activo=True
    )
    
    db.add(servicio)
    db.commit()
    db.refresh(servicio)
    
    return ServicioResponse.model_validate(servicio)


# =============================================================================
# ENDPOINT: PUT /servicios/{id}
# =============================================================================

@router.put("/{servicio_id}")
async def update_servicio(
    servicio_id: int,
    data: ServicioUpdate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Actualiza un servicio del catálogo.
    
    **Permisos:** Solo Admin y Podologo
    """
    servicio = db.query(CatalogoServicio).filter(
        CatalogoServicio.id_servicio == servicio_id
    ).first()
    
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(servicio, field, value)
    
    db.commit()
    db.refresh(servicio)
    
    return ServicioResponse.model_validate(servicio)


# =============================================================================
# ENDPOINT: DELETE /servicios/{id}
# =============================================================================

@router.delete("/{servicio_id}")
async def delete_servicio(
    servicio_id: int,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_ops_db)
):
    """
    Desactiva un servicio del catálogo.
    
    **Permisos:** Solo Admin
    
    **Nota:** No elimina, solo desactiva (activo=False).
    """
    servicio = db.query(CatalogoServicio).filter(
        CatalogoServicio.id_servicio == servicio_id
    ).first()
    
    if not servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio no encontrado"
        )
    
    servicio.activo = False
    db.commit()
    
    return {"message": "Servicio desactivado", "id": servicio_id}
