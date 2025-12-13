# 📋 Notas de Migración - Sistema de IDs Estructurados

**Fecha:** 13 de diciembre de 2024  
**Versión API:** v1  
**Breaking Changes:** SÍ (en endpoint POST /usuarios)

---

## ⚠️ Breaking Change en POST /usuarios

### Cambio en la API

El endpoint `POST /api/v1/usuarios` ahora requiere dos campos adicionales:

```diff
{
  "nombre_usuario": "santiago_ornelas",
  "password": "Ornelas2025!",
  "email": "santiago@podoskin.com",
  "rol": "Admin",
+ "nombre_completo": "Santiago",
+ "apellido_completo": "Ornelas Reynoso"
}
```

### Razón del Cambio

Los campos `nombre_completo` y `apellido_completo` son necesarios para generar el `codigo_interno` estructurado, que es un requisito de NOM-024.

### Impacto

- ✅ **Backend:** Funcional, genera IDs automáticamente
- ⚠️ **Clientes existentes:** Necesitan actualizar requests
- ✅ **Usuarios existentes:** No afectados, siguen funcionando

### Migración para Clientes

#### Opción 1: Actualizar el cliente (Recomendado)

Actualizar los requests para incluir los nuevos campos:

```javascript
// Antes
const createUser = async (username, password, email, role) => {
  return await api.post('/usuarios', {
    nombre_usuario: username,
    password: password,
    email: email,
    rol: role
  });
};

// Después
const createUser = async (username, password, email, role, nombreCompleto, apellidoCompleto) => {
  return await api.post('/usuarios', {
    nombre_usuario: username,
    password: password,
    email: email,
    rol: role,
    nombre_completo: nombreCompleto,      // NUEVO
    apellido_completo: apellidoCompleto   // NUEVO
  });
};
```

#### Opción 2: Valores por defecto (Temporal)

Si no puedes actualizar el cliente inmediatamente, puedes enviar valores genéricos:

```javascript
const createUser = async (username, password, email, role) => {
  return await api.post('/usuarios', {
    nombre_usuario: username,
    password: password,
    email: email,
    rol: role,
    nombre_completo: username.split('_')[0] || 'Usuario',  // Temporal
    apellido_completo: username.split('_')[1] || 'Sistema'  // Temporal
  });
};
```

**NOTA:** Esto generará IDs poco útiles. Actualizar a valores reales cuando sea posible.

---

## ✅ Sin Breaking Change en POST /pacientes

El endpoint `POST /api/v1/pacientes` **NO** tiene breaking changes porque usa los campos existentes `nombres` y `apellidos`.

```json
{
  "nombres": "María",
  "apellidos": "López García",
  "fecha_nacimiento": "1985-05-15",
  "telefono": "5551234567"
}
```

El `codigo_interno` se genera automáticamente sin requerir campos adicionales.

---

## 🔄 Estrategia de Migración de Datos

### Fase 1: Implementación Actual (Nullable)

**Estado:** ✅ Implementado

El campo `codigo_interno` es `nullable=True` en la base de datos.

**Ventajas:**
- ✅ No rompe datos existentes
- ✅ Permite migración gradual
- ✅ Sistema tolerante a fallos

**Desventajas:**
- ⚠️ Inconsistencia temporal (algunos tienen ID, otros no)
- ⚠️ Necesita validación adicional en queries

### Fase 2: Migración de Registros Existentes (Futuro)

**Cuándo:** Después de que el sistema esté estable en producción

**Script de migración sugerido:**

```python
# backend/scripts/migrate_existing_ids.py
"""
Genera codigo_interno para usuarios y pacientes existentes.
Ejecutar UNA VEZ después de deployment.
"""

from backend.api.deps.database import get_auth_db, get_core_db
from backend.schemas.auth.models import SysUsuario
from backend.schemas.core.models import Paciente
from backend.utils.id_generator import generar_codigo_interno
from datetime import datetime, timezone

def migrate_usuarios():
    db = next(get_auth_db())
    usuarios = db.query(SysUsuario).filter(
        SysUsuario.codigo_interno.is_(None)
    ).all()
    
    for usuario in usuarios:
        # Extraer nombre y apellido del username o email
        # Implementar lógica según convención de nombres
        nombre = input(f"Nombre para {usuario.nombre_usuario}: ")
        apellido = input(f"Apellido para {usuario.nombre_usuario}: ")
        
        codigo = generar_codigo_interno(
            apellido_paterno=apellido,
            nombre=nombre,
            fecha_registro=usuario.created_at or datetime.now(timezone.utc),
            model_class=SysUsuario,
            db=db
        )
        
        usuario.codigo_interno = codigo
        db.commit()
        print(f"✅ {usuario.nombre_usuario} → {codigo}")

def migrate_pacientes():
    db = next(get_core_db())
    pacientes = db.query(Paciente).filter(
        Paciente.codigo_interno.is_(None)
    ).all()
    
    for paciente in pacientes:
        # Usar campos existentes
        codigo = generar_codigo_interno(
            apellido_paterno=paciente.apellidos,
            nombre=paciente.nombres,
            fecha_registro=paciente.fecha_registro or datetime.now(timezone.utc),
            model_class=Paciente,
            db=db
        )
        
        paciente.codigo_interno = codigo
        db.commit()
        print(f"✅ {paciente.nombres} {paciente.apellidos} → {codigo}")
```

### Fase 3: Hacer NOT NULL (Futuro)

**Cuándo:** Después de que todos los registros tengan `codigo_interno`

**Migración SQL:**

```sql
-- Verificar que no hay NULLs
SELECT COUNT(*) FROM auth.sys_usuarios WHERE codigo_interno IS NULL;
SELECT COUNT(*) FROM clinic.pacientes WHERE codigo_interno IS NULL;

-- Si ambos retornan 0, proceder:
ALTER TABLE auth.sys_usuarios 
ALTER COLUMN codigo_interno SET NOT NULL;

ALTER TABLE clinic.pacientes 
ALTER COLUMN codigo_interno SET NOT NULL;
```

---

## 🛡️ Manejo de Errores

### Comportamiento Actual

Si falla la generación de `codigo_interno`:

1. **Se registra error detallado en logs** con `logger.error(..., exc_info=True)`
2. **Se registra warning explicativo** con implicaciones
3. **El registro se crea SIN codigo_interno** (campo queda NULL)
4. **El sistema continúa funcionando** (no se lanza excepción)

### Casos de Fallo

Posibles razones de fallo:
- Base de datos no responde temporalmente
- Nombre/apellido con caracteres inválidos
- Conflicto de unicidad (muy improbable)
- Error en la lógica de generación

### Monitoreo

**Logs a monitorear:**

```
ERROR generando codigo_interno para usuario 'X': <detalle>
WARNING Usuario 'X' creado SIN codigo_interno. Puede usar username/email para login.
```

**Query de verificación:**

```sql
-- Usuarios sin codigo_interno
SELECT id_usuario, nombre_usuario, created_at 
FROM auth.sys_usuarios 
WHERE codigo_interno IS NULL
ORDER BY created_at DESC;

-- Pacientes sin codigo_interno
SELECT id_paciente, nombres, apellidos, fecha_registro
FROM clinic.pacientes 
WHERE codigo_interno IS NULL
ORDER BY fecha_registro DESC;
```

---

## 📖 Documentación para Usuarios

### Login con ID Estructurado

Los usuarios pueden hacer login con:
- Username: `santiago_ornelas`
- Email: `santiago@podoskin.com`
- ID estructurado: `RENO-1213-00001`

**Ejemplo de request:**

```json
POST /api/v1/auth/login
{
  "identifier": "RENO-1213-00001",  // Puede ser username, email o ID
  "password": "Ornelas2025!"
}
```

### Beneficios del ID Estructurado

1. **Privacidad:** No revela información sensible
2. **Memorable:** Más fácil que un UUID
3. **Rastreable:** Útil para auditoría
4. **NOM-024 Compliant:** Cumple requisitos normativos

---

## 🔍 Testing

### Casos de Prueba

1. **Crear usuario con campos válidos**
   - ✅ Debe generar codigo_interno
   - ✅ Debe retornar codigo_interno en response

2. **Crear usuario con nombres especiales**
   - Acentos: "José María Pérez"
   - Artículos: "de la Cruz"
   - Caracteres especiales: "O'Brien"
   - ✅ Debe normalizar y generar ID válido

3. **Crear múltiples usuarios en el mismo día**
   - ✅ Contador debe incrementar
   - ✅ No debe haber duplicados

4. **Crear usuario con BD desconectada temporalmente**
   - ✅ Debe crear usuario sin codigo_interno
   - ✅ Debe registrar error en logs
   - ✅ No debe lanzar excepción 500

### Script de Prueba

```bash
# Ejecutar tests unitarios
cd backend
python tests/test_id_generator.py

# Probar endpoint con curl
curl -X POST http://localhost:8000/api/v1/usuarios \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "nombre_usuario": "test_user",
    "password": "Test123!",
    "email": "test@example.com",
    "rol": "Podologo",
    "nombre_completo": "Juan",
    "apellido_completo": "Pérez"
  }'
```

---

## 📞 Soporte

### Preguntas Frecuentes

**Q: ¿Puedo crear usuarios sin codigo_interno?**  
A: Sí, si falla la generación, el usuario se crea sin ID. Puede hacer login con username/email.

**Q: ¿Qué pasa si un paciente no tiene codigo_interno?**  
A: El expediente funciona normalmente. El ID estructurado es opcional.

**Q: ¿Puedo cambiar el codigo_interno después?**  
A: No implementado aún. Una vez generado, es permanente.

**Q: ¿Los IDs son únicos entre usuarios y pacientes?**  
A: No necesariamente. Son únicos dentro de cada tabla (usuarios o pacientes).

---

**Última actualización:** 13 de diciembre de 2024  
**Responsable:** GitHub Copilot Agent  
**Contacto:** Ver documentación técnica en VERIFICACION_BACKEND_NOM024.md
