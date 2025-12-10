# API PodoSkin - Matriz de Permisos por Endpoint

**Fecha Actualización:** 9 de Diciembre, 2025  
**Estado:** 95 endpoints implementados | 89 funcionales (93.7%)

---

## Roles del Sistema

| Rol | Código | Usuarios |
|-----|--------|----------|
| Administrador | `Admin` | admin (usuario seed) |
| Podólogo | `Podologo` | (en producción) |
| Recepción | `Recepcion` | (futuro) |

---

## Leyenda

- ✅ = Permitido
- ❌ = Denegado
- 🔒 = Requiere ser dueño del recurso (created_by = user_id)
- ⚠️ = Permitido con restricciones

---

## 1. Autenticación (`/auth`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/auth/login` | POST | ✅ | ✅ | ✅ | Login (público) |
| `/auth/logout` | POST | ✅ | ✅ | ✅ | Cerrar sesión |
| `/auth/me` | GET | ✅ | ✅ | ✅ | Ver mi perfil |
| `/auth/change-password` | PUT | ✅ | ✅ | ✅ | Cambiar mi contraseña |

---

## 2. Usuarios del Sistema (`/usuarios`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/usuarios` | GET | ✅ | ✅ | ❌ | Listar usuarios |
| `/usuarios/{id}` | GET | ✅ | ⚠️ self | ❌ | Ver detalle usuario |
| `/usuarios` | POST | ✅ | ❌ | ❌ | Crear usuario |
| `/usuarios/{id}` | PUT | ✅ | ⚠️ self | ❌ | Editar usuario |
| `/usuarios/{id}` | DELETE | ✅ | ❌ | ❌ | Eliminar usuario |

---

## 3. Podólogos (`/podologos`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/podologos` | GET | ✅ | ✅ | ✅ | Listar podólogos activos |
| `/podologos/{id}` | GET | ✅ | ✅ | ✅ | Ver detalle podólogo |
| `/podologos` | POST | ✅ | ❌ | ❌ | Crear podólogo |
| `/podologos/{id}` | PUT | ✅ | ⚠️ self | ❌ | Editar podólogo |
| `/podologos/{id}` | DELETE | ✅ | ❌ | ❌ | Desactivar podólogo |

---

## 4. Pacientes (`/pacientes`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/pacientes` | GET | ✅ | ✅ | ✅ | Listar pacientes |
| `/pacientes/buscar` | GET | ✅ | ✅ | ✅ | Búsqueda fuzzy |
| `/pacientes/{id}` | GET | ✅ | ✅ | ⚠️ básico | Ver detalle paciente |
| `/pacientes` | POST | ✅ | ✅ | ✅ | Crear paciente |
| `/pacientes/{id}` | PUT | ✅ | ✅ | ⚠️ básico | Editar paciente |
| `/pacientes/{id}` | DELETE | ✅ | ✅ | ❌ | Soft delete paciente |
| `/pacientes/{id}/purge` | DELETE | ✅ | ❌ | ❌ | Hard delete (permanente) |

### Restricciones de Recepción en Pacientes

- `⚠️ básico` = Solo campos: nombres, apellidos, telefono, email, domicilio, fecha_nacimiento, sexo
- NO puede ver: historial médico, notas clínicas, diagnósticos

---

## 5. Historial Médico (`/pacientes/{id}/historial`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/pacientes/{id}/historial` | GET | ✅ | ✅ | ❌ | Ver historial general |
| `/pacientes/{id}/historial` | POST | ✅ | ✅ | ❌ | Crear historial |
| `/pacientes/{id}/historial` | PUT | ✅ | ✅ | ❌ | Actualizar historial |
| `/pacientes/{id}/historial-gineco` | GET | ✅ | ✅ | ❌ | Ver historial gineco |
| `/pacientes/{id}/historial-gineco` | POST | ✅ | ✅ | ❌ | Crear historial gineco |
| `/pacientes/{id}/historial-gineco` | PUT | ✅ | ✅ | ❌ | Actualizar historial gineco |

---

## 6. Citas (`/citas`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/citas` | GET | ✅ | ✅ | ✅ | Listar citas (con filtros) |
| `/citas/agenda/{fecha}` | GET | ✅ | ✅ | ✅ | Agenda del día |
| `/citas/disponibilidad` | GET | ✅ | ✅ | ✅ | Horarios disponibles |
| `/citas/{id}` | GET | ✅ | ✅ | ✅ | Ver detalle cita |
| `/citas` | POST | ✅ | ✅ | ✅ | Crear cita |
| `/citas/{id}` | PUT | ✅ | ✅ | ✅ | Editar cita |
| `/citas/{id}/status` | PATCH | ✅ | ✅ | ✅ | Cambiar status |
| `/citas/{id}` | DELETE | ✅ | ✅ | ✅ | Cancelar cita (soft) |

---

## 7. Tratamientos (`/tratamientos`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/tratamientos` | GET | ✅ | ✅ | ❌ | Listar tratamientos |
| `/pacientes/{id}/tratamientos` | GET | ✅ | ✅ | ❌ | Tratamientos de paciente |
| `/tratamientos/{id}` | GET | ✅ | ✅ | ❌ | Ver detalle tratamiento |
| `/tratamientos` | POST | ✅ | ✅ | ❌ | Crear tratamiento |
| `/tratamientos/{id}` | PUT | ✅ | ✅ | ❌ | Editar tratamiento |
| `/tratamientos/{id}/status` | PATCH | ✅ | ✅ | ❌ | Cambiar status |
| `/tratamientos/{id}` | DELETE | ✅ | ✅ | ❌ | Soft delete |

---

## 8. Evoluciones Clínicas (`/evoluciones`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/evoluciones` | GET | ✅ | ✅ | ❌ | Listar evoluciones |
| `/tratamientos/{id}/evoluciones` | GET | ✅ | ✅ | ❌ | Evoluciones de tratamiento |
| `/evoluciones/{id}` | GET | ✅ | ✅ | ❌ | Ver detalle evolución |
| `/evoluciones` | POST | ✅ | ✅ | ❌ | Crear evolución |
| `/evoluciones/{id}` | PUT | ✅ | ✅ | ❌ | Editar evolución |
| `/evoluciones/{id}` | DELETE | ✅ | ❌ | ❌ | Soft delete |

---

## 9. Evidencia Fotográfica (`/evidencias`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/evoluciones/{id}/evidencias` | GET | ✅ | ✅ | ❌ | Listar fotos |
| `/evidencias/{id}` | GET | ✅ | ✅ | ❌ | Ver foto |
| `/evidencias` | POST | ✅ | ✅ | ❌ | Subir foto |
| `/evidencias/{id}` | DELETE | ✅ | ✅ | ❌ | Eliminar foto |

---

## 10. Catálogo de Servicios (`/servicios`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/servicios` | GET | ✅ | ✅ | ✅ | Listar servicios |
| `/servicios/{id}` | GET | ✅ | ✅ | ✅ | Ver detalle servicio |
| `/servicios` | POST | ✅ | ✅ | ❌ | Crear servicio |
| `/servicios/{id}` | PUT | ✅ | ✅ | ❌ | Editar servicio |
| `/servicios/{id}` | DELETE | ✅ | ❌ | ❌ | Desactivar servicio |

---

## 11. Prospectos (`/prospectos`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/prospectos` | GET | ✅ | ✅ | ✅ | Listar prospectos |
| `/prospectos/{id}` | GET | ✅ | ✅ | ✅ | Ver detalle |
| `/prospectos` | POST | ✅ | ✅ | ✅ | Crear prospecto |
| `/prospectos/{id}` | PUT | ✅ | ✅ | ✅ | Editar prospecto |
| `/prospectos/{id}/convertir` | POST | ✅ | ✅ | ✅ | Convertir a paciente |

---

## 12. Auditoría (`/audit`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/audit` | GET | ✅ | ✅ | ❌ | Listar logs (con filtros) |
| `/audit/{tabla}/{id}` | GET | ✅ | ✅ | ❌ | Historial de un registro |
| `/audit/export` | GET | ✅ | ❌ | ❌ | Exportar logs |

---

## 13. Sistema (`/sistema`)

| Endpoint | Método | Admin | Podologo | Recepcion | Descripción |
|----------|--------|:-----:|:--------:|:---------:|-------------|
| `/sistema/config` | GET | ✅ | ❌ | ❌ | Ver configuración |
| `/sistema/config` | PUT | ✅ | ❌ | ❌ | Modificar configuración |
| `/sistema/backup` | POST | ✅ | ❌ | ❌ | Crear respaldo |
| `/sistema/stats` | GET | ✅ | ✅ | ❌ | Estadísticas dashboard |

---

## Middleware de Autorización

```python
# Ejemplo de implementación
PERMISOS = {
    "Admin": ["*"],  # Todo permitido
    "Podologo": [
        "pacientes:*",
        "citas:*",
        "tratamientos:*",
        "evoluciones:*",
        "evidencias:*",
        "servicios:read",
        "servicios:create",
        "servicios:update",
        "prospectos:*",
        "audit:read",
    ],
    "Recepcion": [
        "pacientes:read:basic",
        "pacientes:create",
        "pacientes:update:basic",
        "citas:*",
        "servicios:read",
        "prospectos:*",
    ]
}
```

---

## Próximos Pasos

1. [ ] Implementar middleware de autenticación JWT
2. [ ] Implementar middleware de autorización por rol
3. [ ] Crear decorador `@require_role(["Admin", "Podologo"])`
4. [ ] Implementar endpoints en orden de prioridad:
   - [ ] Auth
   - [ ] Pacientes
   - [ ] Citas
   - [ ] Tratamientos/Evoluciones
   - [ ] Catálogos
   - [ ] Auditoría
