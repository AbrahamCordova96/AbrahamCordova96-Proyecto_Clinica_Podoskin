# =============================================================================
# backend/api/routes/historial_detalles.py
# Endpoints para tablas hijas: alergias, suplementos, antecedentes, conversaciones
# =============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime

from backend.api.deps.database import get_core_db
from backend.api.deps.auth import get_current_active_user
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import (
    Alergia, Suplemento, AntecedenteNoPatologico, 
    ConversacionPresencial, ConversacionDigital,
    HistorialMedicoGeneral, Paciente
)
from backend.schemas.core.schemas import (
    AlergiaCreate, AlergiaUpdate, AlergiaResponse,
    SuplementoCreate, SuplementoUpdate, SuplementoResponse,
    AntecedenteNoPatologicoCreate, AntecedenteNoPatologicoUpdate, AntecedenteNoPatologicoResponse,
    ConversacionDigitalCreate, ConversacionDigitalUpdate, ConversacionDigitalResponse
)

router = APIRouter(prefix="/historial", tags=["Historial Detalles"])

# =============================================================================
# ENDPOINTS: ALERGIAS
# =============================================================================

@router.post("/alergias", response_model=AlergiaResponse, status_code=status.HTTP_201_CREATED)
async def crear_alergia(
    alergia: AlergiaCreate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Crear una nueva alergia para un historial médico."""
    # Validar que el historial existe
    historial = db.query(HistorialMedicoGeneral).filter_by(id_historial=alergia.id_historial).first()
    if not historial:
        raise HTTPException(status_code=404, detail="Historial no encontrado")
    
    db_alergia = Alergia(
        id_historial=alergia.id_historial,
        nombre=alergia.nombre,
        tipo=alergia.tipo,
        observaciones=alergia.observaciones,
        created_by=current_user.id_usuario
    )
    db.add(db_alergia)
    db.commit()
    db.refresh(db_alergia)
    return db_alergia

@router.get("/alergias", response_model=List[AlergiaResponse])
async def listar_alergias(
    id_historial: Optional[int] = Query(None),
    nombre: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Listar alergias con filtros opcionales."""
    query = db.query(Alergia).filter(Alergia.deleted_at.is_(None))
    
    if id_historial:
        query = query.filter(Alergia.id_historial == id_historial)
    if nombre:
        query = query.filter(Alergia.nombre.ilike(f"%{nombre}%"))
    if tipo:
        query = query.filter(Alergia.tipo == tipo)
    
    return query.offset(skip).limit(limit).all()

@router.get("/alergias/{id_alergia}", response_model=AlergiaResponse)
async def obtener_alergia(
    id_alergia: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Obtener una alergia por ID."""
    alergia = db.query(Alergia).filter(
        and_(Alergia.id_alergia == id_alergia, Alergia.deleted_at.is_(None))
    ).first()
    if not alergia:
        raise HTTPException(status_code=404, detail="Alergia no encontrada")
    return alergia

@router.put("/alergias/{id_alergia}", response_model=AlergiaResponse)
async def actualizar_alergia(
    id_alergia: int,
    alergia_update: AlergiaUpdate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Actualizar una alergia."""
    alergia = db.query(Alergia).filter(
        and_(Alergia.id_alergia == id_alergia, Alergia.deleted_at.is_(None))
    ).first()
    if not alergia:
        raise HTTPException(status_code=404, detail="Alergia no encontrada")
    
    update_data = alergia_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alergia, field, value)
    alergia.updated_by = current_user.id_usuario
    
    db.commit()
    db.refresh(alergia)
    return alergia

@router.delete("/alergias/{id_alergia}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_alergia(
    id_alergia: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Soft delete de una alergia."""
    alergia = db.query(Alergia).filter(
        and_(Alergia.id_alergia == id_alergia, Alergia.deleted_at.is_(None))
    ).first()
    if not alergia:
        raise HTTPException(status_code=404, detail="Alergia no encontrada")
    
    alergia.deleted_at = datetime.utcnow()
    alergia.updated_by = current_user.id_usuario
    db.commit()

# =============================================================================
# ENDPOINTS: SUPLEMENTOS
# =============================================================================

@router.post("/suplementos", response_model=SuplementoResponse, status_code=status.HTTP_201_CREATED)
async def crear_suplemento(
    suplemento: SuplementoCreate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Crear un nuevo suplemento para un historial médico."""
    historial = db.query(HistorialMedicoGeneral).filter_by(id_historial=suplemento.id_historial).first()
    if not historial:
        raise HTTPException(status_code=404, detail="Historial no encontrado")
    
    db_suplemento = Suplemento(
        id_historial=suplemento.id_historial,
        nombre=suplemento.nombre,
        dosis=suplemento.dosis,
        frecuencia=suplemento.frecuencia,
        created_by=current_user.id_usuario
    )
    db.add(db_suplemento)
    db.commit()
    db.refresh(db_suplemento)
    return db_suplemento

@router.get("/suplementos", response_model=List[SuplementoResponse])
async def listar_suplementos(
    id_historial: Optional[int] = Query(None),
    nombre: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Listar suplementos con filtros opcionales."""
    query = db.query(Suplemento).filter(Suplemento.deleted_at.is_(None))
    
    if id_historial:
        query = query.filter(Suplemento.id_historial == id_historial)
    if nombre:
        query = query.filter(Suplemento.nombre.ilike(f"%{nombre}%"))
    
    return query.offset(skip).limit(limit).all()

@router.get("/suplementos/{id_suplemento}", response_model=SuplementoResponse)
async def obtener_suplemento(
    id_suplemento: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Obtener un suplemento por ID."""
    suplemento = db.query(Suplemento).filter(
        and_(Suplemento.id_suplemento == id_suplemento, Suplemento.deleted_at.is_(None))
    ).first()
    if not suplemento:
        raise HTTPException(status_code=404, detail="Suplemento no encontrado")
    return suplemento

@router.put("/suplementos/{id_suplemento}", response_model=SuplementoResponse)
async def actualizar_suplemento(
    id_suplemento: int,
    suplemento_update: SuplementoUpdate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Actualizar un suplemento."""
    suplemento = db.query(Suplemento).filter(
        and_(Suplemento.id_suplemento == id_suplemento, Suplemento.deleted_at.is_(None))
    ).first()
    if not suplemento:
        raise HTTPException(status_code=404, detail="Suplemento no encontrado")
    
    update_data = suplemento_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(suplemento, field, value)
    suplemento.updated_by = current_user.id_usuario
    
    db.commit()
    db.refresh(suplemento)
    return suplemento

@router.delete("/suplementos/{id_suplemento}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_suplemento(
    id_suplemento: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Soft delete de un suplemento."""
    suplemento = db.query(Suplemento).filter(
        and_(Suplemento.id_suplemento == id_suplemento, Suplemento.deleted_at.is_(None))
    ).first()
    if not suplemento:
        raise HTTPException(status_code=404, detail="Suplemento no encontrado")
    
    suplemento.deleted_at = datetime.utcnow()
    suplemento.updated_by = current_user.id_usuario
    db.commit()

# =============================================================================
# ENDPOINTS: ANTECEDENTES NO PATOLÓGICOS
# =============================================================================

@router.post("/antecedentes-no-patologicos", response_model=AntecedenteNoPatologicoResponse, status_code=status.HTTP_201_CREATED)
async def crear_antecedente(
    antecedente: AntecedenteNoPatologicoCreate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Crear un nuevo antecedente no patológico."""
    historial = db.query(HistorialMedicoGeneral).filter_by(id_historial=antecedente.id_historial).first()
    if not historial:
        raise HTTPException(status_code=404, detail="Historial no encontrado")
    
    db_antecedente = AntecedenteNoPatologico(
        id_historial=antecedente.id_historial,
        descripcion=antecedente.descripcion,
        tipo=antecedente.tipo,
        created_by=current_user.id_usuario
    )
    db.add(db_antecedente)
    db.commit()
    db.refresh(db_antecedente)
    return db_antecedente

@router.get("/antecedentes-no-patologicos", response_model=List[AntecedenteNoPatologicoResponse])
async def listar_antecedentes(
    id_historial: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Listar antecedentes no patológicos con filtros opcionales."""
    query = db.query(AntecedenteNoPatologico).filter(AntecedenteNoPatologico.deleted_at.is_(None))
    
    if id_historial:
        query = query.filter(AntecedenteNoPatologico.id_historial == id_historial)
    if tipo:
        query = query.filter(AntecedenteNoPatologico.tipo == tipo)
    
    return query.offset(skip).limit(limit).all()

@router.get("/antecedentes-no-patologicos/{id_antnp}", response_model=AntecedenteNoPatologicoResponse)
async def obtener_antecedente(
    id_antnp: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Obtener un antecedente por ID."""
    antecedente = db.query(AntecedenteNoPatologico).filter(
        and_(AntecedenteNoPatologico.id_antnp == id_antnp, AntecedenteNoPatologico.deleted_at.is_(None))
    ).first()
    if not antecedente:
        raise HTTPException(status_code=404, detail="Antecedente no encontrado")
    return antecedente

@router.put("/antecedentes-no-patologicos/{id_antnp}", response_model=AntecedenteNoPatologicoResponse)
async def actualizar_antecedente(
    id_antnp: int,
    antecedente_update: AntecedenteNoPatologicoUpdate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Actualizar un antecedente."""
    antecedente = db.query(AntecedenteNoPatologico).filter(
        and_(AntecedenteNoPatologico.id_antnp == id_antnp, AntecedenteNoPatologico.deleted_at.is_(None))
    ).first()
    if not antecedente:
        raise HTTPException(status_code=404, detail="Antecedente no encontrado")
    
    update_data = antecedente_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(antecedente, field, value)
    antecedente.updated_by = current_user.id_usuario
    
    db.commit()
    db.refresh(antecedente)
    return antecedente

@router.delete("/antecedentes-no-patologicos/{id_antnp}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_antecedente(
    id_antnp: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Soft delete de un antecedente."""
    antecedente = db.query(AntecedenteNoPatologico).filter(
        and_(AntecedenteNoPatologico.id_antnp == id_antnp, AntecedenteNoPatologico.deleted_at.is_(None))
    ).first()
    if not antecedente:
        raise HTTPException(status_code=404, detail="Antecedente no encontrado")
    
    antecedente.deleted_at = datetime.utcnow()
    antecedente.updated_by = current_user.id_usuario
    db.commit()

# =============================================================================
# ENDPOINTS: CONVERSACIONES DIGITALES
# =============================================================================

@router.post("/conversaciones-digitales", response_model=ConversacionDigitalResponse, status_code=status.HTTP_201_CREATED)
async def crear_conversacion_digital(
    conversacion: ConversacionDigitalCreate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Crear una nueva conversación digital."""
    paciente = db.query(Paciente).filter_by(id_paciente=conversacion.id_paciente).first()
    if not paciente:
        raise HTTPException(status_code=404, detail="Paciente no encontrado")
    
    db_conversacion = ConversacionDigital(
        id_paciente=conversacion.id_paciente,
        canal=conversacion.canal,
        remitente=conversacion.remitente,
        mensaje=conversacion.mensaje,
        url_adjunto=conversacion.url_adjunto,
        leido=conversacion.leido,
        created_by=current_user.id_usuario
    )
    db.add(db_conversacion)
    db.commit()
    db.refresh(db_conversacion)
    return db_conversacion

@router.get("/conversaciones-digitales", response_model=List[ConversacionDigitalResponse])
async def listar_conversaciones_digitales(
    id_paciente: Optional[int] = Query(None),
    canal: Optional[str] = Query(None),
    leido: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Listar conversaciones digitales con filtros opcionales."""
    query = db.query(ConversacionDigital).filter(ConversacionDigital.deleted_at.is_(None))
    
    if id_paciente:
        query = query.filter(ConversacionDigital.id_paciente == id_paciente)
    if canal:
        query = query.filter(ConversacionDigital.canal == canal)
    if leido is not None:
        query = query.filter(ConversacionDigital.leido == leido)
    
    return query.order_by(desc(ConversacionDigital.fecha)).offset(skip).limit(limit).all()

@router.get("/conversaciones-digitales/{id_conversacion}", response_model=ConversacionDigitalResponse)
async def obtener_conversacion_digital(
    id_conversacion: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Obtener una conversación digital por ID."""
    conversacion = db.query(ConversacionDigital).filter(
        and_(ConversacionDigital.id_conversacion == id_conversacion, ConversacionDigital.deleted_at.is_(None))
    ).first()
    if not conversacion:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    return conversacion

@router.put("/conversaciones-digitales/{id_conversacion}", response_model=ConversacionDigitalResponse)
async def actualizar_conversacion_digital(
    id_conversacion: int,
    conversacion_update: ConversacionDigitalUpdate,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Actualizar una conversación digital."""
    conversacion = db.query(ConversacionDigital).filter(
        and_(ConversacionDigital.id_conversacion == id_conversacion, ConversacionDigital.deleted_at.is_(None))
    ).first()
    if not conversacion:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    update_data = conversacion_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(conversacion, field, value)
    conversacion.updated_by = current_user.id_usuario
    
    db.commit()
    db.refresh(conversacion)
    return conversacion

@router.delete("/conversaciones-digitales/{id_conversacion}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_conversacion_digital(
    id_conversacion: int,
    current_user: SysUsuario = Depends(get_current_active_user),
    db: Session = Depends(get_core_db)
):
    """Soft delete de una conversación digital."""
    conversacion = db.query(ConversacionDigital).filter(
        and_(ConversacionDigital.id_conversacion == id_conversacion, ConversacionDigital.deleted_at.is_(None))
    ).first()
    if not conversacion:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    
    conversacion.deleted_at = datetime.utcnow()
    conversacion.updated_by = current_user.id_usuario
    db.commit()
