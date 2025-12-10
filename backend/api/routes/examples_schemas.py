from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from backend.api.deps.database import get_core_db
from backend.api.deps.auth import get_current_active_user
from backend.schemas.core.schemas_examples import (
    PacienteCreate, PacienteUpdate, PacienteResponse, TratamientoCreate
)
from backend.schemas.core.models import Paciente, Tratamiento
from backend.schemas.auth.models import SysUsuario

router = APIRouter(prefix="/examples", tags=["Examples"])


@router.post("/pacientes", response_model=PacienteResponse, status_code=status.HTTP_201_CREATED)
def create_paciente(
    paciente_in: PacienteCreate,
    db: Session = Depends(get_core_db),
    current_user: SysUsuario = Depends(get_current_active_user)
):
    """Crear paciente de ejemplo usando `PacienteCreate` y validaciones Pydantic."""
    paciente = Paciente(
        nombres=paciente_in.nombres,
        apellidos=paciente_in.apellidos,
        fecha_nacimiento=paciente_in.fecha_nacimiento,
        sexo=paciente_in.sexo,
        telefono=paciente_in.telefono,
        email=paciente_in.email
    )
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente


@router.put("/pacientes/{id}", response_model=PacienteResponse)
def update_paciente(
    id: int,
    paciente_in: PacienteUpdate,
    db: Session = Depends(get_core_db),
    current_user: SysUsuario = Depends(get_current_active_user)
):
    paciente = db.query(Paciente).filter(Paciente.id_paciente == id).first()
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente no encontrado")

    # Aplicar cambios parciales
    for field, value in paciente_in.model_dump(exclude_unset=True).items():
        setattr(paciente, field, value)

    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente


@router.post("/tratamientos", status_code=status.HTTP_201_CREATED)
def create_tratamiento(
    tr_in: TratamientoCreate,
    db: Session = Depends(get_core_db),
    current_user: SysUsuario = Depends(get_current_active_user)
):
    # Validar existencia de paciente (FK virtual dentro de la misma BD)
    paciente = db.query(Paciente).filter(Paciente.id_paciente == tr_in.paciente_id).first()
    if paciente is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="paciente_id inválido")

    tr = Tratamiento(
        paciente_id=tr_in.paciente_id,
        motivo_consulta_principal=tr_in.motivo_consulta_principal,
        fecha_inicio=tr_in.fecha_inicio
    )
    db.add(tr)
    db.commit()
    db.refresh(tr)
    return {"id_tratamiento": tr.id_tratamiento, "paciente_id": tr.paciente_id}
