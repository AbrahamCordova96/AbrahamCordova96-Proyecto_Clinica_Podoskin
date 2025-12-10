# =============================================================================
# backend/api/routes/podologos.py
# CRUD de Podólogos
# =============================================================================
# Este archivo implementa los endpoints de podólogos:
#   - GET /podologos → Listar podólogos
#   - GET /podologos/{id} → Detalle de podólogo
#   - POST /podologos → Crear podólogo (Solo Admin)
#   - PUT /podologos/{id} → Editar podólogo (Admin o self)
#   - DELETE /podologos/{id} → Desactivar podólogo (Solo Admin)
#
# PERMISOS:
#   - Lectura: Todos los roles
#   - Creación/Eliminación: Solo Admin
#   - Edición: Admin o el propio podólogo
# =============================================================================

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr

from backend.api.deps.database import get_ops_db
from backend.api.deps.permissions import require_role, ALL_ROLES, CLINICAL_ROLES, ROLE_ADMIN
from backend.schemas.auth.models import SysUsuario
from backend.schemas.ops.models import Podologo


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/podologos", tags=["Podólogos"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PodologoBase(BaseModel):
    """Campos base de podólogo"""
    nombre_completo: str = Field(..., min_length=3, max_length=150)
    especialidad: Optional[str] = None
    cedula_profesional: Optional[str] = None


class PodologoCreate(PodologoBase):
    """Request para crear podólogo"""
    usuario_id: Optional[int] = None  # Enlazar con sys_usuarios


class PodologoUpdate(BaseModel):
    """Request para actualizar podólogo"""
    nombre_completo: Optional[str] = Field(None, min_length=3, max_length=150)
    especialidad: Optional[str] = None
    cedula_profesional: Optional[str] = None


class PodologoResponse(BaseModel):
    """Response de podólogo"""
    id_podologo: int
    id_clinica: int
    nombre_completo: str
    especialidad: Optional[str] = None
    cedula_profesional: Optional[str] = None
    activo: bool
    usuario_sistema_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT: GET /podologos
# =============================================================================

@router.get("")
async def list_podologos(
    activo: Optional[bool] = Query(True, description="Filtrar por activos"),
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Lista los podólogos de la clínica.
    
    **Permisos:** Todos los roles
    """
    query = db.query(Podologo)
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(Podologo.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if activo is not None:
        query = query.filter(Podologo.activo == activo)
    
    podologos = query.order_by(Podologo.nombre_completo).all()
    
    return {
        "total": len(podologos),
        "podologos": [PodologoResponse.model_validate(p) for p in podologos]
    }


# =============================================================================
# ENDPOINT: GET /podologos/{id}
# =============================================================================

@router.get("/{podologo_id}")
async def get_podologo(
    podologo_id: int,
    current_user: SysUsuario = Depends(require_role(ALL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Obtiene detalle de un podólogo.
    
    **Permisos:** Todos los roles
    """
    podologo = db.query(Podologo).filter(
        Podologo.id_podologo == podologo_id
    ).first()
    
    if not podologo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podólogo no encontrado"
        )
    
    return PodologoResponse.model_validate(podologo)


# =============================================================================
# ENDPOINT: POST /podologos
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_podologo(
    data: PodologoCreate,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_ops_db)
):
    """
    Crea un nuevo podólogo.
    
    **Permisos:** Solo Admin
    """
    podologo = Podologo(
        **data.model_dump(),
        id_clinica=current_user.clinica_id or 1,
        activo=True
    )
    
    db.add(podologo)
    db.commit()
    db.refresh(podologo)
    
    return PodologoResponse.model_validate(podologo)


# =============================================================================
# ENDPOINT: PUT /podologos/{id}
# =============================================================================

@router.put("/{podologo_id}")
async def update_podologo(
    podologo_id: int,
    data: PodologoUpdate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_ops_db)
):
    """
    Actualiza un podólogo.
    
    **Permisos:** 
    - Admin: Puede editar cualquier podólogo
    - Podologo: Solo puede editar su propio perfil
    """
    podologo = db.query(Podologo).filter(
        Podologo.id_podologo == podologo_id
    ).first()
    
    if not podologo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podólogo no encontrado"
        )
    
    # Si no es admin, verificar que sea el propio podólogo
    if current_user.rol != ROLE_ADMIN:
        if podologo.usuario_id != current_user.id_usuario:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes editar tu propio perfil"
            )
    
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(podologo, field, value)
    
    db.commit()
    db.refresh(podologo)
    
    return PodologoResponse.model_validate(podologo)


# =============================================================================
# ENDPOINT: DELETE /podologos/{id}
# =============================================================================

@router.delete("/{podologo_id}")
async def delete_podologo(
    podologo_id: int,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_ops_db)
):
    """
    Desactiva un podólogo.
    
    **Permisos:** Solo Admin
    
    **Nota:** No elimina, solo desactiva (activo=False).
    """
    podologo = db.query(Podologo).filter(
        Podologo.id_podologo == podologo_id
    ).first()
    
    if not podologo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Podólogo no encontrado"
        )
    
    podologo.activo = False
    db.commit()
    
    return {"message": "Podólogo desactivado", "id": podologo_id}
