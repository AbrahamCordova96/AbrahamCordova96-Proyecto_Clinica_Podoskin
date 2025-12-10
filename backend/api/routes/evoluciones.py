# =============================================================================
# backend/api/routes/evoluciones.py
# CRUD de Evoluciones Clínicas (Notas SOAP por visita)
# =============================================================================
# Este archivo implementa los endpoints de evoluciones:
#   - GET /evoluciones → Listar evoluciones
#   - GET /tratamientos/{id}/evoluciones → Evoluciones de un tratamiento
#   - GET /evoluciones/{id} → Detalle de evolución
#   - POST /evoluciones → Crear evolución
#   - PUT /evoluciones/{id} → Editar evolución
#   - DELETE /evoluciones/{id} → Soft delete (solo Admin)
#
# PERMISOS: Solo Admin y Podologo (datos clínicos)
# =============================================================================

from typing import List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.api.deps.database import get_core_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES, ROLE_ADMIN
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import EvolucionClinica, Tratamiento, EvidenciaFotografica


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/evoluciones", tags=["Evoluciones Clínicas"])


# =============================================================================
# SCHEMAS
# =============================================================================

class SignosVitales(BaseModel):
    """Signos vitales de la visita"""
    presion_arterial: Optional[str] = None
    frecuencia_cardiaca: Optional[int] = Field(None, ge=40, le=200)
    temperatura: Optional[float] = Field(None, ge=35, le=42)
    glucosa: Optional[int] = Field(None, ge=50, le=400)


class EvolucionBase(BaseModel):
    """Campos base de evolución clínica"""
    tratamiento_id: int
    cita_id: Optional[int] = None
    podologo_id: Optional[int] = None
    nota_subjetiva: Optional[str] = None
    nota_objetiva: Optional[str] = None
    analisis_texto: Optional[str] = None
    plan_texto: Optional[str] = None
    signos_vitales_visita: Optional[SignosVitales] = None


class EvolucionCreate(EvolucionBase):
    """Request para crear evolución"""
    pass


class EvolucionUpdate(BaseModel):
    """Request para actualizar evolución"""
    nota_subjetiva: Optional[str] = None
    nota_objetiva: Optional[str] = None
    analisis_texto: Optional[str] = None
    plan_texto: Optional[str] = None
    signos_vitales_visita: Optional[SignosVitales] = None


class EvolucionResponse(BaseModel):
    """Response de evolución"""
    id_evolucion: int
    id_clinica: int
    tratamiento_id: int
    cita_id: Optional[int] = None
    podologo_id: Optional[int] = None
    fecha_visita: Optional[datetime] = None
    nota_subjetiva: Optional[str] = None
    nota_objetiva: Optional[str] = None
    analisis_texto: Optional[str] = None
    plan_texto: Optional[str] = None
    signos_vitales_visita: Optional[dict] = None
    created_by: Optional[int] = None
    
    # Datos agregados
    total_evidencias: Optional[int] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# HELPERS
# =============================================================================

def enrich_evolucion_response(evolucion: EvolucionClinica, db: Session) -> dict:
    """Agrega conteo de evidencias fotográficas"""
    response = EvolucionResponse.model_validate(evolucion).model_dump()
    
    # Contar evidencias
    total_evidencias = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.evolucion_id == evolucion.id_evolucion
    ).count()
    response["total_evidencias"] = total_evidencias
    
    return response


# =============================================================================
# ENDPOINT: GET /evoluciones
# =============================================================================

@router.get("")
async def list_evoluciones(
    tratamiento_id: Optional[int] = Query(None, description="Filtrar por tratamiento"),
    podologo_id: Optional[int] = Query(None, description="Filtrar por podólogo"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista evoluciones clínicas.
    
    **Permisos:** Solo Admin y Podologo
    
    **Filtros:**
    - tratamiento_id: Filtrar por tratamiento
    - podologo_id: Filtrar por podólogo que atendió
    """
    query = db.query(EvolucionClinica)
    
    # Filtrar por clínica
    if current_user.clinica_id:
        query = query.filter(EvolucionClinica.id_clinica == current_user.clinica_id)
    
    # Aplicar filtros
    if tratamiento_id:
        query = query.filter(EvolucionClinica.tratamiento_id == tratamiento_id)
    if podologo_id:
        query = query.filter(EvolucionClinica.podologo_id == podologo_id)
    
    # Ordenar por más reciente
    query = query.order_by(EvolucionClinica.fecha_visita.desc())
    
    total = query.count()
    evoluciones = query.offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "evoluciones": [enrich_evolucion_response(e, db) for e in evoluciones]
    }


# =============================================================================
# ENDPOINT: GET /evoluciones/{id}
# =============================================================================

@router.get("/{evolucion_id}")
async def get_evolucion(
    evolucion_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Obtiene detalle de una evolución clínica.
    
    **Permisos:** Solo Admin y Podologo
    """
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evolucion_id
    ).first()
    
    if not evolucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evolución no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evolución"
        )
    
    response = enrich_evolucion_response(evolucion, db)
    
    # Agregar lista de evidencias
    evidencias = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.evolucion_id == evolucion_id
    ).all()
    
    response["evidencias"] = [
        {
            "id_evidencia": e.id_evidencia,
            "etapa_tratamiento": e.etapa_tratamiento,
            "url_archivo": e.url_archivo,
            "fecha_captura": e.fecha_captura
        }
        for e in evidencias
    ]
    
    return response


# =============================================================================
# ENDPOINT: POST /evoluciones
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evolucion(
    data: EvolucionCreate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Crea una nueva evolución clínica (nota SOAP).
    
    **Permisos:** Solo Admin y Podologo
    
    **Campos SOAP:**
    - nota_subjetiva: Lo que el paciente reporta
    - nota_objetiva: Lo que el podólogo observa
    - analisis_texto: Diagnóstico/análisis
    - plan_texto: Plan de tratamiento
    """
    # Verificar que el tratamiento existe
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == data.tratamiento_id,
        Tratamiento.deleted_at.is_(None)
    ).first()
    
    if not tratamiento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tratamiento no encontrado"
        )
    
    # Preparar datos
    evolucion_data = data.model_dump()
    
    # Convertir signos vitales a dict si existe
    if evolucion_data.get("signos_vitales_visita"):
        evolucion_data["signos_vitales_visita"] = evolucion_data["signos_vitales_visita"]
    
    # Crear evolución
    evolucion = EvolucionClinica(
        **evolucion_data,
        id_clinica=current_user.clinica_id or 1,
        created_by=current_user.id_usuario,
        podologo_id=data.podologo_id or current_user.id_usuario
    )
    
    db.add(evolucion)
    db.commit()
    db.refresh(evolucion)
    
    return enrich_evolucion_response(evolucion, db)


# =============================================================================
# ENDPOINT: PUT /evoluciones/{id}
# =============================================================================

@router.put("/{evolucion_id}")
async def update_evolucion(
    evolucion_id: int,
    data: EvolucionUpdate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Actualiza una evolución clínica.
    
    **Permisos:** Solo Admin y Podologo
    
    **Nota:** Tanto Santiago como Ibeth pueden editar notas del otro
    (trabajo colaborativo según los requerimientos).
    """
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evolucion_id
    ).first()
    
    if not evolucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evolución no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evolución"
        )
    
    # Actualizar campos
    update_data = data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(evolucion, field, value)
    
    db.commit()
    db.refresh(evolucion)
    
    return enrich_evolucion_response(evolucion, db)


# =============================================================================
# ENDPOINT: DELETE /evoluciones/{id} (Solo Admin)
# =============================================================================

@router.delete("/{evolucion_id}")
async def delete_evolucion(
    evolucion_id: int,
    current_user: SysUsuario = Depends(require_role([ROLE_ADMIN])),  # Solo Admin
    db: Session = Depends(get_core_db)
):
    """
    Elimina una evolución clínica.
    
    **Permisos:** Solo Admin
    
    ⚠️ Esta acción elimina también las evidencias fotográficas asociadas.
    """
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evolucion_id
    ).first()
    
    if not evolucion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evolución no encontrada"
        )
    
    # Verificar clínica
    if current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evolución"
        )
    
    # Eliminar (CASCADE eliminará evidencias)
    db.delete(evolucion)
    db.commit()
    
    return {"message": "Evolución eliminada", "id": evolucion_id}
