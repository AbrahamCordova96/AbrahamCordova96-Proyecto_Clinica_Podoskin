# Gestión de API Keys de Gemini - Guía de Implementación

Este documento describe cómo implementar la gestión segura de API Keys de Google Gemini por usuario.

## 📋 Resumen de Cambios

Se agregaron las siguientes funcionalidades al backend:

1. **Modelo de datos**: 3 nuevas columnas en `auth.sys_usuarios`
2. **Encriptación**: Servicio de encriptación con Fernet (symmetric encryption)
3. **Validación**: Validador de API Keys contra la API de Google Gemini
4. **Endpoints**: 3 nuevos endpoints para gestionar API Keys
5. **Login**: Modificado para incluir estado de API Key
6. **Catálogo**: 8 comandos disponibles para el chatbot

---

## 🗄️ Paso 1: Ejecutar Migración de Base de Datos

### Opción A: Ejecutar manualmente con psql

```bash
# Conectar a la base de datos de autenticación
docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db

# Ejecutar el script de migración
\i /app/schemas/migrations/002_add_gemini_api_key.sql

# Verificar que las columnas se agregaron
\d auth.sys_usuarios

# Salir
\q
```

### Opción B: Ejecutar desde el host

```bash
# Copiar el script al contenedor
docker cp backend/schemas/migrations/002_add_gemini_api_key.sql podoskin-db:/tmp/

# Ejecutar el script
docker exec -it podoskin-db psql -U podoskin -d clinica_auth_db -f /tmp/002_add_gemini_api_key.sql
```

### Verificación

Después de ejecutar la migración, verifica que las columnas existan:

```sql
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'auth' 
  AND table_name = 'sys_usuarios'
  AND column_name LIKE 'gemini%'
ORDER BY column_name;
```

Deberías ver:
- `gemini_api_key_encrypted` (character varying(500), nullable)
- `gemini_api_key_last_validated` (timestamp with time zone, nullable)
- `gemini_api_key_updated_at` (timestamp with time zone, nullable)

---

## 🔐 Paso 2: Configurar Clave de Encriptación

### Generar clave de encriptación

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Esto generará una clave como: `yX5MtVv7OA99-L8jZ-WPMIEdo7i460T-F_bfa0GwV2k=`

### Agregar a archivo .env

Editar `backend/.env` y agregar:

```bash
# Clave de encriptación para API Keys (Fernet)
ENCRYPTION_KEY=yX5MtVv7OA99-L8jZ-WPMIEdo7i460T-F_bfa0GwV2k=
```

⚠️ **IMPORTANTE:** 
- Esta clave debe ser única y secreta
- En producción, usar variables de entorno del sistema operativo
- Hacer backup de esta clave (si se pierde, las API Keys no se pueden recuperar)
- Rotar periódicamente (cada 6-12 meses)

---

## 🧪 Paso 3: Probar la Encriptación

```bash
cd backend
python test_encryption_simple.py
```

Deberías ver:

```
============================================================
TEST SIMPLE DE ENCRIPTACIÓN FERNET
============================================================
...
✅ TODOS LOS TESTS DE ENCRIPTACIÓN PASARON
============================================================
```

---

## 📝 Paso 4: Instalar Dependencias

Si aún no está instalada:

```bash
cd backend
pip install cryptography==41.0.7
```

O instalar todas las dependencias:

```bash
pip install -r requirements.txt
```

---

## 🚀 Paso 5: Probar los Endpoints

### 5.1 Login (debe incluir estado de API Key)

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'
```

Respuesta esperada:

```json
{
  "access_token": "eyJ0eXAi...",
  "token_type": "bearer",
  "user": {
    "id_usuario": 1,
    "nombre_usuario": "admin",
    "email": "admin@podoskin.com",
    "rol": "Admin",
    "clinica_id": 1,
    "has_gemini_key": false,
    "gemini_key_status": null
  }
}
```

### 5.2 Actualizar API Key

```bash
# Guardar token
export TOKEN="tu_token_aqui"

# Actualizar API Key
curl -X PUT http://localhost:8000/api/v1/usuarios/1/gemini-key \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"api_key":"AIzaSyC1234567890abcdefghijklmnopqrstuv"}'
```

⚠️ **NOTA:** Para que la validación funcione, necesitas una API Key real de Google Gemini.  
Obtener una en: https://makersuite.google.com/app/apikey

### 5.3 Ver estado de API Key

```bash
curl -X GET http://localhost:8000/api/v1/usuarios/1/gemini-key/status \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta esperada:

```json
{
  "has_key": true,
  "is_valid": true,
  "last_updated": "2024-12-12T10:30:00Z",
  "last_validated": "2024-12-12T10:30:00Z"
}
```

### 5.4 Eliminar API Key

```bash
curl -X DELETE http://localhost:8000/api/v1/usuarios/1/gemini-key \
  -H "Authorization: Bearer $TOKEN"
```

### 5.5 Obtener catálogo de comandos

```bash
curl -X GET http://localhost:8000/api/v1/chat/commands \
  -H "Authorization: Bearer $TOKEN"
```

Respuesta esperada:

```json
{
  "total": 8,
  "commands": [
    {
      "id": "list_appointments_today",
      "name": "Listar citas de hoy",
      "description": "Obtiene todas las citas programadas para el día actual",
      "category": "Citas",
      "examples": ["Citas de hoy", "¿Qué citas tengo hoy?"],
      ...
    },
    ...
  ],
  "user_role": "Admin",
  "user_id": 1
}
```

---

## 🏗️ Arquitectura de la Solución

### Flujo de Encriptación

```
Usuario → Frontend → Backend
                       ↓
                  Validar contra Gemini API
                       ↓
                  Encriptar con Fernet
                       ↓
                  Guardar en PostgreSQL (encriptada)
```

### Flujo de Desencriptación

```
Backend → Leer de PostgreSQL (encriptada)
             ↓
        Desencriptar con Fernet
             ↓
        Usar para llamadas a Gemini API
```

### Seguridad

- **Encriptación:** Fernet (AES-128-CBC + HMAC)
- **Validación:** Contra API de Google antes de guardar
- **Almacenamiento:** Nunca en texto plano
- **Logs:** Solo primeros 10 caracteres de la key
- **Acceso:** Solo el usuario o Admin pueden gestionar la key

---

## 📊 Estructura de la Base de Datos

### Tabla: auth.sys_usuarios (modificada)

```sql
CREATE TABLE auth.sys_usuarios (
    -- Campos existentes...
    id_usuario BIGINT PRIMARY KEY,
    nombre_usuario VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    rol VARCHAR NOT NULL,
    -- ...
    
    -- NUEVOS CAMPOS para API Key de Gemini
    gemini_api_key_encrypted VARCHAR(500),
    gemini_api_key_updated_at TIMESTAMPTZ,
    gemini_api_key_last_validated TIMESTAMPTZ
);

-- Índice para búsquedas eficientes
CREATE INDEX idx_usuarios_gemini_key 
ON auth.sys_usuarios(id_usuario) 
WHERE gemini_api_key_encrypted IS NOT NULL;
```

---

## 🔌 Endpoints Nuevos

### GET /api/v1/usuarios/{id}/gemini-key/status

Obtiene el estado de la API Key de un usuario.

**Permisos:** Usuario propio o Admin

**Respuesta:**
```json
{
  "has_key": true,
  "is_valid": true,
  "last_updated": "2024-12-12T10:30:00Z",
  "last_validated": "2024-12-12T10:30:00Z"
}
```

### PUT /api/v1/usuarios/{id}/gemini-key

Actualiza la API Key de un usuario.

**Permisos:** Usuario propio o Admin

**Request:**
```json
{
  "api_key": "AIzaSyC1234567890abcdefghijklmnopqrstuv"
}
```

**Respuesta:**
```json
{
  "message": "API Key de Gemini actualizada exitosamente",
  "status": "valid",
  "updated_at": "2024-12-12T10:30:00Z"
}
```

### DELETE /api/v1/usuarios/{id}/gemini-key

Elimina la API Key de un usuario.

**Permisos:** Usuario propio o Admin

**Respuesta:**
```json
{
  "message": "API Key de Gemini eliminada exitosamente"
}
```

### GET /api/v1/chat/commands

Lista todos los comandos disponibles para el chatbot, filtrados por rol.

**Permisos:** Cualquier usuario autenticado

**Respuesta:**
```json
{
  "total": 8,
  "commands": [...],
  "user_role": "Admin",
  "user_id": 1
}
```

### GET /api/v1/chat/commands/{command_id}

Obtiene detalles de un comando específico.

**Permisos:** Usuario con rol apropiado para el comando

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'cryptography'"

```bash
pip install cryptography==41.0.7
```

### Error: "La clave de encriptación no es válida"

1. Generar nueva clave:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

2. Actualizar en `backend/.env`:
   ```bash
   ENCRYPTION_KEY=nueva_clave_aqui
   ```

3. Reiniciar backend:
   ```bash
   docker restart podoskin-backend
   ```

### Error: "API Key inválida"

La validación contra Gemini API falló. Posibles causas:

1. **API Key incorrecta:** Verificar que sea una key válida de Google
2. **Sin internet:** El backend necesita conexión para validar
3. **Rate limit:** Google limita requests. Esperar unos minutos
4. **API Key sin permisos:** Activar Gemini API en Google Cloud Console

### Error: "Token inválido al desencriptar"

La `ENCRYPTION_KEY` cambió desde que se encriptó la API Key. Soluciones:

1. **Restaurar clave original:** Si tienes backup
2. **Pedir al usuario que reconfigure:** Eliminar y volver a agregar API Key

---

## 📚 Referencias

- [Cryptography - Fernet](https://cryptography.io/en/latest/fernet/)
- [Google Gemini API](https://ai.google.dev/gemini-api/docs)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## ✅ Checklist de Implementación

- [ ] Migración SQL ejecutada
- [ ] Clave de encriptación generada y configurada en .env
- [ ] Dependencias instaladas (cryptography)
- [ ] Tests de encriptación pasando
- [ ] Endpoint de login modificado y funcionando
- [ ] Endpoints de API Key funcionando
- [ ] Catálogo de comandos accesible
- [ ] Documentación actualizada

---

**Última actualización:** 12 de diciembre de 2024  
**Versión:** 1.0.0
