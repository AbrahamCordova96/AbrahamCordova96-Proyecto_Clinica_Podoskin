#!/bin/bash
# Script de verificación de la implementación de API Keys de Gemini
# Ejecutar desde el directorio backend/

echo "============================================================"
echo "VERIFICACIÓN DE IMPLEMENTACIÓN - API KEYS DE GEMINI"
echo "============================================================"
echo ""

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Contador de checks
PASSED=0
FAILED=0

# Función para verificar
check() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗${NC} $2"
        FAILED=$((FAILED + 1))
    fi
}

# 1. Verificar que el archivo de migración existe
echo "=== 1. Verificando archivos de migración ==="
if [ -f "schemas/migrations/002_add_gemini_api_key.sql" ]; then
    check 0 "Archivo de migración SQL existe"
else
    check 1 "Archivo de migración SQL NO existe"
fi
echo ""

# 2. Verificar que los archivos de código existen
echo "=== 2. Verificando archivos de código ==="
files=(
    "api/core/encryption.py"
    "api/services/gemini_validator.py"
    "api/core/config.py"
    "schemas/auth/models.py"
    "schemas/auth/schemas.py"
    "api/routes/usuarios.py"
    "api/routes/auth.py"
    "api/routes/chat.py"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        check 0 "Archivo $file existe"
    else
        check 1 "Archivo $file NO existe"
    fi
done
echo ""

# 3. Verificar que cryptography está instalado
echo "=== 3. Verificando dependencias Python ==="
python -c "import cryptography" 2>/dev/null
check $? "Librería cryptography instalada"

python -c "from cryptography.fernet import Fernet" 2>/dev/null
check $? "Módulo Fernet disponible"
echo ""

# 4. Verificar que el archivo .env existe y tiene ENCRYPTION_KEY
echo "=== 4. Verificando configuración ==="
if [ -f ".env" ]; then
    check 0 "Archivo .env existe"
    
    if grep -q "ENCRYPTION_KEY" .env; then
        check 0 "Variable ENCRYPTION_KEY configurada en .env"
    else
        check 1 "Variable ENCRYPTION_KEY NO configurada en .env"
        echo -e "${YELLOW}   → Generar con: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"${NC}"
    fi
else
    check 1 "Archivo .env NO existe"
    echo -e "${YELLOW}   → Copiar desde .env.example y configurar${NC}"
fi
echo ""

# 5. Verificar que los imports son correctos
echo "=== 5. Verificando imports en código ==="
grep -q "from backend.api.core.encryption import" api/routes/usuarios.py
check $? "Import de encryption en usuarios.py"

grep -q "from backend.api.services.gemini_validator import" api/routes/usuarios.py
check $? "Import de gemini_validator en usuarios.py"

grep -q "from backend.api.core.encryption import" api/routes/auth.py
check $? "Import de encryption en auth.py"

grep -q "GeminiKeyUpdate" schemas/auth/schemas.py
check $? "Schema GeminiKeyUpdate en schemas.py"

grep -q "COMMAND_CATALOG" api/routes/chat.py
check $? "COMMAND_CATALOG en chat.py"
echo ""

# 6. Verificar sintaxis Python (básico)
echo "=== 6. Verificando sintaxis Python ==="
python -m py_compile api/core/encryption.py 2>/dev/null
check $? "Sintaxis de encryption.py válida"

python -m py_compile api/services/gemini_validator.py 2>/dev/null
check $? "Sintaxis de gemini_validator.py válida"
echo ""

# 7. Verificar que la documentación existe
echo "=== 7. Verificando documentación ==="
if [ -f "GEMINI_API_KEY_IMPLEMENTATION.md" ]; then
    check 0 "Documentación de implementación existe"
else
    check 1 "Documentación de implementación NO existe"
fi
echo ""

# Resumen
echo "============================================================"
echo "RESUMEN"
echo "============================================================"
echo -e "${GREEN}Checks pasados:${NC} $PASSED"
echo -e "${RED}Checks fallidos:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ TODOS LOS CHECKS PASARON${NC}"
    echo ""
    echo "Próximos pasos:"
    echo "1. Ejecutar migración SQL: docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db -f /tmp/002_add_gemini_api_key.sql"
    echo "2. Configurar ENCRYPTION_KEY en .env"
    echo "3. Reiniciar backend: docker restart podoskin-backend"
    echo "4. Probar endpoints con curl (ver GEMINI_API_KEY_IMPLEMENTATION.md)"
    exit 0
else
    echo -e "${RED}✗ ALGUNOS CHECKS FALLARON${NC}"
    echo ""
    echo "Revisar los errores arriba y corregir antes de continuar."
    exit 1
fi
