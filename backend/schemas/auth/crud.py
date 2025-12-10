# backend/schemas/auth/crud.py
from typing import Optional
from sqlalchemy.orm import Session
from .models import Clinica, SysUsuario
from .auth_utils import hash_password

def get_clinica(db: Session, id_clinica: int) -> Optional[Clinica]:
    return db.query(Clinica).filter(Clinica.id_clinica == id_clinica).first()

def create_clinica(db: Session, nombre: str, rfc: Optional[str] = None, activa: bool = True) -> Clinica:
    clinic = Clinica(nombre=nombre, rfc=rfc, activa=activa)
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic

def get_user_by_username(db: Session, username: str) -> Optional[SysUsuario]:
    return db.query(SysUsuario).filter(SysUsuario.nombre_usuario == username).first()

def create_user(db: Session, user_in) -> SysUsuario:
    # user_in debe ser SysUsuarioCreate
    user = SysUsuario(
        nombre_usuario=user_in.nombre_usuario,
        password_hash=hash_password(user_in.password),
        rol=user_in.rol,
        email=user_in.email,
        clinica_id=user_in.clinica_id
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def assign_user_to_clinica(db: Session, user: SysUsuario, clinica_id: int):
    clinica = get_clinica(db, clinica_id)
    if clinica is None:
        raise ValueError(f"Clinica {clinica_id} no existe")
    user.clinica_id = clinica_id
    db.commit()