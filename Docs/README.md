# 📚 Índice de Documentación - Proyecto PodoSkin

**Última actualización:** 8 de Diciembre, 2025  
**Estado del proyecto:** ✅ Operativo en Desarrollo

---

## 🎯 Documentos por Audiencia

### Para el Cliente (Prof. Santiago)

| Documento | Descripción | Ubicación |
|-----------|-------------|-----------|
| **Informe: Nueva Estructura de BD** | Explica los 3 archiveros (BDs) y beneficios | `Informes/PodoSkin_Informe_Nueva_BD.md` |
| **Informe: Modelos de Datos** | Qué información guarda cada tabla | `Informes/PodoSkin_Informe_Modelos_Datos.md` |
| **Propuesta: Permisos de API** | Qué puede hacer cada rol (Admin/Podologo/Recepcion) | `Informes/PodoSkin_Propuesta_Permisos_API.md` |

### Para el Equipo de Desarrollo

| Documento | Descripción | Ubicación |
|-----------|-------------|-----------|
| **Plan: Arquitectura de BD** | Diseño de las 3 bases de datos | `Planeamiento/PodoSkin_Plan_Arquitectura_BD.md` |
| **Plan: Modelos SQLAlchemy** | Cómo mapear tablas PostgreSQL a Python | `Planeamiento/PodoSkin_Plan_Modelos_SQLAlchemy.md` |
| **Plan: Permisos de Endpoints** | Matriz rol × endpoint × acción | `Planeamiento/API_Permisos_Endpoints.md` |
| **Desarrollo: BD v4** | Implementación técnica de la BD | `Desarrollo/PodoSkin_Desarrollo_BD_v4.md` |
| **Desarrollo: Modelos SQLAlchemy** | Código SQLAlchemy final | `Desarrollo/PodoSkin_Desarrollo_Modelos_SQLAlchemy.md` |
| **Especificación Funcional** | Requisitos completos del sistema | `Informes/Especificacion_Funcional_BD.md` |

### Post-Mortem y Aprendizaje

| Documento | Descripción | Ubicación |
|-----------|-------------|-----------|
| **Lecciones Aprendidas** | Errores cometidos y cómo evitarlos | `Lecciones_Aprendidas.md` |

---

## 🗂️ Estructura de Carpetas

```
Docs/
├── Planeamiento/          ← Lo que planeamos hacer
│   ├── PodoSkin_Plan_Arquitectura_BD.md
│   ├── PodoSkin_Plan_Modelos_SQLAlchemy.md
│   └── API_Permisos_Endpoints.md
│
├── Desarrollo/            ← Cómo lo implementamos
│   ├── PodoSkin_Desarrollo_BD_v4.md
│   └── PodoSkin_Desarrollo_Modelos_SQLAlchemy.md
│
├── Informes/              ← Documentos para el cliente
│   ├── PodoSkin_Informe_Nueva_BD.md
│   ├── PodoSkin_Informe_Modelos_Datos.md
│   ├── PodoSkin_Propuesta_Permisos_API.md
│   └── Especificacion_Funcional_BD.md
│
└── Lecciones_Aprendidas.md ← Post-mortem del proyecto
```

---

## 🔑 Información de Acceso Actualizada

### Credenciales del Sistema

| Servicio | Usuario | Contraseña | Notas |
|----------|---------|------------|-------|
| **Admin Web** | `admin` | `Admin2405` | Cambiar en primer login |
| **PostgreSQL** | `podoskin` | `podoskin123` | Solo desde localhost |
| **Docker DB** | `podoskin` | `podoskin123` | Puerto 5432 |

### URLs del Sistema

| Servicio | URL | Notas |
|----------|-----|-------|
| **API Backend** | `http://localhost:8000` | FastAPI |
| **Swagger Docs** | `http://localhost:8000/docs` | Documentación interactiva |
| **ReDoc** | `http://localhost:8000/redoc` | Documentación alternativa |
| **PostgreSQL** | `localhost:5432` | 3 BDs: auth, core, ops |

---

## 🚀 Estado Actual del Proyecto

### ✅ Completado

- [x] 3 Bases de datos PostgreSQL separadas
- [x] 58+ endpoints REST API
- [x] Autenticación JWT con JSON
- [x] Auditoría completa (INSERT, UPDATE, DELETE, LOGIN_EXITOSO, etc.)
- [x] RBAC con 3 roles (Admin, Podologo, Recepcion)
- [x] Soft deletes en tablas sensibles
- [x] Versionado de API (`/api/v1`)
- [x] Documentación Swagger autogenerada
- [x] Tests unitarios básicos

### 🔄 En Progreso

- [ ] Tests de integración completos
- [ ] Migraciones con Alembic
- [ ] CI/CD pipeline
- [ ] Frontend (React/Vue)

### 📋 Backlog

- [ ] Monitoreo con Prometheus
- [ ] Logging estructurado
- [ ] Deploy a producción
- [ ] Backups automáticos
- [ ] Multi-tenancy completo

---

## 📖 Guía Rápida de Lectura

### Si eres el cliente (Prof. Santiago):
1. Lee `Informes/PodoSkin_Informe_Nueva_BD.md` primero
2. Luego revisa `Informes/PodoSkin_Propuesta_Permisos_API.md`
3. Si necesitas detalles técnicos, consulta `Informes/Especificacion_Funcional_BD.md`

### Si eres desarrollador nuevo:
1. Lee `.github/copilot-instructions.md` (contexto general)
2. Revisa `Planeamiento/PodoSkin_Plan_Arquitectura_BD.md`
3. Estudia `Desarrollo/PodoSkin_Desarrollo_Modelos_SQLAlchemy.md`
4. Lee `Lecciones_Aprendidas.md` para evitar errores pasados

### Si vas a hacer cambios a la BD:
1. Consulta `Desarrollo/PodoSkin_Desarrollo_BD_v4.md`
2. Actualiza los scripts en `data/sql/`
3. Documenta el cambio en `Lecciones_Aprendidas.md` si es relevante

---

## 🔧 Mantenimiento de Documentación

### Reglas para mantener docs actualizados:

1. **Cada cambio de arquitectura** → Actualizar `Planeamiento/` y `Desarrollo/`
2. **Cada endpoint nuevo** → Actualizar `API_Permisos_Endpoints.md`
3. **Cada error crítico** → Agregar a `Lecciones_Aprendidas.md`
4. **Cada cambio de credenciales** → Actualizar este índice

### Formato de documentos:

- **Para cliente:** Lenguaje simple, diagramas visuales, sin tecnicismos
- **Para desarrolladores:** Código, SQL, diagramas técnicos, referencias
- **Lecciones aprendidas:** Formato: Error → Impacto → Lección → Checklist

---

## 📞 Contacto

| Rol | Nombre | Email | Teléfono |
|-----|--------|-------|----------|
| **Cliente** | Prof. Santiago Ornelas | - | - |
| **Desarrollador** | Abraham Córdova | abraham.cordova.0405@gmail.com | 686 226 23-77 |

---

## 📋 Información Legal y Propiedad Intelectual

### Propiedad del Software

Este sistema **PodoSkin** es propiedad exclusiva de:

**Cognita.I.A.**  
Desarrollador: Abraham Córdova  
Contacto: abraham.cordova.0405@gmail.com  
Teléfono: 686 226 23-77

### Modelo de Licencia

El sistema PodoSkin ha sido desarrollado como **software especializado bajo contrato** para uso exclusivo de:

**Cliente:** Prof. Santiago de Jesús Ornelas Reynoso  
**Clínica:** Clínica PodoSkin

#### Términos de Uso

- **Licencia:** Renta mensual con desarrollo especializado
- **Alcance:** Uso exclusivo para la clínica del cliente contratante
- **Propiedad del código:** Cognita.I.A. mantiene todos los derechos de propiedad intelectual
- **Personalización:** El sistema está diseñado específicamente para las necesidades de Clínica PodoSkin
- **Soporte:** Incluido bajo contrato de renta mensual
- **Actualizaciones:** Incluidas según términos contractuales

> ⚠️ **IMPORTANTE:** Este software no puede ser redistribuido, copiado, modificado o utilizado por terceros sin autorización expresa y por escrito de Cognita.I.A.

---

<div align="center">

**Documentación Técnica - Proyecto PodoSkin**  
*Sistema de Gestión Clínica Podológica*

**Desarrollado por:** Cognita.I.A.  
**Contacto:** abraham.cordova.0405@gmail.com

© 2025 Cognita.I.A. - Todos los derechos reservados  
Última revisión: 8 de Diciembre, 2025

</div>
