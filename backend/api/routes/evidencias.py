# =============================================================================
# backend/api/routes/evidencias.py
# Endpoints de Evidencia Fotográfica
# =============================================================================
# Este archivo implementa los endpoints de evidencias:
#   - GET /evoluciones/{id}/evidencias → Listar fotos de evolución
#   - GET /evidencias/{id} → Ver foto
#   - POST /evidencias → Subir foto
#   - DELETE /evidencias/{id} → Eliminar foto
#
# PERMISOS: Solo Admin y Podologo (datos clínicos)
# =============================================================================

from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import base64
import os

from backend.api.deps.database import get_core_db
from backend.api.deps.permissions import require_role, CLINICAL_ROLES
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import EvidenciaFotografica, EvolucionClinica


# =============================================================================
# ROUTER
# =============================================================================
router = APIRouter(prefix="/evidencias", tags=["Evidencias Fotográficas"])


# =============================================================================
# SCHEMAS
# =============================================================================

class EvidenciaCreate(BaseModel):
    """Request para crear evidencia (sin archivo)"""
    evolucion_id: int
    etapa_tratamiento: str = Field(
        ..., 
        pattern="^(Antes|Durante|Después)$",
        description="Etapa: Antes, Durante o Después"
    )
    observaciones: Optional[str] = None
    url_archivo: str = Field(..., description="URL o path de la imagen")


class EvidenciaResponse(BaseModel):
    """Response de evidencia"""
    id_evidencia: int
    evolucion_id: int
    etapa_tratamiento: str
    url_archivo: str
    observaciones: Optional[str] = None
    fecha_captura: Optional[datetime] = None
    created_by: Optional[int] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# ENDPOINT: GET /evidencias
# =============================================================================

@router.get("")
async def list_all_evidencias(
    skip: int = 0,
    limit: int = 100,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista todas las evidencias fotográficas.
    
    **Permisos:** Solo Admin y Podologo
    """
    query = db.query(EvidenciaFotografica)
    
    # Filtrar por clínica si el usuario está asignado a una
    if current_user.clinica_id:
        query = query.filter(EvidenciaFotografica.id_clinica == current_user.clinica_id)
    
    total = query.count()
    evidencias = query.order_by(EvidenciaFotografica.fecha_captura.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "evidencias": [EvidenciaResponse.model_validate(e) for e in evidencias]
    }


# =============================================================================
# ENDPOINT: GET /evoluciones/{id}/evidencias
# =============================================================================

@router.get("/evolucion/{evolucion_id}")
async def list_evidencias_by_evolucion(
    evolucion_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista todas las evidencias fotográficas de una evolución.
    
    **Permisos:** Solo Admin y Podologo
    """
    # Verificar que la evolución existe
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
    
    evidencias = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.evolucion_id == evolucion_id
    ).order_by(EvidenciaFotografica.fecha_captura).all()
    
    return {
        "evolucion_id": evolucion_id,
        "total": len(evidencias),
        "evidencias": [EvidenciaResponse.model_validate(e) for e in evidencias]
    }


# =============================================================================
# ENDPOINT: GET /evidencias/{id}
# =============================================================================

@router.get("/{evidencia_id}")
async def get_evidencia(
    evidencia_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Obtiene detalle de una evidencia fotográfica.
    
    **Permisos:** Solo Admin y Podologo
    """
    evidencia = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.id_evidencia == evidencia_id
    ).first()
    
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    
    # Verificar acceso via evolución
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evidencia.evolucion_id
    ).first()
    
    if evolucion and current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evidencia"
        )
    
    return EvidenciaResponse.model_validate(evidencia)


# =============================================================================
# ENDPOINT: GET /evidencias/tratamiento/{tratamiento_id}
# =============================================================================

@router.get("/tratamiento/{tratamiento_id}")
async def list_evidencias_by_tratamiento(
    tratamiento_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Lista todas las evidencias de un tratamiento (todas sus evoluciones).
    
    **Permisos:** Solo Admin y Podologo
    """
    from backend.schemas.core.models import Tratamiento
    
    # Verificar que el tratamiento existe
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == tratamiento_id
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
    
    # Obtener todas las evoluciones del tratamiento
    evoluciones = db.query(EvolucionClinica).filter(
        EvolucionClinica.tratamiento_id == tratamiento_id
    ).all()
    
    evolucion_ids = [e.id_evolucion for e in evoluciones]
    
    # Obtener todas las evidencias de esas evoluciones
    evidencias = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.evolucion_id.in_(evolucion_ids)
    ).order_by(EvidenciaFotografica.fecha_captura).all()
    
    return {
        "tratamiento_id": tratamiento_id,
        "total_evoluciones": len(evoluciones),
        "total_evidencias": len(evidencias),
        "evidencias": [EvidenciaResponse.model_validate(e) for e in evidencias]
    }


# =============================================================================
# ENDPOINT: POST /evidencias (con URL)
# =============================================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_evidencia(
    data: EvidenciaCreate,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Registra una nueva evidencia fotográfica.
    
    **Permisos:** Solo Admin y Podologo
    
    **Parámetros:**
    - evolucion_id: ID de la evolución clínica
    - etapa_tratamiento: "Antes", "Durante" o "Después"
    - url_archivo: URL o path donde está almacenada la imagen
    - observaciones: Notas opcionales sobre la foto
    
    **Nota:** Esta versión registra la URL de la foto.
    Para subir archivos binarios, usar el endpoint /evidencias/upload.
    """
    # Verificar que la evolución existe
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == data.evolucion_id
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
    
    # Crear evidencia
    evidencia = EvidenciaFotografica(
        evolucion_id=data.evolucion_id,
        etapa_tratamiento=data.etapa_tratamiento,
        url_archivo=data.url_archivo,
        observaciones=data.observaciones,
        fecha_captura=datetime.now(timezone.utc),
        created_by=current_user.id_usuario
    )
    
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    
    return EvidenciaResponse.model_validate(evidencia)


# =============================================================================
# ENDPOINT: PUT /evidencias/{id}
# =============================================================================

@router.put("/{evidencia_id}")
async def update_evidencia(
    evidencia_id: int,
    observaciones: Optional[str] = None,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Actualiza las observaciones de una evidencia.
    
    **Permisos:** Solo Admin y Podologo
    """
    evidencia = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.id_evidencia == evidencia_id
    ).first()
    
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    
    # Verificar acceso via evolución
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evidencia.evolucion_id
    ).first()
    
    if evolucion and current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evidencia"
        )
    
    # Actualizar observaciones
    if observaciones is not None:
        evidencia.observaciones = observaciones
    
    db.commit()
    db.refresh(evidencia)
    
    return {
        "message": "Evidencia actualizada",
        "evidencia": EvidenciaResponse.model_validate(evidencia)
    }


# =============================================================================
# ENDPOINT: POST /evidencias/upload (con archivo binario)
# =============================================================================

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_evidencia(
    evolucion_id: int = Form(...),
    etapa_tratamiento: str = Form(..., pattern="^(Antes|Durante|Después)$"),
    observaciones: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Sube una foto de evidencia clínica.
    
    **Permisos:** Solo Admin y Podologo
    
    **Parámetros (form-data):**
    - evolucion_id: ID de la evolución clínica
    - etapa_tratamiento: "Antes", "Durante" o "Después"
    - observaciones: Notas opcionales
    - file: Archivo de imagen (JPG, PNG)
    
    **Nota:** Las fotos se guardan en el sistema de archivos local.
    En producción, considera usar S3 o similar.
    """
    # Verificar que la evolución existe
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
    
    # Validar tipo de archivo
    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido. Permitidos: {allowed_types}"
        )
    
    # Generar nombre único para el archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"evidencia_{evolucion_id}_{timestamp}.{extension}"
    
    # Directorio de uploads (crear si no existe)
    upload_dir = os.path.join("uploads", "evidencias")
    os.makedirs(upload_dir, exist_ok=True)
    
    # Guardar archivo
    file_path = os.path.join(upload_dir, filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Crear registro en BD
    evidencia = EvidenciaFotografica(
        evolucion_id=evolucion_id,
        etapa_tratamiento=etapa_tratamiento,
        url_archivo=file_path,
        observaciones=observaciones,
        fecha_captura=datetime.now(timezone.utc),
        created_by=current_user.id_usuario
    )
    
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    
    return {
        "message": "Evidencia subida exitosamente",
        "evidencia": EvidenciaResponse.model_validate(evidencia)
    }


# =============================================================================
# ENDPOINT: DELETE /evidencias/{id}
# =============================================================================

@router.delete("/{evidencia_id}")
async def delete_evidencia(
    evidencia_id: int,
    current_user: SysUsuario = Depends(require_role(CLINICAL_ROLES)),
    db: Session = Depends(get_core_db)
):
    """
    Elimina una evidencia fotográfica.
    
    **Permisos:** Solo Admin y Podologo
    
    **Nota:** También intenta eliminar el archivo físico si existe.
    """
    evidencia = db.query(EvidenciaFotografica).filter(
        EvidenciaFotografica.id_evidencia == evidencia_id
    ).first()
    
    if not evidencia:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evidencia no encontrada"
        )
    
    # Verificar acceso via evolución
    evolucion = db.query(EvolucionClinica).filter(
        EvolucionClinica.id_evolucion == evidencia.evolucion_id
    ).first()
    
    if evolucion and current_user.clinica_id and evolucion.id_clinica != current_user.clinica_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta evidencia"
        )
    
    # Intentar eliminar archivo físico
    if evidencia.url_archivo and os.path.exists(evidencia.url_archivo):
        try:
            os.remove(evidencia.url_archivo)
        except Exception:
            pass  # Ignorar errores al eliminar archivo
    
    # Eliminar registro
    db.delete(evidencia)
    db.commit()
    
    return {"message": "Evidencia eliminada", "id": evidencia_id}
