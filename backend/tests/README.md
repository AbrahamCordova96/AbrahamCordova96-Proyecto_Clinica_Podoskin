# 🧪 Guía Completa de Testing - PodoSkin API

## 📋 Tabla de Contenidos

1. [Introducción](#introducción)
2. [Instalación de Dependencias](#instalación-de-dependencias)
3. [Estructura de Tests](#estructura-de-tests)
4. [Ejecutar Tests](#ejecutar-tests)
5. [Generación de Datos de Prueba](#generación-de-datos-de-prueba)
6. [Limpieza de Base de Datos](#limpieza-de-base-de-datos)
7. [Chatbot de Terminal](#chatbot-de-terminal)
8. [Cobertura de Tests](#cobertura-de-tests)
9. [Guía de Contribución](#guía-de-contribución)

---

## 🎯 Introducción

Esta suite de testing cubre los **103 endpoints** de la API PodoSkin con tests unitarios, de integración y de flujos completos (workflows).

### Tipos de Tests

- **Unitarios**: Testean endpoints individuales
- **Integración**: Testean flujos de múltiples endpoints
- **RBAC**: Verifican permisos por rol (Admin, Podologo, Recepcion)
- **Seguridad**: Validan autenticación, rate limiting, etc.

---

## 📦 Instalación de Dependencias

### 1. Activar Entorno Virtual

```bash
# Windows PowerShell
cd backend
.\venv\Scripts\Activate.ps1

# Linux/Mac
cd backend
source venv/bin/activate
```

### 2. Instalar Dependencias de Testing

```bash
# Instalar todas las dependencias de testing
pip install -r requirements-test.txt

# O instalar manualmente
pip install pytest pytest-asyncio pytest-cov pytest-mock faker factory-boy
```

### 3. Verificar Instalación

```bash
pytest --version
# Debe mostrar: pytest 8.3.4 o superior
```

---

## 📁 Estructura de Tests

```
backend/tests/
├── conftest.py                 # Configuración global y fixtures
├── pytest.ini                  # Configuración de pytest
├── unit/                       # Tests unitarios por módulo
│   ├── test_auth_endpoints.py       # Auth (3 endpoints, 25 tests)
│   ├── test_pacientes_endpoints.py  # Pacientes (8 endpoints, 45+ tests)
│   ├── test_citas_endpoints.py      # Citas (8 endpoints, 50+ tests)
│   ├── test_usuarios_endpoints.py   # Usuarios (pendiente)
│   └── ...
├── integration/                # Tests de integración
│   ├── test_patient_workflow.py
│   ├── test_appointment_flow.py
│   └── ...
├── factories/                  # Generadores de datos fake
│   └── __init__.py
├── fixtures/                   # Fixtures específicos
└── scripts/                    # Scripts de utilidad
    ├── seed_test_data.py      # Generar datos placebo
    └── clean_database.py      # Limpiar base de datos
```

---

## ▶️ Ejecutar Tests

### Ejecutar TODOS los Tests

```bash
cd backend
pytest
```

### Ejecutar Tests Específicos

```bash
# Por módulo
pytest tests/unit/test_auth_endpoints.py
pytest tests/unit/test_pacientes_endpoints.py
pytest tests/unit/test_citas_endpoints.py

# Por clase de test
pytest tests/unit/test_auth_endpoints.py::TestAuthLogin

# Test individual
pytest tests/unit/test_auth_endpoints.py::TestAuthLogin::test_login_success_admin

# Por marcador
pytest -m auth              # Solo tests de autenticación
pytest -m api               # Solo tests de API
pytest -m integration       # Solo tests de integración
pytest -m "not slow"        # Excluir tests lentos
```

### Ejecutar con Cobertura

```bash
# Con reporte en terminal
pytest --cov=backend/api --cov-report=term-missing

# Generar reporte HTML
pytest --cov=backend/api --cov-report=html
# Ver reporte: open backend/tests/coverage_html/index.html
```

### Modo Verbose (Detallado)

```bash
# Ver cada test que se ejecuta
pytest -v

# Modo super detallado
pytest -vv

# Ver print statements
pytest -s
```

### Ejecutar Tests en Paralelo

```bash
# Instalar pytest-xdist
pip install pytest-xdist

# Ejecutar con 4 workers
pytest -n 4
```

---

## 🌱 Generación de Datos de Prueba

El script `seed_test_data.py` genera datos placebo realistas en español para poblar la base de datos.

### Uso Básico

```bash
cd backend

# Generar datos por defecto (50 registros por entidad)
python tests/scripts/seed_test_data.py --clean

# Generar más datos
python tests/scripts/seed_test_data.py --count 100 --clean

# Ver ayuda
python tests/scripts/seed_test_data.py --help
```

### Opciones

- `--count N`: Cantidad de registros a generar (default: 50)
- `--clean`: Limpiar datos existentes antes de generar
- `--db TYPE`: Tipo de BD (sqlite|postgres, default: postgres)

### Datos Generados

El script crea:

- ✅ **1 Clínica** principal
- ✅ **Usuarios** (admin, podólogos, recepcionistas)
- ✅ **50-100 Pacientes** con datos realistas
- ✅ **Tratamientos** (70% de pacientes tienen al menos 1)
- ✅ **Evoluciones clínicas** (2-5 por tratamiento)
- ✅ **Evidencias fotográficas** simuladas
- ✅ **Podólogos** (5-10 profesionales)
- ✅ **Servicios** del catálogo
- ✅ **Citas** (distribuidas en ±3 meses)
- ✅ **Prospectos** (leads)
- ✅ **Transacciones y Pagos**
- ✅ **Gastos** operativos

### Credenciales Generadas

```
Admin:        admin / admin123
Podólogo:     podologo1 / podo123
Recepción:    recepcion1 / recep123
```

### Ejemplo de Salida

```
============================================================================
🌱 GENERADOR DE DATOS DE PRUEBA - PODOSKIN
============================================================================
📊 Cantidad de registros: 50
🧹 Limpiar primero: Sí
============================================================================

📊 Conectando a bases de datos...
🧹 Limpiando datos existentes...
✅ Datos limpiados exitosamente

🔐 Generando datos de autenticación...
  ✓ Clínica: PodoSkin - Clínica Central
  ✓ 11 usuarios creados

🏥 Generando datos clínicos...
  ✓ 50 pacientes creados
  ✓ 35 tratamientos creados
  ✓ 123 evoluciones clínicas creadas

📅 Generando datos operacionales...
  ✓ 5 métodos de pago creados
  ✓ 5 podólogos creados
  ✓ 8 servicios creados
  ✓ 100 citas creadas
  ✓ 10 prospectos creados

💰 Generando datos financieros...
  ✓ 50 transacciones creadas
  ✓ 50 pagos creados
  ✓ 25 gastos creados

============================================================================
✅ GENERACIÓN COMPLETADA
============================================================================
```

---

## 🧹 Limpieza de Base de Datos

El script `clean_database.py` limpia y formatea las bases de datos.

### ⚠️ ADVERTENCIA

**Este script BORRA TODOS LOS DATOS. Solo usar en desarrollo/testing.**

### Uso

```bash
cd backend

# Limpiar todas las BDs (requiere confirmación)
python tests/scripts/clean_database.py --confirm

# Limpiar y recrear schemas
python tests/scripts/clean_database.py --confirm --reset

# Solo limpiar una BD específica
python tests/scripts/clean_database.py --confirm --db auth
python tests/scripts/clean_database.py --confirm --db core
python tests/scripts/clean_database.py --confirm --db ops

# Solo verificar estado (no borra)
python tests/scripts/clean_database.py --verify
```

### Opciones

- `--confirm`: **Requerido** para confirmar limpieza (seguridad)
- `--reset`: Borrar y recrear schemas completos
- `--db TYPE`: BD específica (auth|core|ops|all, default: all)
- `--verify`: Solo verificar estado sin limpiar

### Flujo de Trabajo Típico

```bash
# 1. Limpiar todo
python tests/scripts/clean_database.py --confirm --reset

# 2. Generar datos de prueba
python tests/scripts/seed_test_data.py --count 100 --clean

# 3. Ejecutar tests
pytest

# 4. Verificar estado
python tests/scripts/clean_database.py --verify
```

---

## 🤖 Chatbot de Terminal

El chatbot de terminal permite interactuar con el sistema en **lenguaje natural**.

### Instalación de Dependencias Adicionales

```bash
# Para mejor experiencia visual (opcional)
pip install rich
```

### Ejecución

```bash
cd backend

# Modo interactivo
python tools/terminal_chatbot.py

# Consulta única
python tools/terminal_chatbot.py --single "¿Cuántos pacientes tenemos hoy?"
```

### Comandos Especiales

Dentro del chatbot:

- `/help` - Mostrar ayuda
- `/ejemplos` - Ver ejemplos de consultas
- `/stats` - Estadísticas del sistema
- `/clear` - Limpiar pantalla
- `/history` - Ver historial de conversación
- `/exit` o `/quit` - Salir

### Ejemplos de Consultas

#### 📊 Estadísticas de Pacientes

```
¿Cuántas personas con sobrepeso tuvimos la semana pasada?
Dame la lista de pacientes mayores de 60 años
¿Cuántos pacientes nuevos hubo este mes?
Muéstrame la distribución de pacientes por sexo
```

#### 💰 Análisis Financiero

```
¿Cuánto sería el 20% de las ganancias después de gastos la semana pasada?
Dame un resumen de ingresos vs gastos del mes
¿Cuál fue el ingreso total de noviembre?
Muéstrame los gastos de la última semana
Calcula el margen de ganancia del último trimestre
```

#### 📅 Gestión de Citas

```
¿Qué pacientes tienen citas mañana?
Muéstrame el horario completo de esta semana
¿Cuántas citas completadas hubo hoy?
¿Hay espacios disponibles el viernes?
¿Cuál es la tasa de no-asistencia este mes?
```

#### 👨‍⚕️ Staff y Horarios

```
¿Cuál es el horario del Dr. Martínez esta semana?
¿Qué podólogos están disponibles mañana?
Muéstrame la carga de trabajo de cada podólogo
¿Quién atendió más pacientes este mes?
```

#### 💊 Tratamientos

```
¿Cuántos tratamientos activos tenemos?
Muéstrame pacientes con tratamiento de onicomicosis
¿Qué tratamientos se completaron este mes?
Dame estadísticas de los problemas más comunes
```

### Configuración

El chatbot requiere configurar la API key de Anthropic en `.env`:

```bash
# backend/.env
ANTHROPIC_API_KEY=tu-api-key-aqui
CLAUDE_MODEL=claude-3-5-haiku-20241022
CLAUDE_TEMPERATURE=0.1
```

---

## 📊 Cobertura de Tests

### Ver Cobertura Actual

```bash
# Generar reporte de cobertura
pytest --cov=backend/api --cov-report=term-missing

# Generar reporte HTML detallado
pytest --cov=backend/api --cov-report=html

# Ver en navegador
open backend/tests/coverage_html/index.html  # Mac
xdg-open backend/tests/coverage_html/index.html  # Linux
start backend/tests/coverage_html/index.html  # Windows
```

### Estado Actual de Cobertura por Módulo

| Módulo | Endpoints | Tests | Cobertura |
|--------|-----------|-------|-----------|
| 🔐 Auth | 3 | ✅ 25 | ~90% |
| 👥 Pacientes | 8 | ✅ 45+ | ~85% |
| 📅 Citas | 8 | ✅ 50+ | ~85% |
| 🔧 Usuarios | 6 | ⏳ Pendiente | 0% |
| 💊 Tratamientos | 6 | ⏳ Pendiente | 0% |
| 📈 Evoluciones | 5 | ⏳ Pendiente | 0% |
| 📸 Evidencias | 8 | ⏳ Pendiente | 0% |
| 👨‍⚕️ Podólogos | 5 | ⏳ Pendiente | 0% |
| 📋 Servicios | 5 | ⏳ Pendiente | 0% |
| 💼 Prospectos | 5 | ⏳ Pendiente | 0% |
| 📜 Historial | 20 | ⏳ Pendiente | 0% |
| 💰 Finance | 6 | ⏳ Pendiente | 0% |
| 🛡️ Audit | 3 | ⏳ Pendiente | 0% |
| 📊 Statistics | 2 | ⏳ Pendiente | 0% |
| 📧 Notifications | 3 | ⏳ Pendiente | 0% |

**Total**: 120+ tests de 103 endpoints (~12% cobertura completa)

---

## 🤝 Guía de Contribución

### Agregar Nuevos Tests

#### 1. Crear archivo de test

```python
# backend/tests/unit/test_nuevo_modulo.py

import pytest

@pytest.mark.api
@pytest.mark.database
class TestNuevoModuloListar:
    """Tests de listado."""
    
    def test_list_success(self, client, auth_headers_admin):
        """Test: Listar como admin."""
        response = client.get(
            "/api/v1/nuevo-modulo",
            headers=auth_headers_admin
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data
```

#### 2. Usar fixtures existentes

Fixtures disponibles en `conftest.py`:

- `client`: TestClient de FastAPI
- `auth_db`, `core_db`, `ops_db`: Sesiones de BD
- `test_admin_user`, `test_podologo_user`, `test_recepcion_user`: Usuarios de prueba
- `admin_token`, `podologo_token`, `recepcion_token`: Tokens JWT
- `auth_headers_admin`, `auth_headers_podologo`, `auth_headers_recepcion`: Headers con auth
- `test_paciente`, `test_podologo`: Datos de prueba

#### 3. Agregar marcadores

```python
@pytest.mark.auth        # Tests de autenticación
@pytest.mark.api         # Tests de endpoints API
@pytest.mark.database    # Tests que usan BD
@pytest.mark.integration # Tests de integración
@pytest.mark.slow        # Tests lentos
@pytest.mark.security    # Tests de seguridad
@pytest.mark.rbac        # Tests de permisos
```

### Convenciones de Nomenclatura

- Clases: `TestModuloAccion` (ej: `TestPacientesListar`)
- Métodos: `test_descripcion_caso` (ej: `test_list_success_admin`)
- Fixtures: `test_nombre` o `nombre_fixture`

### Estructura de Test

```python
def test_descripcion_del_caso(self, client, auth_headers_admin):
    """Test: Descripción breve del caso de prueba."""
    
    # Arrange (preparar)
    data_to_send = {"field": "value"}
    
    # Act (actuar)
    response = client.post("/endpoint", headers=auth_headers_admin, json=data_to_send)
    
    # Assert (verificar)
    assert response.status_code == 200
    assert response.json()["field"] == "value"
```

---

## 🐛 Troubleshooting

### Error: No module named 'backend'

```bash
# Asegúrate de estar en el directorio correcto
cd backend
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."  # Linux/Mac
$env:PYTHONPATH = "$env:PYTHONPATH;$(Get-Location)\.."  # Windows
```

### Error: No se puede conectar a la BD

```bash
# Verificar que Docker esté corriendo
docker ps

# Iniciar base de datos
docker-compose up -d

# Verificar conexión
docker exec -it podoskin-db psql -U podoskin -d clinica_core_db -c "SELECT 1;"
```

### Tests fallan por timeout

```bash
# Aumentar timeout en pytest.ini
timeout = 600  # 10 minutos
```

### Error: ANTHROPIC_API_KEY no configurada

```bash
# Crear archivo .env en backend/
cd backend
echo "ANTHROPIC_API_KEY=tu-api-key-aqui" >> .env
```

---

## 📞 Soporte

Para preguntas o problemas:

1. Revisar esta documentación
2. Revisar logs de tests: `pytest -v -s`
3. Revisar archivo de configuración: `pytest.ini`
4. Verificar fixtures: `backend/tests/conftest.py`

---

## 📝 Changelog

### Versión 1.0.0 (Diciembre 2024)

- ✅ Infraestructura completa de testing con pytest
- ✅ 120+ tests para auth, pacientes y citas
- ✅ Scripts de seed y limpieza de BD
- ✅ Chatbot de terminal con IA
- ✅ Factories para generación de datos fake
- ✅ Fixtures globales y por módulo
- ✅ Documentación completa en español

---

**¡Listo para testing! 🚀**

```bash
# Quick start
cd backend
pip install -r requirements-test.txt
python tests/scripts/seed_test_data.py --clean
pytest -v
```
