# =============================================================================
# backend/api/deps/database.py
# Dependencias de conexión a bases de datos
# =============================================================================
# Este archivo proporciona "generadores" de sesiones de base de datos.
# Cada función retorna una sesión conectada a una BD específica.
#
# ¿POR QUÉ USAMOS GENERADORES (yield)?
# El patrón try/yield/finally garantiza que la sesión se cierre
# correctamente después de cada request, incluso si hay errores.
# Esto evita "connection leaks" (conexiones que se quedan abiertas).
#
# ANALOGÍA: Cada función es como un bibliotecario que:
# 1. Te abre la puerta del archivo (yield session)
# 2. Espera a que termines de leer
# 3. Cierra la puerta cuando sales (finally: session.close())
# =============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from backend.api.core.config import get_settings


# Obtenemos la configuración
settings = get_settings()


# =============================================================================
# ENGINES: Conexiones a las bases de datos
# =============================================================================
# Un "engine" es la conexión de bajo nivel a la BD.
# Creamos uno por cada base de datos.

# clinica_auth_db: Usuarios, permisos, auditoría
auth_engine = create_engine(
    settings.AUTH_DB_URL,
    pool_pre_ping=True,  # Verifica que la conexión esté viva antes de usarla
    echo=settings.DEBUG,  # Si DEBUG=True, imprime las queries SQL
)

# clinica_core_db: Pacientes, tratamientos, evoluciones
core_engine = create_engine(
    settings.CORE_DB_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

# clinica_ops_db: Citas, servicios, pagos, gastos
ops_engine = create_engine(
    settings.OPS_DB_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)


# =============================================================================
# SESSION FACTORIES: Fábricas de sesiones
# =============================================================================
# Un SessionLocal es una "fábrica" que crea sesiones de BD.
# Cada vez que llamamos SessionLocal(), obtenemos una nueva sesión.

AuthSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=auth_engine
)

CoreSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=core_engine
)

OpsSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=ops_engine
)


# =============================================================================
# DEPENDENCIAS: Generadores de sesiones para FastAPI
# =============================================================================

def get_auth_db() -> Generator[Session, None, None]:
    """
    Obtiene una sesión de clinica_auth_db.
    
    Uso en endpoints:
        @router.get("/usuarios")
        def get_usuarios(db: Session = Depends(get_auth_db)):
            return db.query(SysUsuario).all()
    
    La sesión se cierra automáticamente al terminar el request.
    """
    db = AuthSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_core_db() -> Generator[Session, None, None]:
    """
    Obtiene una sesión de clinica_core_db.
    
    Uso en endpoints:
        @router.get("/pacientes")
        def get_pacientes(db: Session = Depends(get_core_db)):
            return db.query(Paciente).all()
    """
    db = CoreSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_ops_db() -> Generator[Session, None, None]:
    """
    Obtiene una sesión de clinica_ops_db.
    
    Nota: Esta BD contiene AMBOS schemas: ops y finance.
    Los modelos de ops/ y finance/ usan la misma conexión.
    
    Uso en endpoints:
        @router.get("/citas")
        def get_citas(db: Session = Depends(get_ops_db)):
            return db.query(Cita).all()
    """
    db = OpsSessionLocal()
    try:
        yield db
    finally:
        db.close()
