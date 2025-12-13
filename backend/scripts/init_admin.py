"""
Script para inicializar BD limpia con solo el administrador.
Ejecutar: python backend/scripts/init_admin.py
"""
import sys
from pathlib import Path

# Agregar backend al path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from datetime import datetime
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Imports locales
from api.deps.database import AuthSessionLocal, OpsSessionLocal
from schemas.auth.models import Clinica, SysUsuario
from schemas.ops.models import Podologo
from api.core.security import get_password_hash


def generar_id_estructurado(nombre: str, apellido: str, fecha: datetime, contador: int) -> str:
    """
    Genera ID estructurado: ASGO-1213-00001
    - Últimas 2 letras del apellido
    - Últimas 2 letras del nombre
    - Mes-Día (MMDD)
    - Contador de 5 dígitos
    """
    apellido_clean = apellido.replace(" ", "").upper()
    nombre_clean = nombre.replace(" ", "").upper()
    
    letras_apellido = apellido_clean[-2:] if len(apellido_clean) >= 2 else apellido_clean.ljust(2, 'X')
    letras_nombre = nombre_clean[-2:] if len(nombre_clean) >= 2 else nombre_clean.ljust(2, 'X')
    
    mes_dia = fecha.strftime("%m%d")
    
    return f"{letras_apellido}{letras_nombre}-{mes_dia}-{contador:05d}"


def init_clean_db():
    """Inicializa BD limpia con solo admin y clínica."""
    
    print("🧹 Inicializando base de datos limpia...")
    
    # Crear sesiones
    auth_db = AuthSessionLocal()
    ops_db = OpsSessionLocal()
    
    try:
        # 1. Crear clínica
        print("\n📍 Creando clínica...")
        clinica = Clinica(
            nombre="Podoskin Libertad",
            direccion="Dirección pendiente",
            telefono="0000000000",
            email="info@podoskin.com",
            activo=True
        )
        auth_db.add(clinica)
        auth_db.commit()
        auth_db.refresh(clinica)
        print(f"   ✅ Clínica creada: {clinica.nombre} (ID: {clinica.id_clinica})")
        
        # 2. Generar ID estructurado para admin
        fecha_registro = datetime.now()
        admin_id = generar_id_estructurado(
            nombre="Santiago",
            apellido="Ornelas",
            fecha=fecha_registro,
            contador=1
        )
        print(f"\n👤 ID generado para admin: {admin_id}")
        
        # 3. Crear administrador
        print("\n👨‍💼 Creando administrador...")
        admin = SysUsuario(
            username="admin",
            email="admin@podoskin.com",
            hashed_password=get_password_hash("Ornelas2025!"),
            nombre_completo="Santiago de Jesus Ornelas Reynoso",
            rol="Admin",
            id_usuario_custom=admin_id,
            clinica_id=clinica.id_clinica,
            activo=True
        )
        auth_db.add(admin)
        auth_db.commit()
        auth_db.refresh(admin)
        print(f"   ✅ Admin creado:")
        print(f"      - Nombre: {admin.nombre_completo}")
        print(f"      - Username: {admin.username}")
        print(f"      - Email: {admin.email}")
        print(f"      - ID Estructurado: {admin.id_usuario_custom}")
        print(f"      - Contraseña: Ornelas2025!")
        
        # 4. Crear registro en podólogos (opcional, si el admin también es podólogo)
        print("\n🩺 Creando registro de podólogo para admin...")
        podologo = Podologo(
            nombres="Santiago de Jesus",
            apellidos="Ornelas Reynoso",
            cedula_profesional="PENDIENTE",
            especialidad="Administración",
            telefono="0000000000",
            email="admin@podoskin.com",
            activo=True
        )
        ops_db.add(podologo)
        ops_db.commit()
        ops_db.refresh(podologo)
        print(f"   ✅ Podólogo creado (ID: {podologo.id_podologo})")
        
        print("\n" + "="*60)
        print("✅ BASE DE DATOS INICIALIZADA CORRECTAMENTE")
        print("="*60)
        print("\n📋 CREDENCIALES DE ACCESO:")
        print(f"   Username: admin")
        print(f"   Email: admin@podoskin.com")
        print(f"   ID: {admin_id}")
        print(f"   Contraseña: Ornelas2025!")
        print("\n💡 Puedes iniciar sesión con username, email o ID")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        auth_db.rollback()
        ops_db.rollback()
        raise
    finally:
        auth_db.close()
        ops_db.close()


if __name__ == "__main__":
    init_clean_db()
