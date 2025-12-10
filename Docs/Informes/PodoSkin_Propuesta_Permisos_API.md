# 🦶 Sistema PodoSkin

## Propuesta de Permisos y Estructura de Acceso

---

**Documento preparado para:** Profesional Santiago de Jesús Ornelas Reynoso  
**Fecha:** 6 de Diciembre, 2024  
**Versión:** 1.0

---

## 📋 Resumen Ejecutivo

Este documento presenta la estructura de permisos propuesta para el sistema digital de la clínica **PodoSkin**. El objetivo es definir **quién puede hacer qué** dentro del sistema, garantizando:

- ✅ **Seguridad** de la información de los pacientes
- ✅ **Flexibilidad** operativa para el día a día
- ✅ **Trazabilidad** de todas las acciones (quién hizo qué y cuándo)
- ✅ **Cumplimiento legal** de expedientes médicos

---

## 👥 Equipo PodoSkin

### Organigrama

```
┌─────────────────────────────────────────────────────────────┐
│                    🏥 CLÍNICA PODOSKIN                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│    ┌─────────────────────┐                                  │
│    │  👨‍⚕️ Profesional Santiago    │                                  │
│    │     Ornelas         │                                  │
│    │  ─────────────────  │                                  │
│    │  Dueño y Podólogo   │                                  │
│    │  Principal          │                                  │
│    │  Usuario: dr.ornelas│                                  │
│    └──────────┬──────────┘                                  │
│               │                                             │
│               │ Delega tareas                               │
│               ▼                                             │
│    ┌─────────────────────┐                                  │
│    │  👩‍⚕️ Ibeth Castillo  │                                  │
│    │     Mendoza         │                                  │
│    │  ─────────────────  │                                  │
│    │  Podóloga y         │                                  │
│    │  Secretaria         │                                  │
│    │  Usuario:           │                                  │
│    │  ibeth.castillo     │                                  │
│    └─────────────────────┘                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Tabla de Usuarios

| 👤 Nombre | 🎭 Rol en Sistema | 📧 Usuario | 🔑 Nivel |
|-----------|-------------------|------------|----------|
| Profesional Santiago de Jesús Ornelas Reynoso | **Administrador** | `dr.ornelas` | Máximo |
| Ibeth Castillo Mendoza | **Podóloga** | `ibeth.castillo` | Alto |

---

## 🔐 ¿Qué significa cada Rol?

### 🔴 Administrador (Profesional Santiago)

> El **dueño** del sistema. Tiene acceso completo a TODO, incluyendo configuración del sistema y la capacidad de eliminar información permanentemente.

**Características:**

- ✅ Control total del sistema
- ✅ Puede crear y eliminar usuarios
- ✅ Puede exportar toda la base de datos
- ✅ Puede eliminar registros permanentemente
- ✅ Acceso a configuración del sistema

---

### 🟢 Podóloga (Ibeth)

> **Mano derecha** del Profesional Santiago. Puede hacer prácticamente todo en el día a día: agendar, atender pacientes, escribir notas clínicas. Solo hay algunas funciones reservadas para el dueño.

**Características:**

- ✅ Atender pacientes completamente
- ✅ Agendar y manejar citas
- ✅ Escribir y editar notas clínicas
- ✅ Modificar catálogo y precios
- ❌ NO puede crear/eliminar usuarios
- ❌ NO puede eliminar datos permanentemente

---

## 📊 Distribución de Permisos

```
┌────────────────────────────────────────────────────────────────┐
│                   DISTRIBUCIÓN DE PERMISOS                     │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│   ████████████████████████████████████████████░░░░░░░░  85%   │
│   ▲                                                            │
│   │                                                            │
│   └── Permisos COMPARTIDOS (ambos pueden hacer)                │
│                                                                │
│   ░░░░░░░░  15%                                                │
│   ▲                                                            │
│   │                                                            │
│   └── Permisos EXCLUSIVOS del Profesional Santiago                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

**Conclusión:** El 85% de las funciones del sistema las pueden usar ambos. Solo el 15% está reservado para el administrador.

---

## 📁 Gestión de Pacientes

| Acción | 👨‍⚕️ Profesional Santiago | 👩‍⚕️ Ibeth |
|--------|:-----------------:|:----------:|
| Ver lista de pacientes | ✅ | ✅ |
| Crear nuevo paciente | ✅ | ✅ |
| Editar datos del paciente | ✅ | ✅ |
| Ver historial médico completo | ✅ | ✅ |
| Escribir notas clínicas | ✅ | ✅ |
| Desactivar paciente (archivar) | ✅ | ✅ |
| **Eliminar paciente permanentemente** | ✅ | ❌ |

> 💡 **Nota importante:**  
>
> - **"Desactivar"** = Archivar el expediente. Se puede recuperar después.  
> - **"Eliminar permanentemente"** = Borrar TODO sin posibilidad de recuperación.

---

## 📅 Gestión de Citas

| Acción | 👨‍⚕️ Profesional Santiago | 👩‍⚕️ Ibeth |
|--------|:-----------------:|:----------:|
| Ver agenda del día | ✅ | ✅ |
| Ver agenda de la semana/mes | ✅ | ✅ |
| Agendar cita nueva | ✅ | ✅ |
| Reagendar cita | ✅ | ✅ |
| Cancelar cita | ✅ | ✅ |
| Marcar como "Realizada" | ✅ | ✅ |
| Marcar como "No Asistió" | ✅ | ✅ |

> ✅ **Ambos tienen control total de la agenda** para máxima flexibilidad operativa.

---

## 📝 Historial Clínico y Tratamientos

| Acción | 👨‍⚕️ Profesional Santiago | 👩‍⚕️ Ibeth |
|--------|:-----------------:|:----------:|
| Crear nuevo tratamiento | ✅ | ✅ |
| Escribir evolución clínica | ✅ | ✅ |
| Editar notas propias | ✅ | ✅ |
| Editar notas del compañero | ✅ | ✅ |
| Subir fotografías clínicas | ✅ | ✅ |
| Ver evoluciones anteriores | ✅ | ✅ |
| Cerrar/dar de alta un tratamiento | ✅ | ✅ |

> 🤝 **Colaboración total:** Como trabajan en equipo y hay confianza mutua, ambos pueden editar cualquier nota clínica del sistema.

---

## ⚙️ Configuración del Sistema

| Acción | 👨‍⚕️ Profesional Santiago | 👩‍⚕️ Ibeth |
|--------|:-----------------:|:----------:|
| Ver catálogo de servicios | ✅ | ✅ |
| Modificar catálogo de servicios | ✅ | ✅ |
| Cambiar precios | ✅ | ✅ |
| **Crear nuevos usuarios** | ✅ | ❌ |
| **Eliminar usuarios** | ✅ | ❌ |
| Ver registro de auditoría | ✅ | ✅ |
| **Exportar datos completos** | ✅ | ❌ |
| **Configuración del sistema** | ✅ | ❌ |

---

## 🔒 Funciones EXCLUSIVAS del Administrador

Estas son las **únicas 4 acciones** que Ibeth **NO puede** realizar:

```
┌─────────────────────────────────────────────────────────────┐
│           🔒 SOLO Profesional SANTIAGO PUEDE HACER                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  1. 👤 CREAR/ELIMINAR USUARIOS                      │   │
│   │     Solo el dueño decide quién tiene acceso         │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  2. 🗑️ ELIMINAR DATOS PERMANENTEMENTE               │   │
│   │     Protección legal de expedientes                 │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  3. 💾 EXPORTAR BASE DE DATOS COMPLETA              │   │
│   │     Información sensible de todos los pacientes     │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
│   ┌─────────────────────────────────────────────────────┐   │
│   │  4. ⚙️ CONFIGURACIÓN DEL SISTEMA                    │   │
│   │     Cambios técnicos del funcionamiento             │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### ¿Por qué estas restricciones?

| # | Función Restringida | Motivo |
|---|---------------------|--------|
| 1 | Crear/Eliminar usuarios | Solo el dueño decide quién tiene acceso al sistema |
| 2 | Eliminar datos permanentemente | Protección legal - los expedientes médicos deben conservarse por ley |
| 3 | Exportar base de datos | Información sensible que solo el dueño debe poder extraer |
| 4 | Configuración del sistema | Cambios técnicos que podrían afectar todo el funcionamiento |

---

## 🛡️ Sistema de Auditoría

**Todo queda registrado automáticamente.** Cada vez que alguien hace algo en el sistema, se guarda un registro.

### ¿Qué se registra?

```
┌────────────────────────────────────────────────────────────┐
│                  SISTEMA DE AUDITORÍA                      │
├────────────────────────────────────────────────────────────┤
│                                                            │
│   🖱️ Acción realizada                                      │
│          │                                                 │
│          ▼                                                 │
│   📋 Se registra automáticamente:                          │
│          │                                                 │
│          ├──► 👤 QUIÉN lo hizo (usuario)                   │
│          │                                                 │
│          ├──► 📅 CUÁNDO (fecha y hora exacta)              │
│          │                                                 │
│          ├──► 🔄 QUÉ CAMBIÓ (antes y después)              │
│          │                                                 │
│          └──► 📍 DESDE DÓNDE (dirección IP)                │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Ejemplo de registro de auditoría

| Campo | Valor de Ejemplo |
|-------|------------------|
| **Usuario** | ibeth.castillo |
| **Fecha/Hora** | 6/Dic/2024 a las 10:35 AM |
| **Acción** | Modificó evolución clínica |
| **Paciente afectado** | María García López (ID: 45) |
| **Cambio realizado** | Agregó nota: "Paciente presenta mejoría..." |
| **Valor anterior** | "Paciente en observación" |
| **Valor nuevo** | "Paciente presenta mejoría en uña del pie derecho" |

> 📜 **Requisito Legal:**  
> En México, los expedientes clínicos deben conservarse por **mínimo 5 años**.  
> Este sistema de auditoría garantiza el cumplimiento de la NOM-004-SSA3-2012.

---

## 🔄 Flujo de Trabajo Típico

Este es el proceso normal de atención a un paciente:

```
┌─────────────────────────────────────────────────────────────────┐
│                    FLUJO DE ATENCIÓN                            │
└─────────────────────────────────────────────────────────────────┘

 📞 RECEPCIÓN (Santiago o Ibeth)
 ─────────────────────────────────
    │
    ├─► 1. Paciente llama o llega
    │
    ├─► 2. Buscar paciente existente
    │      o crear nuevo registro
    │
    └─► 3. Agendar cita
              │
              ▼
 🩺 CONSULTA (Santiago o Ibeth)
 ─────────────────────────────────
    │
    ├─► 4. Llamar paciente a consultorio
    │
    ├─► 5. Realizar exploración
    │
    ├─► 6. Escribir evolución clínica
    │
    ├─► 7. Tomar fotos (si aplica)
    │
    └─► 8. Agendar siguiente cita
              │
              ▼
 ✅ CIERRE
 ─────────────────────────────────
    │
    ├─► 9. Cobro del servicio
    │
    └─► 10. Despedir al paciente
```

> 💡 **Nota:** Tanto Santiago como Ibeth pueden realizar **CUALQUIER** paso de este flujo.

---

## 🚀 Escalabilidad Futura

Si en el futuro contrata más personal, el sistema ya está preparado:

### Configuración Actual (2 personas)

```
┌──────────────────────────────────────┐
│         EQUIPO ACTUAL                │
├──────────────────────────────────────┤
│                                      │
│   👨‍⚕️ Profesional Santiago ──► Administrador  │
│                                      │
│   👩‍⚕️ Ibeth ──────────► Podóloga      │
│                                      │
└──────────────────────────────────────┘
```

### Si crece el equipo

```
┌──────────────────────────────────────┐
│         EQUIPO EXPANDIDO             │
├──────────────────────────────────────┤
│                                      │
│   👨‍⚕️ Profesional Santiago ──► Administrador  │
│                                      │
│   👩‍⚕️ Ibeth ──────────► Podóloga      │
│                                      │
│   👩 Nueva persona ──► Recepción     │
│      (solo agenda)                   │
│                                      │
│   👨‍⚕️ Nuevo doctor ───► Podólogo     │
│      (solo clínica)                  │
│                                      │
└──────────────────────────────────────┘
```

### Rol "Recepción" (disponible para futuro uso)

Si contratan a alguien **solo para recepción** (que NO sea podólogo), tendría permisos limitados:

| ✅ Puede hacer | ❌ No puede hacer |
|----------------|-------------------|
| Ver datos de contacto de pacientes | Ver historial médico |
| Agendar y cancelar citas | Escribir notas clínicas |
| Registrar nuevos pacientes | Ver diagnósticos |
| Atender llamadas telefónicas | Modificar tratamientos |
| Ver agenda del día | Subir fotografías clínicas |

---

## 📋 Resumen de Permisos por Rol

### Tabla Completa

| Recurso / Acción | 🔴 Admin | 🟢 Podólogo | 🟡 Recepción* |
|------------------|:--------:|:-----------:|:-------------:|
| **PACIENTES** |
| Ver lista de pacientes | ✅ | ✅ | ✅ |
| Crear paciente | ✅ | ✅ | ✅ |
| Editar datos básicos | ✅ | ✅ | ✅ |
| Ver historial médico | ✅ | ✅ | ❌ |
| Editar historial médico | ✅ | ✅ | ❌ |
| Desactivar (archivar) | ✅ | ✅ | ❌ |
| Eliminar permanentemente | ✅ | ❌ | ❌ |
| **CITAS** |
| Ver agenda | ✅ | ✅ | ✅ |
| Agendar cita | ✅ | ✅ | ✅ |
| Cancelar/reagendar | ✅ | ✅ | ✅ |
| Marcar status | ✅ | ✅ | ✅ |
| **CLÍNICO** |
| Crear tratamiento | ✅ | ✅ | ❌ |
| Escribir evolución | ✅ | ✅ | ❌ |
| Editar evoluciones | ✅ | ✅ | ❌ |
| Subir fotografías | ✅ | ✅ | ❌ |
| **CONFIGURACIÓN** |
| Modificar catálogo | ✅ | ✅ | ❌ |
| Cambiar precios | ✅ | ✅ | ❌ |
| Crear usuarios | ✅ | ❌ | ❌ |
| Eliminar usuarios | ✅ | ❌ | ❌ |
| Ver auditoría | ✅ | ✅ | ❌ |
| Exportar datos | ✅ | ❌ | ❌ |
| Configuración sistema | ✅ | ❌ | ❌ |

*Rol en reserva para futuras contrataciones

---

## ✅ Aprobación del Cliente

Por favor confirmar si está de acuerdo con cada punto:

| # | Punto a Aprobar | Aprobado |
|---|-----------------|:--------:|
| 1 | Ibeth puede hacer todo excepto: crear usuarios, eliminar permanentemente, exportar datos y configurar sistema | ⬜ |
| 2 | Todas las acciones quedan registradas en auditoría automática | ⬜ |
| 3 | Ambos pueden editar notas clínicas del otro (trabajo colaborativo) | ⬜ |
| 4 | Solo Profesional Santiago puede exportar la base de datos completa | ⬜ |
| 5 | El sistema está preparado para contratar más personal en el futuro | ⬜ |

---

## 📞 Información de Contacto

| Campo | Información |
|-------|-------------|
| **Desarrollador** | Abraham Córdova |
| **Email** | abraham.cordova.0405@gmail.com |
| **Teléfono** | 686 226 23-77 |
| **Fecha de documento** | 6 de Diciembre, 2025 |

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

---

**Documento generado para Clínica PodoSkin**  
*Sistema de Gestión Clínica Podológica*

**Desarrollado por:** Cognita.I.A.  
**Contacto:** abraham.cordova.0405@gmail.com

© 2025 Cognita.I.A. - Todos los derechos reservados

---

</div>
