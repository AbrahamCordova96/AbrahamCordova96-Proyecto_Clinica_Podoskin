# 🎨 PROMPT PARA AGENTE FRONTEND - Adaptación NOM-024

## 📋 CONTEXTO

El backend ya implementó campos adicionales para cumplir con NOM-024 (norma mexicana de expediente clínico electrónico). Tu trabajo es **INTEGRAR estos campos en la UI existente** sin crear formularios nuevos desde cero.

**IMPORTANTE:** Somos una clínica podológica pequeña, NO un hospital. Los campos NOM-024 son **OPCIONALES** por ahora, pero deben estar disponibles para cuando los necesitemos.

---

## 🎯 TU MISIÓN

Agregar campos NOM-024 en formularios existentes de forma **NO INTRUSIVA**:
- Campos opcionales (no obligatorios)
- Integrados en secciones existentes
- UI limpia, no sobrecargada
- No romper funcionalidad actual

---

## 📦 CAMBIOS EN BACKEND (Ya implementados)

### **1. Pacientes - Nuevos Campos Opcionales**
```json
{
  "curp": "string(18)",           // Opcional
  "estado_nacimiento": "string",  // Opcional - Catálogo INEGI
  "nacionalidad": "string(3)",    // Opcional - MEX default
  "estado_residencia": "string",  // Opcional
  "municipio_residencia": "string", // Opcional
  "localidad_residencia": "string"  // Opcional
}
```

### **2. Podólogos - Datos Profesionales**
```json
{
  "cedula_profesional": "string",     // Campo en configuración
  "especialidad": "string",           // Campo en configuración
  "institucion_emisora": "string"     // Campo en configuración
}
```

### **3. Evoluciones - Catálogos CIE-10**
```json
{
  "diagnostico_codigo_cie10": "string",  // Opcional - Autocompletado
  "procedimiento_codigo": "string"       // Opcional - Autocompletado
}
```

### **4. Audit Log (automático en backend)**
No requiere UI, pero puedes agregar vista de "Historial de Cambios" en expediente.

---

## 🛠️ TAREAS ESPECÍFICAS

### **TAREA 1: Formulario de Registro de Pacientes**

**Ubicación:** Busca el componente de registro/edición de pacientes

**Acción:**
1. Encuentra la sección de "Datos Personales" o similar
2. Agrega estos campos **AL FINAL** de esa sección (no al inicio):

```jsx
// Sección adicional colapsable (acordeón)
<AccordionItem title="Datos Adicionales (Opcional)">
  
  <InputField 
    label="CURP" 
    name="curp"
    placeholder="AAAA######HDFXXX##"
    maxLength={18}
    pattern="[A-Z]{4}[0-9]{6}[HM][A-Z]{5}[0-9]{2}"
    helperText="18 caracteres - Opcional"
    optional
  />

  <SelectField
    label="Estado de Nacimiento"
    name="estado_nacimiento"
    options={[/* Catálogo INEGI - ver backend/data/catalogos */]}
    optional
  />

  <InputField
    label="Nacionalidad"
    name="nacionalidad"
    defaultValue="MEX"
    maxLength={3}
    optional
  />

  {/* Residencia */}
  <SelectField label="Estado de Residencia" name="estado_residencia" optional />
  <SelectField label="Municipio" name="municipio_residencia" optional />
  <InputField label="Localidad" name="localidad_residencia" optional />

</AccordionItem>
```

**Validaciones:**
- CURP: Validar formato solo si el usuario lo llena
- No hacer campos obligatorios
- Si CURP inválido, mostrar warning (no error que bloquee)

---

### **TAREA 2: Configuración de Podólogos**

**Ubicación:** Busca el área de "Configuración de Usuario" o "Mi Perfil" para podólogos

**Acción:**
1. Encuentra la sección de datos del profesional
2. Agrega subsección "Datos Profesionales":

```jsx
<FormSection title="Datos Profesionales">
  
  <InputField
    label="Cédula Profesional"
    name="cedula_profesional"
    placeholder="1234567"
    helperText="Número de cédula profesional"
  />

  <InputField
    label="Especialidad"
    name="especialidad"
    placeholder="Ej: Podología Clínica"
  />

  <InputField
    label="Institución que otorgó el título"
    name="institucion_emisora"
    placeholder="Ej: UNAM"
  />

</FormSection>
```

**Comportamiento:**
- Estos datos se guardan UNA VEZ y aparecen automáticamente en expedientes
- No pedir en cada consulta

---

### **TAREA 3: Formulario de Evoluciones/Notas Clínicas**

**Ubicación:** Busca donde se registran las notas SOAP o evoluciones

**Acción:**
1. En la sección de "Diagnóstico" o "Evaluación":

```jsx
<FormSection title="Diagnóstico">
  
  {/* Campo de texto libre existente */}
  <TextArea
    label="Diagnóstico"
    name="diagnostico"
    rows={3}
  />

  {/* NUEVO: Código CIE-10 opcional */}
  <AutocompleteField
    label="Código CIE-10 (Opcional)"
    name="diagnostico_codigo_cie10"
    placeholder="Buscar código..."
    endpoint="/api/v1/catalogos/cie10"
    renderOption={(option) => `${option.codigo} - ${option.descripcion}`}
    helperText="Opcional - Para reportes estadísticos"
    optional
  />

</FormSection>

<FormSection title="Procedimiento Realizado">
  
  <TextArea
    label="Procedimiento"
    name="procedimiento"
    rows={3}
  />

  {/* NUEVO: Código de procedimiento opcional */}
  <AutocompleteField
    label="Código de Procedimiento (Opcional)"
    name="procedimiento_codigo"
    endpoint="/api/v1/catalogos/procedimientos"
    optional
  />

</FormSection>
```

**Endpoints que debes usar:**
- `GET /api/v1/catalogos/cie10?search={query}` - Buscar diagnósticos CIE-10
- `GET /api/v1/catalogos/procedimientos?search={query}` - Buscar procedimientos

---

### **TAREA 4: Botón "Imprimir Expediente"**

**Ubicación:** Vista de expediente completo del paciente

**Acción:**
1. Agrega botón en la barra de acciones del expediente:

```jsx
<ButtonGroup>
  {/* Botones existentes */}
  
  {/* NUEVO */}
  <Button
    icon={<PrintIcon />}
    onClick={handlePrintExpediente}
    variant="secondary"
  >
    Imprimir Expediente
  </Button>
</ButtonGroup>
```

**Funcionalidad:**
```jsx
const handlePrintExpediente = async () => {
  try {
    const response = await fetch(
      `/api/v1/reportes/expediente/${pacienteId}/html`,
      {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
      }
    );
    
    const html = await response.text();
    
    // Opción 1: Abrir en nueva ventana para imprimir
    const printWindow = window.open('', '_blank');
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.print();
    
    // Opción 2: Descargar PDF
    // const blob = await response.blob();
    // downloadFile(blob, `expediente_${pacienteId}.pdf`);
    
  } catch (error) {
    showNotification('Error al generar expediente', 'error');
  }
};
```

**Endpoint backend:**
- `GET /api/v1/reportes/expediente/{paciente_id}/html` - Retorna HTML formateado
- `GET /api/v1/reportes/expediente/{paciente_id}/pdf` - Retorna PDF (futuro)

---

### **TAREA 5 (OPCIONAL): Vista de Auditoría**

**Ubicación:** Vista de expediente del paciente

**Acción:**
1. Agrega pestaña o sección "Historial de Cambios":

```jsx
<TabPanel value="historial">
  <AuditLogViewer pacienteId={pacienteId} />
</TabPanel>
```

**Componente:**
```jsx
const AuditLogViewer = ({ pacienteId }) => {
  const [logs, setLogs] = useState([]);
  
  useEffect(() => {
    fetch(`/api/v1/audit/paciente/${pacienteId}`)
      .then(res => res.json())
      .then(data => setLogs(data));
  }, [pacienteId]);
  
  return (
    <Timeline>
      {logs.map(log => (
        <TimelineItem key={log.id}>
          <TimelineDate>{formatDate(log.timestamp)}</TimelineDate>
          <TimelineContent>
            <strong>{log.usuario}</strong> {log.accion}
            <br />
            <small>{log.tabla_afectada}</small>
          </TimelineContent>
        </TimelineItem>
      ))}
    </Timeline>
  );
};
```

---

## 🚫 LO QUE NO DEBES HACER

❌ **NO hagas campos obligatorios** (todos opcionales)  
❌ **NO crees formularios desde cero** (integra en existentes)  
❌ **NO rompas funcionalidad actual** (todo debe seguir funcionando sin llenar nuevos campos)  
❌ **NO agregues validaciones estrictas** (solo formato si el usuario llena)  
❌ **NO implementes firma electrónica** (no es necesario ahorita)  
❌ **NO te preocupes por certificación** (eso es del backend)  

---

## ✅ LO QUE SÍ DEBES HACER

✅ Integrar campos de forma **no intrusiva**  
✅ Usar **componentes existentes** del sistema  
✅ Hacer todo **opcional** y progresivo  
✅ Mantener **UI limpia** (acordeones, pestañas)  
✅ Agregar **tooltips/ayudas** explicando para qué sirven los campos  
✅ Probar que funciona **con y sin** llenar campos nuevos  

---

## 📚 RECURSOS

### **Catálogos en Backend:**
- `backend/data/catalogos/estados_mexico.json` - Estados INEGI
- `backend/data/catalogos/municipios.json` - Municipios
- `backend/schemas/ops/catalogos.py` - Modelos de catálogos

### **Endpoints Importantes:**
```
GET  /api/v1/catalogos/cie10?search={query}
GET  /api/v1/catalogos/procedimientos?search={query}
GET  /api/v1/catalogos/estados
GET  /api/v1/catalogos/municipios?estado={codigo}
GET  /api/v1/reportes/expediente/{id}/html
GET  /api/v1/audit/paciente/{id}
POST /api/v1/pacientes (acepta campos nuevos)
PUT  /api/v1/podologos/{id}/configuracion
```

### **Documentación de Referencia:**
- `INFORME_CUMPLIMIENTO_NOM024.md` - Contexto completo
- `PROMPT_IMPLEMENTACION_NOM024.md` - Cambios en backend

---

## 🎯 CRITERIOS DE ÉXITO

Tu implementación es exitosa si:

1. ✅ Formulario de pacientes tiene sección "Datos Adicionales" colapsable
2. ✅ Configuración de podólogos tiene campos profesionales
3. ✅ Evoluciones tienen autocompletado de CIE-10 (opcional)
4. ✅ Existe botón "Imprimir Expediente" funcional
5. ✅ Todo funciona igual que antes si NO llenas campos nuevos
6. ✅ UI no se ve sobrecargada
7. ✅ No hay errores de validación bloqueantes en campos opcionales

---

## 📝 REPORTE FINAL

Al terminar, crea archivo `REPORTE_FRONTEND_NOM024.md` con:

1. **Componentes modificados** (lista de archivos)
2. **Nuevos componentes creados** (si aplica)
3. **Endpoints consumidos** (lista)
4. **Screenshots** o descripción de cambios visuales
5. **Problemas encontrados** (si hay)
6. **Recomendaciones** para mejoras futuras

---

## ⚠️ NOTAS IMPORTANTES

- **No te sobre-compliques:** Si algo no existe (ej: acordeones), usa lo que tengas disponible
- **Prioriza funcionalidad:** Mejor funcional y simple que bonito pero roto
- **Pregunta si tienes dudas:** Mejor preguntar que asumir
- **No implementes todo de golpe:** Hazlo por tareas (1, 2, 3, 4, 5)

---

**Última actualización:** 13 de diciembre de 2024  
**Versión:** 1.0  
**Autor:** Sistema PodoSkin
