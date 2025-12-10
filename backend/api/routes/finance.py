from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from decimal import Decimal

from backend.api.deps.database import get_ops_db, get_core_db
from backend.api.deps.auth import get_current_active_user
from backend.schemas.finance import models as fin_models
from backend.schemas.finance.schemas import (
    MetodoPagoCreate, MetodoPagoResponse,
    PagoCreate, PagoResponse,
    TransaccionCreate, TransaccionResponse
)
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Paciente

router = APIRouter(prefix="/finance", tags=["Finance"])


@router.get("/metodos", response_model=list[MetodoPagoResponse])
def list_metodos(db: Session = Depends(get_ops_db)):
    ms = db.query(fin_models.MetodoPago).filter(fin_models.MetodoPago.activo == True).all()
    return ms


@router.post("/metodos", response_model=MetodoPagoResponse, status_code=status.HTTP_201_CREATED)
def create_metodo(m_in: MetodoPagoCreate, db: Session = Depends(get_ops_db), user: SysUsuario = Depends(get_current_active_user)):
    metodo = fin_models.MetodoPago(nombre=m_in.nombre)
    db.add(metodo)
    db.commit()
    db.refresh(metodo)
    return metodo


@router.get("/pagos", response_model=list[PagoResponse])
def list_pagos(skip: int = 0, limit: int = 100, db: Session = Depends(get_ops_db), user: SysUsuario = Depends(get_current_active_user)):
    """
    Lista todos los pagos.
    """
    pagos = db.query(fin_models.Pago).order_by(fin_models.Pago.fecha_emision.desc()).offset(skip).limit(limit).all()
    return pagos


@router.post("/pagos", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
def create_pago(p_in: PagoCreate, db_ops: Session = Depends(get_ops_db), db_core: Session = Depends(get_core_db), user: SysUsuario = Depends(get_current_active_user)):
    # Validar que paciente existe en core DB usando ORM (compatible con test y prod)
    try:
        paciente_obj = db_core.query(Paciente).filter(Paciente.id_paciente == p_in.paciente_id).first()
    except Exception as e:
        # En test, si la tabla no existe o hay otro error, fallar
        paciente_obj = None
    
    if not paciente_obj:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="paciente_id inválido")

    pago = fin_models.Pago(
        paciente_id=p_in.paciente_id,
        total_facturado=p_in.total_facturado,
        monto_pagado=Decimal(0),
        saldo_pendiente=p_in.total_facturado,
        status_pago='Pendiente',
        notas=p_in.notas
    )
    db_ops.add(pago)
    db_ops.commit()
    db_ops.refresh(pago)
    return pago


@router.get("/pagos/{id}", response_model=PagoResponse)
def get_pago(id: int, db: Session = Depends(get_ops_db)):
    pago = db.query(fin_models.Pago).filter(fin_models.Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")
    return pago


@router.post("/pagos/{id}/transacciones", response_model=TransaccionResponse, status_code=status.HTTP_201_CREATED)
def add_transaccion(id: int, t_in: TransaccionCreate, db_ops: Session = Depends(get_ops_db), user: SysUsuario = Depends(get_current_active_user)):
    # Validate pago
    pago = db_ops.query(fin_models.Pago).filter(fin_models.Pago.id_pago == id).first()
    if not pago:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago no encontrado")

    # Validate metodo
    metodo = db_ops.query(fin_models.MetodoPago).filter(fin_models.MetodoPago.id_metodo == t_in.metodo_pago_id).first()
    if not metodo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="metodo_pago_id inválido")

    # Create transaction
    trans = fin_models.Transaccion(
        pago_id=pago.id_pago,
        monto=t_in.monto,
        metodo_pago_id=t_in.metodo_pago_id,
        notas=t_in.notas,
        recibido_por=user.id_usuario
    )
    db_ops.add(trans)

    # Update pago amounts
    pago.monto_pagado = (pago.monto_pagado or Decimal(0)) + Decimal(t_in.monto)
    pago.saldo_pendiente = (pago.total_facturado or Decimal(0)) - pago.monto_pagado
    if pago.saldo_pendiente <= 0:
        pago.status_pago = 'Pagado'
        pago.saldo_pendiente = Decimal(0)
    elif pago.monto_pagado > 0:
        pago.status_pago = 'Parcial'

    db_ops.add(pago)
    db_ops.commit()
    db_ops.refresh(trans)
    return trans
