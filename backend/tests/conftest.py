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
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Importar la app FastAPI
from backend.api.app import app

# Importar los modelos
from backend.schemas.auth.models import Base as AuthBase, SysUsuario, Clinica
from backend.schemas.core.models import Base as CoreBase, Paciente
from backend.schemas.ops.models import Base as OpsBase, Podologo, Cita

# Importar dependencias
from backend.api.deps.database import get_auth_db, get_core_db, get_ops_db
from backend.api.core.security import create_access_token, get_password_hash


# =============================================================================
# CONFIGURACIÓN DE BASES DE DATOS DE PRUEBA
# =============================================================================

# URLs de bases de datos de prueba (usar SQLite en memoria para tests rápidos)
TEST_AUTH_DB_URL = "sqlite:///:memory:"
TEST_CORE_DB_URL = "sqlite:///:memory:"
TEST_OPS_DB_URL = "sqlite:///:memory:"

# Alternativamente, usar PostgreSQL de prueba si está disponible
# TEST_AUTH_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/test_auth_db"
# TEST_CORE_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/test_core_db"
# TEST_OPS_DB_URL = "postgresql://podoskin:podoskin123@localhost:5432/test_ops_db"


# =============================================================================
# FIXTURES DE MOTOR Y SESIÓN DE BASE DE DATOS
# =============================================================================

@pytest.fixture(scope="function")
def auth_engine():
    """Engine de SQLAlchemy para base de datos de autenticación."""
    engine = create_engine(
        TEST_AUTH_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_AUTH_DB_URL else {},
        poolclass=StaticPool,
    )
    
    # Crear todas las tablas
    AuthBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar
    AuthBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def core_engine():
    """Engine de SQLAlchemy para base de datos core (pacientes, tratamientos)."""
    engine = create_engine(
        TEST_CORE_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_CORE_DB_URL else {},
        poolclass=StaticPool,
    )
    
    # Crear todas las tablas
    CoreBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar
    CoreBase.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def ops_engine():
    """Engine de SQLAlchemy para base de datos ops (citas, podólogos)."""
    engine = create_engine(
        TEST_OPS_DB_URL,
        connect_args={"check_same_thread": False} if "sqlite" in TEST_OPS_DB_URL else {},
        poolclass=StaticPool,
    )
    
    # Crear todas las tablas
    OpsBase.metadata.create_all(bind=engine)
    
    yield engine
    
    # Limpiar
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
    user = SysUsuario(
        nombre_usuario="admin_test",
        email="admin@test.com",
        nombre="Admin",
        apellidos="Test",
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
    user = SysUsuario(
        nombre_usuario="podologo_test",
        email="podologo@test.com",
        nombre="Juan",
        apellidos="Podólogo",
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
    user = SysUsuario(
        nombre_usuario="recepcion_test",
        email="recepcion@test.com",
        nombre="María",
        apellidos="Recepción",
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
    return create_access_token(data={"sub": test_admin_user.nombre_usuario})


@pytest.fixture
def podologo_token(test_podologo_user) -> str:
    """Token JWT de podólogo."""
    return create_access_token(data={"sub": test_podologo_user.nombre_usuario})


@pytest.fixture
def recepcion_token(test_recepcion_user) -> str:
    """Token JWT de recepcionista."""
    return create_access_token(data={"sub": test_recepcion_user.nombre_usuario})


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
