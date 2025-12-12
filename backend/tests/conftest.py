"""
Configuración global de pytest y fixtures compartidos
=====================================================

Este archivo contiene:
- Fixtures de base de datos (sessiones de prueba)
- Fixtures de autenticación (tokens, usuarios)
- Fixtures de datos de prueba
- Configuración de FastAPI TestClient
"""

import os
import pytest
import asyncio
from typing import Generator, Dict, Any
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy import JSON, String, TypeDecorator

# Importar la app FastAPI
from backend.api.app import app

# Importar los modelos
from backend.schemas.auth.models import Base as AuthBase, SysUsuario, Clinica
from backend.schemas.core.models import Base as CoreBase, Paciente
from backend.schemas.ops.models import Base as OpsBase, Podologo, Cita
from backend.schemas.finance.models import Base as FinanceBase

# Importar dependencias
from backend.api.deps.database import get_auth_db, get_core_db, get_ops_db
from backend.api.core.security import create_access_token, get_password_hash


# =============================================================================
# CONFIGURACIÓN DE BASES DE DATOS DE PRUEBA
# =============================================================================

# ✅ Usando las bases de datos PostgreSQL del Docker Compose
# Los tests usarán las mismas BDs que desarrollo (docker-compose.yml)
TEST_AUTH_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db"
TEST_CORE_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db"
TEST_OPS_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db"

# Nota: Los tests crearán/eliminarán tablas en cada ejecución
# Si prefieres usar BDs separadas para tests, crea:
# - test_auth_db, test_core_db, test_ops_db en PostgreSQL
# y actualiza las URLs arriba


# =============================================================================
# FIXTURES DE MOTOR Y SESIÓN DE BASE DE DATOS
# =============================================================================

@pytest.fixture(scope="function")
def auth_engine():
    """Engine de SQLAlchemy para base de datos de autenticación."""
    engine = create_engine(
        TEST_AUTH_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_AUTH_DB_URL else {},
        poolclass=StaticPool if "sqlite" in TEST_AUTH_DB_URL else None,
    )
    
    # Limpiar ANTES de crear (importante para tests repetidos)
    if "postgresql" in TEST_AUTH_DB_URL:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {AuthBase.metadata.schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {AuthBase.metadata.schema}"))
    
    # Crear todas las tablas
    AuthBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar después del test
    if "postgresql" in TEST_AUTH_DB_URL:
        with engine.begin() as conn:
            # Truncate todas las tablas para limpiar datos Y secuencias
            conn.execute(text(f"""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = '{AuthBase.metadata.schema}') LOOP
                        EXECUTE 'TRUNCATE TABLE {AuthBase.metadata.schema}.' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE';
                    END LOOP;
                END $$;
            """))
    else:
        AuthBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def core_engine():
    """Engine de SQLAlchemy para base de datos core (pacientes, tratamientos)."""
    engine = create_engine(
        TEST_CORE_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_CORE_DB_URL else {},
        poolclass=StaticPool if "sqlite" in TEST_CORE_DB_URL else None,
    )
    
    # Limpiar ANTES de crear (importante para tests repetidos)
    if "postgresql" in TEST_CORE_DB_URL:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {CoreBase.metadata.schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {CoreBase.metadata.schema}"))
    
    # Crear todas las tablas
    CoreBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar después del test
    if "postgresql" in TEST_CORE_DB_URL:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {CoreBase.metadata.schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {CoreBase.metadata.schema}"))
    else:
        CoreBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def ops_engine():
    """Engine de SQLAlchemy para base de datos ops (citas, podólogos)."""
    engine = create_engine(
        TEST_OPS_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_OPS_DB_URL else {},
        poolclass=StaticPool if "sqlite" in TEST_OPS_DB_URL else None,
    )
    
    # Limpiar ANTES de crear (importante para tests repetidos)
    if "postgresql" in TEST_OPS_DB_URL:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {OpsBase.metadata.schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {OpsBase.metadata.schema}"))
            if hasattr(FinanceBase.metadata, 'schema') and FinanceBase.metadata.schema:
                conn.execute(text(f"DROP SCHEMA IF EXISTS {FinanceBase.metadata.schema} CASCADE"))
                conn.execute(text(f"CREATE SCHEMA {FinanceBase.metadata.schema}"))
    
    # Crear todas las tablas
    OpsBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar después del test
    if "postgresql" in TEST_OPS_DB_URL:
        with engine.begin() as conn:
            conn.execute(text(f"DROP SCHEMA IF EXISTS {OpsBase.metadata.schema} CASCADE"))
            conn.execute(text(f"CREATE SCHEMA {OpsBase.metadata.schema}"))
            if hasattr(FinanceBase.metadata, 'schema') and FinanceBase.metadata.schema:
                conn.execute(text(f"DROP SCHEMA IF EXISTS {FinanceBase.metadata.schema} CASCADE"))
                conn.execute(text(f"CREATE SCHEMA {FinanceBase.metadata.schema}"))
    else:
        OpsBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def auth_db(auth_engine) -> Generator[Session, None, None]:
    """Sesión de base de datos de autenticación para tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=auth_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def core_db(core_engine) -> Generator[Session, None, None]:
    """Sesión de base de datos core para tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=core_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def ops_db(ops_engine) -> Generator[Session, None, None]:
    """Sesión de base de datos ops para tests."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=ops_engine)
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# =============================================================================
# FIXTURES DE FASTAPI TEST CLIENT
# =============================================================================

@pytest.fixture(scope="function")
def client(auth_db, core_db, ops_db) -> Generator[TestClient, None, None]:
    """
    Cliente de prueba de FastAPI con override de dependencias de BD.
    
    Este fixture reemplaza las conexiones reales de BD con las de prueba.
    """
    
    # Override de dependencias de base de datos
    def override_get_auth_db():
        try:
            yield auth_db
        finally:
            pass
    
    def override_get_core_db():
        try:
            yield core_db
        finally:
            pass
    
    def override_get_ops_db():
        try:
            yield ops_db
        finally:
            pass
    
    app.dependency_overrides[get_auth_db] = override_get_auth_db
    app.dependency_overrides[get_core_db] = override_get_core_db
    app.dependency_overrides[get_ops_db] = override_get_ops_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Limpiar overrides
    app.dependency_overrides.clear()


# =============================================================================
# FIXTURES DE DATOS DE PRUEBA - USUARIOS Y AUTENTICACIÓN
# =============================================================================

@pytest.fixture
def test_clinica(auth_db) -> Clinica:
    """Clínica de prueba."""
    clinica = Clinica(
        nombre="Clínica de Prueba",
        activa=True
    )
    auth_db.add(clinica)
    auth_db.commit()
    auth_db.refresh(clinica)
    return clinica


@pytest.fixture
def test_admin_user(auth_db, test_clinica) -> SysUsuario:
    """Usuario administrador de prueba."""
    # Get-or-create pattern para evitar duplicados
    user = auth_db.query(SysUsuario).filter_by(nombre_usuario="admin_test").first()
    if not user:
        user = SysUsuario(
            nombre_usuario="admin_test",
            email="admin@test.com",
            password_hash=get_password_hash("admin123"),
            rol="Admin",
            activo=True,
            clinica_id=test_clinica.id_clinica
        )
        auth_db.add(user)
        auth_db.commit()
        auth_db.refresh(user)
    return user


@pytest.fixture
def test_podologo_user(auth_db, test_clinica) -> SysUsuario:
    """Usuario podólogo de prueba."""
    # Get-or-create pattern para evitar duplicados
    user = auth_db.query(SysUsuario).filter_by(nombre_usuario="podologo_test").first()
    if not user:
        user = SysUsuario(
            nombre_usuario="podologo_test",
            email="podologo@test.com",
            password_hash=get_password_hash("podo123"),
            rol="Podologo",
            activo=True,
            clinica_id=test_clinica.id_clinica
        )
        auth_db.add(user)
        auth_db.commit()
        auth_db.refresh(user)
    return user


@pytest.fixture
def test_recepcion_user(auth_db, test_clinica) -> SysUsuario:
    """Usuario recepcionista de prueba."""
    # Get-or-create pattern para evitar duplicados
    user = auth_db.query(SysUsuario).filter_by(nombre_usuario="recepcion_test").first()
    if not user:
        user = SysUsuario(
            nombre_usuario="recepcion_test",
            email="recepcion@test.com",
            password_hash=get_password_hash("recep123"),
            rol="Recepcion",
            activo=True,
            clinica_id=test_clinica.id_clinica
        )
        auth_db.add(user)
        auth_db.commit()
        auth_db.refresh(user)
    return user


@pytest.fixture
def admin_token(test_admin_user) -> str:
    """Token JWT de administrador."""
    return create_access_token(data={
        "user_id": test_admin_user.id_usuario,
        "username": test_admin_user.nombre_usuario,
        "rol": test_admin_user.rol,
        "clinica_id": test_admin_user.clinica_id
    })


@pytest.fixture
def podologo_token(test_podologo_user) -> str:
    """Token JWT de podólogo."""
    return create_access_token(data={
        "user_id": test_podologo_user.id_usuario,
        "username": test_podologo_user.nombre_usuario,
        "rol": test_podologo_user.rol,
        "clinica_id": test_podologo_user.clinica_id
    })


@pytest.fixture
def recepcion_token(test_recepcion_user) -> str:
    """Token JWT de recepcionista."""
    return create_access_token(data={
        "user_id": test_recepcion_user.id_usuario,
        "username": test_recepcion_user.nombre_usuario,
        "rol": test_recepcion_user.rol,
        "clinica_id": test_recepcion_user.clinica_id
    })


@pytest.fixture
def auth_headers_admin(admin_token) -> Dict[str, str]:
    """Headers de autorización para admin."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def auth_headers_podologo(podologo_token) -> Dict[str, str]:
    """Headers de autorización para podólogo."""
    return {"Authorization": f"Bearer {podologo_token}"}


@pytest.fixture
def auth_headers_recepcion(recepcion_token) -> Dict[str, str]:
    """Headers de autorización para recepcionista."""
    return {"Authorization": f"Bearer {recepcion_token}"}


# =============================================================================
# FIXTURES DE DATOS DE PRUEBA - DATOS CLÍNICOS
# =============================================================================

@pytest.fixture
def test_paciente(core_db) -> Paciente:
    """Paciente de prueba."""
    from datetime import date
    paciente = Paciente(
        nombres="Juan",
        apellidos="Pérez López",
        fecha_nacimiento=date(1990, 5, 15),
        sexo="M",
        telefono="5551234567",
        email="juan.perez@test.com",
        activo=True
    )
    core_db.add(paciente)
    core_db.commit()
    core_db.refresh(paciente)
    return paciente


@pytest.fixture
def test_podologo(ops_db) -> Podologo:
    """Podólogo de prueba."""
    podologo = Podologo(
        nombre="Dr. Carlos",
        apellidos="Martínez",
        especialidad="Podología General",
        cedula_profesional="12345678",
        telefono="5559876543",
        email="carlos.martinez@test.com",
        activo=True
    )
    ops_db.add(podologo)
    ops_db.commit()
    ops_db.refresh(podologo)
    return podologo


# =============================================================================
# HOOKS DE PYTEST
# =============================================================================

def pytest_configure(config):
    """Configuración inicial de pytest."""
    print("\n" + "="*80)
    print("🧪 Iniciando suite de tests de PodoSkin API")
    print("="*80)


def pytest_collection_finish(session):
    """Después de recolectar todos los tests."""
    print(f"\n✓ Se encontraron {len(session.items)} tests")


def pytest_sessionfinish(session, exitstatus):
    """Al finalizar la sesión de tests."""
    print("\n" + "="*80)
    if exitstatus == 0:
        print("✅ Todos los tests pasaron exitosamente")
    else:
        print("❌ Algunos tests fallaron")
    print("="*80 + "\n")
