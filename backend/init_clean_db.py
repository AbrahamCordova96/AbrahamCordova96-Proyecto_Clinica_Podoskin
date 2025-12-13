"""
Script para inicializar BD limpia con solo Admin y Clínica
Ejecutar: python backend/init_clean_db.py
"""
import os
import sys
from datetime import datetime

# Agregar backend al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.schemas.auth.models import Base as AuthBase, Clinica, SysUsuario
from backend.schemas.core.models import Base as CoreBase
from backend.schemas.ops.models import Base as OpsBase
from backend.schemas.finance.models import Base as FinanceBase
from backend.api.core.security import get_password_hash
from backend.utils.id_generator import generar_codigo_interno

# URLs de BD
AUTH_DB_URL = os.getenv("AUTH_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db")
CORE_DB_URL = os.getenv("CORE_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db")
OPS_DB_URL = os.getenv("OPS_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db")

def clean_and_init():
    """Limpia todas las tablas y crea solo Admin + Clínica"""
    
    print("🗑️  Limpiando base de datos...")
    
    # Crear engines
    auth_engine = create_engine(AUTH_DB_URL)
    core_engine = create_engine(CORE_DB_URL)
    ops_engine = create_engine(OPS_DB_URL)
    
    # Eliminar todas las tablas
    print("  📦 Eliminando tablas existentes...")
    FinanceBase.metadata.drop_all(bind=ops_engine)
    OpsBase.metadata.drop_all(bind=ops_engine)
    CoreBase.metadata.drop_all(bind=core_engine)
    AuthBase.metadata.drop_all(bind=auth_engine)
    
    # Recrear tablas vacías
    print("  🏗️  Creando tablas nuevas...")
    AuthBase.metadata.create_all(bind=auth_engine)
    CoreBase.metadata.create_all(bind=core_engine)
    OpsBase.metadata.create_all(bind=ops_engine)
    FinanceBase.metadata.create_all(bind=ops_engine)
    
    # Crear sesión para auth
    AuthSession = sessionmaker(bind=auth_engine)
    session = AuthSession()
    
    try:
        # 1. Crear Clínica
        print("\n🏥 Creando clínica 'Podoskin Libertad'...")
        clinica = Clinica(
            nombre="Podoskin Libertad",
            activa=True
        )
        session.add(clinica)
        session.flush()  # Para obtener id_clinica
        
        print(f"   ✅ Clínica creada con ID: {clinica.id_clinica}")
        
        # 2. Crear Admin
        print("\n👤 Creando usuario administrador...")
        
        # Datos del admin
        nombre = "Santiago"
        apellidos = "Ornelas Reynoso"
        password = "Ornelas2025!"
        
        # Generar código interno: ASGO-MMDD-00001
        fecha_hoy = datetime.now()
        codigo_interno = generar_codigo_interno(
            nombre=nombre,
            apellidos=apellidos,
            fecha_registro=fecha_hoy,
            session=session
        )
        
        admin = SysUsuario(
            nombre_usuario="admin",
            nombre=nombre,
            apellidos=apellidos,
            email="admin@podoskin.com",
            password_hash=get_password_hash(password),
            rol="Admin",
            codigo_interno=codigo_interno,
            clinica_id=clinica.id_clinica,
            activo=True
        )
        
        session.add(admin)
        session.commit()
        
        print(f"   ✅ Admin creado exitosamente")
        print(f"   📋 Código Interno: {codigo_interno}")
        print(f"   👤 Usuario: admin")
        print(f"   🔑 Contraseña: {password}")
        print(f"   📧 Email: admin@podoskin.com")
        print(f"   🏥 Clínica: Podoskin Libertad (ID: {clinica.id_clinica})")
        
        print("\n" + "="*60)
        print("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
        print("="*60)
        print(f"\n🔐 Credenciales de acceso:")
        print(f"   Usuario: admin (o {codigo_interno} o admin@podoskin.com)")
        print(f"   Contraseña: {password}")
        print("\n")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    clean_and_init()
