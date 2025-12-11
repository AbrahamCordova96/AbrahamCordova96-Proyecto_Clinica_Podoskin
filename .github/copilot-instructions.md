# 🦶 PodoSkin API - Instrucciones para Agentes de IA

## Arquitectura General

**PodoSkin** es un sistema de gestión clínica podológica con:
- **Backend**: FastAPI (Python) + SQLAlchemy ORM
- **BD**: 3 bases de datos PostgreSQL independientes en un contenedor Docker
- **Auth**: JWT tokens + RBAC (3 roles: Admin, Podologo, Recepcion)
- **API**: 101+ endpoints organizados en 16 módulos
- **Testing**: Suite pytest con 120+ tests automatizados
- **IA Tools**: Chatbot terminal con NL-to-SQL, análisis matemático, fuzzy search

### Modelo de Datos (3 Bases Separadas)

```
clinica_auth_db (schema: auth)
├── clinicas         # Clínicas (multi-tenant potencial)
├── sys_usuarios     # Usuarios + roles del sistema
└── audit_logs       # Auditoría de cambios

clinica_core_db (schema: clinic)
├── pacientes        # Expedientes de pacientes
├── tratamientos     # "Carpetas de problemas"
├── evoluciones      # Notas clínicas SOAP por visita
├── evidencias       # Fotos clínicas
└── (7 modelos total)

clinica_ops_db (schemas: ops + finance)
├── podologos        # Personal clínico
├── citas            # Agenda
├── catalogo_servicios
├── solicitudes_prospectos  # Leads/prospectos
├── pagos, transacciones, gastos (finance)
└── (4 + 8 modelos total)
```

**Nota crítica**: No hay FKs entre BD diferentes. SQLAlchemy no lo soporta. Las validaciones son de aplicación.

## Patrones Clave

### 1. Inyección de Dependencias (Conexiones BD)

Toda sesión de BD es un **Depends** en FastAPI:

```python
# backend/api/deps/database.py - 3 funciones generadoras
async def get_auth_db() -> Generator[Session, None, None]:
    # Yields sesión a clinica_auth_db
async def get_core_db() -> Generator[Session, None, None]:
    # Yields sesión a clinica_core_db
async def get_ops_db() -> Generator[Session, None, None]:
    # Yields sesión a clinica_ops_db
```

En endpoints:
```python
@router.get("/pacientes")
async def list_pacientes(db: Session = Depends(get_core_db)):
    # db está ya conectada a clinica_core_db
```

### 2. Autenticación y Autorización

**Token JWT** en header: `Authorization: Bearer {token}`

```python
# backend/api/deps/auth.py
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_auth_db)
) -> SysUsuario:
    # Extrae JWT, verifica, busca usuario en BD
```

**RBAC**: 3 roles con permisos diferenciados
- `Admin`: Todo (incluyendo eliminar y crear usuarios)
- `Podologo`: Datos clínicos, citas, reportes
- `Recepcion`: Solo agenda y contacto de pacientes (no historial médico)

```python
# Uso en endpoints
@router.get("/tratamientos")
async def list_tratamientos(
    current_user: SysUsuario = Depends(get_current_active_user),
    _: None = Depends(require_role(CLINICAL_ROLES))  # Admin, Podologo
):
    pass
```

### 3. Modelos SQLAlchemy (Multi-BD)

Cada BD tiene su `Base` declarativa separada:

```python
# backend/schemas/auth/models.py
from sqlalchemy.dialects.postgresql import TIMESTAMP

class SysUsuario(Base):
    __tablename__ = "sys_usuarios"
    __table_args__ = {"schema": "auth"}  # Schema explícito
    
    # IMPORTANTE: TIMESTAMP(timezone=True) es TIMESTAMPTZ en PostgreSQL
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
```

**Patrones importantes**:
- Usar `BigInteger` para PKs (por performance con índices B-tree PostgreSQL)
- Timestampz para auditoría: `TIMESTAMP(timezone=True)`
- Soft deletes: campo `activo` booleano (no DELETE, sino UPDATE activo=False)

### 4. Estructura de Rutas

Cada módulo es un router FastAPI con patrón de esquemas Pydantic:

```
backend/api/routes/
├── auth.py          # Login, me, change-password
├── pacientes.py     # CRUD + historial
├── citas.py         # Agenda
├── tratamientos.py  # Carpetas de problemas
├── evoluciones.py   # Notas SOAP
├── evidencias.py    # Fotos clínicas
├── servicios.py     # Catálogo
├── prospectos.py    # Leads
├── podologos.py     # Staff
├── usuarios.py      # Gestión de usuarios (Admin)
└── audit.py         # Logs (Admin/Podologo)
```

Cada ruta sigue este pattern:
```python
from pydantic import BaseModel

class TratamientoBase(BaseModel):
    problema: str
    fecha_inicio: date

class TratamientoCreate(TratamientoBase):
    paciente_id: int

class TratamientoUpdate(BaseModel):
    # Solo campos editables
    problema: Optional[str] = None
    estado: Optional[str] = None

class TratamientoResponse(TratamientoBase):
    id_tratamiento: int
    class Config:
        orm_mode = True  # Permite deserializar desde ORM
```

### 5. Convención de Campos

- `id_*` para PKs: `id_paciente`, `id_tratamiento`
- `*_id` para FKs: `paciente_id`, `podologo_id`
- Timestamps: `created_at`, `updated_at` (auto con func.now())
- Estado: `estado` (string con valores discretos: "activo", "completado")
- Soft delete: `activo` (boolean, no DELETE)

## Flujo de Desarrollo

### Agregar un Nuevo Endpoint

1. **Crear/Editar modelo SQLAlchemy** en `backend/schemas/{auth|core|ops}/models.py`
   - Define `__table_args__ = {"schema": "..."}` explícitamente
   - Usa `TIMESTAMP(timezone=True)` para timestampz

2. **Crear schema Pydantic** en `backend/schemas/{auth|core|ops}/schemas.py`
   - Base, Create, Update, Response

3. **Crear ruta** en `backend/api/routes/{module}.py`
   ```python
   @router.post("", response_model=TratamientoResponse)
   async def create_tratamiento(
       tratamiento_in: TratamientoCreate,
       current_user: SysUsuario = Depends(get_current_active_user),
       db: Session = Depends(get_core_db)
   ):
       # Validar permisos con current_user.rol
       # db.add(tratamiento)
       # db.commit()
   ```

4. **Incluir router en app.py**
   ```python
   from backend.api.routes import tratamientos
   app.include_router(tratamientos.router)
   ```

### Estructura de Sesiones

Las sesiones **SIEMPRE** son `Depends()`:

```python
# ✅ CORRECTO - FastAPI inyecta y cierra automáticamente
async def endpoint(db: Session = Depends(get_core_db)):
    paciente = db.query(Paciente).first()
    db.add(paciente)
    db.commit()
    return paciente

# ❌ INCORRECTO - ManualSession leakage
engine = create_engine(...)
session = Session()
paciente = session.query(Paciente).first()
```

### Pruebas Comunes

```bash
# Levantar stack completo
docker-compose up -d

# Ejecutar backend
cd backend
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

# Acceder a Swagger
http://localhost:8000/docs

# Conectar a BD directamente
docker exec -it podoskin-db psql -U podoskin -d clinica_core_db
```

## Archivos Críticos

- `backend/api/app.py` → FastAPI app + CORS + routers
- `backend/api/core/config.py` → Configuración (ENV vars)
- `backend/api/core/security.py` → JWT create/verify
- `backend/api/deps/database.py` → 3 generadores de sesiones
- `backend/api/deps/auth.py` → get_current_user dependency
- `backend/api/deps/permissions.py` → RBAC require_role()
- `backend/schemas/{auth|core|ops}/models.py` → ORM models
- `Docs/Desarrollo/` → Especificaciones de BD y modelos

## Convenciones de Respuesta

- `200 OK`: GET, PUT exitosos
- `201 Created`: POST exitoso (include Location header)
- `204 No Content`: DELETE exitoso
- `400 Bad Request`: Validación Pydantic falló
- `401 Unauthorized`: Token ausente/inválido
- `403 Forbidden`: Autenticado pero sin permisos
- `404 Not Found`: Recurso no existe
- `409 Conflict`: Violación de constraint único

```python
raise HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Solo Admin puede crear usuarios"
)
```

## Configuración (.env)

```bash
# Base de datos (3 URLs distintas)
AUTH_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db
CORE_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db
OPS_DB_URL=postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db

# JWT
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# App
DEBUG=True
APP_NAME="PodoSkin API"
```

## Notas de Implementación

- **Soft deletes**: Nunca DELETE. Usar `activo=False` + queries con `WHERE activo=True`
- **Auditoría**: Todos los cambios van a `auth.audit_logs` (implementar en cada POST/PUT/DELETE)
- **Multi-tenant**: Estructura preparada para múltiples clínicas; actualmente 1 clínica
- **Cross-DB validation**: FKs entre BDs se validan en la app, no en PostgreSQL
- **Computed columns**: IMC en pacientes se calcula automáticamente en PostgreSQL

---

**Última actualización**: 11 de diciembre de 2025

## Testing y Herramientas de Desarrollo

### Suite de Testing con pytest

El proyecto incluye una infraestructura completa de testing:

**Ubicación**: `backend/tests/`

**Cobertura actual**:
- 120+ tests implementados
- 84 funciones de test
- ~85-90% cobertura en módulos principales (auth, pacientes, citas)

**Archivos clave**:
- `conftest.py` - Fixtures globales (sessions de BD, usuarios de prueba, auth headers)
- `unit/test_auth_endpoints.py` - 25 tests de autenticación
- `unit/test_pacientes_endpoints.py` - 45+ tests de pacientes
- `unit/test_citas_endpoints.py` - 50+ tests de citas
- `factories/__init__.py` - Generadores de datos fake con Faker
- `scripts/seed_test_data.py` - Generador de datos de prueba (563 líneas)
- `scripts/clean_database.py` - Limpieza de BD de prueba (343 líneas)

**Ejecutar tests**:
```bash
cd backend
pytest -v                              # Todos los tests
pytest tests/unit/test_auth_endpoints.py -v  # Módulo específico
pytest -m auth                         # Por marcador
pytest --cov=backend/api --cov-report=html  # Con cobertura
```

**Generar datos de prueba**:
```bash
python tests/scripts/seed_test_data.py --count 100 --clean
```

Genera automáticamente:
- Usuarios (admin, podólogos, recepcionistas)
- 50-100 pacientes con datos realistas en español
- Tratamientos, evoluciones, evidencias
- Citas distribuidas en ±3 meses
- Transacciones financieras

**Credenciales de prueba**:
- Admin: `admin` / `admin123`
- Podólogo: `podologo1` / `podo123`
- Recepción: `recepcion1` / `recep123`

### Chatbot de Terminal con IA

**Ubicación**: `backend/tools/terminal_chatbot.py` (514 líneas)

Un asistente inteligente que permite consultas en lenguaje natural sobre la base de datos.

**Tecnología**:
- Anthropic Claude 3.5 Haiku
- LangGraph workflow
- NL-to-SQL converter
- Mathematical analyzer
- Fuzzy search

**Configuración**:
```bash
# En backend/.env
ANTHROPIC_API_KEY=tu-api-key-aqui
CLAUDE_MODEL=claude-3-5-haiku-20241022
CLAUDE_TEMPERATURE=0.1
```

**Uso**:
```bash
cd backend
python tools/terminal_chatbot.py              # Modo interactivo
python tools/terminal_chatbot.py --single "query"  # Consulta única
```

**Comandos especiales**:
- `/help` - Ayuda
- `/ejemplos` - Ver ejemplos
- `/stats` - Estadísticas del sistema
- `/history` - Historial de conversación
- `/exit` - Salir

**Ejemplos de consultas**:
```
¿Cuántos pacientes con sobrepeso tuvimos la semana pasada?
¿Cuánto es el 20% de las ganancias después de gastos la semana pasada?
¿Qué pacientes tienen citas mañana?
¿Cuál es el horario del Dr. Martínez esta semana?
```

**Herramientas de soporte**:
- `tools/sql_executor.py` - NL-to-SQL conversion
- `tools/mathematical_analyzer.py` - Cálculos matemáticos sobre datos
- `tools/fuzzy_search.py` - Búsqueda inteligente tolerante a errores
- `tools/schema_info.py` - Información de esquemas de BD
- `tools/appointment_manager.py` - Gestión inteligente de citas

### Documentación de Testing

- **Guía completa**: `backend/tests/README.md` (587 líneas)
- **Quick start**: `backend/tests/QUICKSTART.md` (182 líneas)
- **Informe para cliente**: `Docs/Informes/Testing_y_Herramientas_IA.md`

### Convenciones de Testing

**Marcadores pytest**:
```python
@pytest.mark.auth        # Tests de autenticación
@pytest.mark.api         # Tests de endpoints API
@pytest.mark.database    # Tests que usan BD
@pytest.mark.integration # Tests de integración
@pytest.mark.security    # Tests de seguridad
@pytest.mark.rbac        # Tests de permisos
```

**Fixtures disponibles** (definidos en `conftest.py`):
- `client` - TestClient de FastAPI
- `auth_db`, `core_db`, `ops_db` - Sesiones de BD de prueba
- `test_admin_user`, `test_podologo_user`, `test_recepcion_user` - Usuarios
- `admin_token`, `podologo_token`, `recepcion_token` - JWT tokens
- `auth_headers_admin`, `auth_headers_podologo`, `auth_headers_recepcion` - Headers HTTP
- `test_paciente`, `test_podologo` - Datos de prueba

**Patrón de test**:
```python
@pytest.mark.api
@pytest.mark.database
class TestPacientesListar:
    """Tests de listado de pacientes."""
    
    def test_list_success_admin(self, client, auth_headers_admin):
        """Test: Admin puede listar pacientes."""
        response = client.get("/api/v1/pacientes", headers=auth_headers_admin)
        assert response.status_code == 200
```

---

**Última actualización**: 11 de diciembre de 2025

## Pydantic (schemas) — Guía práctica y ejemplos

Foco: aquí explicamos cómo definir y validar `pydantic` models (v2) usados por los endpoints.

- Uso recomendado: definir `Base`, `Create`, `Update`, `Response` por recurso. Ejemplo concreto:

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
from pydantic.dataclasses import dataclass
from pydantic import ConfigDict
from datetime import date

class PacienteCreate(BaseModel):
    nombre: str = Field(..., min_length=2)
    apellidos: str = Field(..., min_length=2)
    fecha_nacimiento: date
    telefono: str = Field(..., min_length=7)
    email: EmailStr | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("fecha_nacimiento")
    @classmethod
    def fecha_must_be_past(cls, v: date):
        from datetime import date as _date
        if v >= _date.today():
            raise ValueError("fecha_nacimiento debe ser anterior a hoy")
        return v
```

- `Update` models deben permitir `Optional` para operaciones parciales. Ejemplo:

```python
class PacienteUpdate(BaseModel):
    telefono: str | None = None
    domicilio: str | None = None
    email: EmailStr | None = None
    model_config = ConfigDict(from_attributes=True)
```

- `Response` models deben permitir conversión desde objetos ORM:

```python
class PacienteResponse(BaseModel):
    id_paciente: int
    nombres: str
    apellidos: str
    fecha_nacimiento: date

    model_config = ConfigDict(from_attributes=True)
```

Ejemplos en el repo: ver `backend/schemas/core/schemas_examples.py` (archivo nuevo de referencia).

Integración con endpoints:

```python
@router.post("/pacientes", response_model=PacienteResponse)
def create_paciente(p: PacienteCreate, db: Session = Depends(get_core_db), user: SysUsuario = Depends(get_current_active_user)):
    # Validación ya hecha por Pydantic; aplicar reglas de negocio adicionales aquí
    paciente = Paciente(
        nombres=p.nombre, apellidos=p.apellidos, fecha_nacimiento=p.fecha_nacimiento,
        telefono=p.telefono, email=p.email
    )
    db.add(paciente)
    db.commit()
    db.refresh(paciente)
    return paciente
```

Notas prácticas:
- Validación cruzada (p.ej. FK virtual a otra BD) debe hacerse en el endpoint: usar `get_ops_db()` o `get_auth_db()` para verificar existencia.
- Usar `field_validator` y `model_validator` (pydantic v2) para reglas complejas (fechas, rangos, inter-campos).
- Mantener `model_config = ConfigDict(from_attributes=True)` para facilitar `response_model` desde instancias SQLAlchemy.

Si quieres, puedo: (A) añadir más modelos de ejemplo (Tratamiento, Evolucion), (B) implementar endpoints reales que usen las validaciones cruzadas, o (C) escribir tests más exhaustivos.
