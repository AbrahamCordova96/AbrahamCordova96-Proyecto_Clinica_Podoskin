import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.schemas.auth.models import Clinica, SysUsuario  # ajusta ruta si es necesario

# Conexión a la base de datos
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

TARGET_NAME = "Podoskin Solutions/Libertad"

try:
    # Encuentra admin (pueden ser 'admin' o 'Admin')
    admin = session.query(SysUsuario).filter(SysUsuario.nombre_usuario.in_(["admin", "Admin"])).first()

    # Desvincula admin de cualquier clínica existente
    if admin and admin.clinica_id is not None:
        admin.clinica_id = None
        session.commit()

    # Borrar clínicas existentes
    session.query(Clinica).delete()
    session.commit()

    # Crear la clínica principal
    clinica = Clinica(nombre=TARGET_NAME, activa=True)
    session.add(clinica)
    session.commit()

    # Enlazar admin existente a la nueva clínica
    if admin:
        admin.clinica_id = clinica.id_clinica
        session.commit()

    print(f"Clínica creada: {TARGET_NAME} (id={clinica.id_clinica})")
    if admin:
        print(f"Admin enlazado: {admin.nombre_usuario} -> clínica {clinica.id_clinica}")
finally:
    session.close()