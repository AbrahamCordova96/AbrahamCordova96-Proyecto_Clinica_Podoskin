# 🚀 Inicio Rápido - Testing y Chatbot PodoSkin

## ⚡ Setup Rápido (5 minutos)

### 1. Instalar Dependencias

```bash
cd backend
pip install -r requirements-test.txt
```

### 2. Iniciar Base de Datos

```bash
# En la raíz del proyecto
docker-compose up -d
```

### 3. Generar Datos de Prueba

```bash
python tests/scripts/seed_test_data.py --count 50 --clean
```

**Credenciales generadas:**
- Admin: `admin / admin123`
- Podólogo: `podologo1 / podo123`
- Recepción: `recepcion1 / recep123`

### 4. Ejecutar Tests

```bash
# Todos los tests
pytest

# Con cobertura
pytest --cov=backend/api --cov-report=html

# Solo un módulo
pytest tests/unit/test_auth_endpoints.py -v
```

### 5. Probar Chatbot Terminal

```bash
# Configurar API key primero
echo "ANTHROPIC_API_KEY=tu-api-key" >> .env

# Iniciar chatbot
python tools/terminal_chatbot.py
```

**Ejemplos de consultas:**
```
¿Cuántas personas con sobrepeso tuvimos la semana pasada?
¿Cuánto es el 20% de las ganancias después de gastos la semana pasada?
Muéstrame las citas de mañana
¿Cuál es el horario del Dr. Martínez esta semana?
```

---

## 📊 Resultados Esperados

### Tests
```
============== test session starts ==============
collected 120 items

tests/unit/test_auth_endpoints.py::TestAuthLogin ✓✓✓✓✓✓✓✓✓✓ (10 passed)
tests/unit/test_auth_endpoints.py::TestAuthMe ✓✓✓✓✓✓ (6 passed)
tests/unit/test_auth_endpoints.py::TestAuthChangePassword ✓✓✓✓✓✓✓✓✓ (9 passed)
tests/unit/test_pacientes_endpoints.py ✓✓✓✓✓... (45+ passed)
tests/unit/test_citas_endpoints.py ✓✓✓✓✓... (50+ passed)

============== 120 passed in 8.52s ==============
```

### Datos de Prueba
```
✅ GENERACIÓN COMPLETADA
  🔐 Usuarios: 11
  🏥 Pacientes: 50
  💊 Tratamientos: 35
  👨‍⚕️ Podólogos: 5
  📅 Citas: 100
  💰 Transacciones: 50
```

### Chatbot
```
🦶 BIENVENIDO AL CHATBOT PODOSKIN IA

Tú: ¿Cuántos pacientes tenemos hoy?

🤖 Asistente:
Basándome en los datos actuales, tenemos 50 pacientes 
registrados en el sistema. De ellos, 5 tienen citas 
agendadas para hoy.

Tú: /exit
👋 ¡Hasta luego!
```

---

## 🎯 Comandos Útiles

```bash
# Testing
pytest -v                          # Verbose
pytest -m auth                     # Solo auth
pytest -k "test_login"             # Por nombre
pytest --lf                        # Solo últimos fallidos
pytest --cov-report=term-missing   # Cobertura detallada

# Base de Datos
python tests/scripts/clean_database.py --verify     # Ver estado
python tests/scripts/clean_database.py --confirm    # Limpiar
python tests/scripts/seed_test_data.py --count 100  # Más datos

# Chatbot
python tools/terminal_chatbot.py                    # Interactivo
python tools/terminal_chatbot.py --single "query"   # Una consulta
```

---

## 📚 Documentación Completa

Ver: `backend/tests/README.md` para guía completa de:
- Estructura de tests
- Generación de datos
- Limpieza de BD
- Uso del chatbot
- Contribuir con tests
- Troubleshooting

---

## ✅ Verificación

Para verificar que todo funciona:

```bash
# 1. Tests básicos pasan
pytest tests/unit/test_auth_endpoints.py::TestAuthLogin::test_login_success_admin -v

# 2. Seed funciona
python tests/scripts/seed_test_data.py --count 10 --clean

# 3. Limpieza funciona
python tests/scripts/clean_database.py --verify

# 4. Chatbot responde (requiere API key)
python tools/terminal_chatbot.py --single "¿Cuántos pacientes hay?"
```

---

## 🆘 Problemas Comunes

**Error: No module named 'backend'**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/.."
```

**Error: No se puede conectar a BD**
```bash
docker-compose up -d
docker ps  # Verificar que corra
```

**Error: ANTHROPIC_API_KEY no configurada**
```bash
# Editar backend/.env
ANTHROPIC_API_KEY=tu-api-key-aqui
```

---

**¡Listo para probar! 🎉**
