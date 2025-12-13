// Componente para generar e imprimir expedientes médicos NOM-024
import { Paciente } from '../types/pacientes.types'

interface ExpedienteImpresionProps {
  paciente: Paciente
  tratamientos: any[]
  evoluciones: any[]
  podologos: any[]
}

/**
 * Genera el HTML completo para impresión de expediente médico
 * Cumple con requisitos NOM-024
 */
export function generarExpedienteHTML({
  paciente,
  tratamientos,
  evoluciones,
  podologos
}: ExpedienteImpresionProps): string {
  
  const calcularEdad = (fechaNacimiento: string) => {
    const hoy = new Date()
    const nacimiento = new Date(fechaNacimiento)
    let edad = hoy.getFullYear() - nacimiento.getFullYear()
    const mes = hoy.getMonth() - nacimiento.getMonth()
    if (mes < 0 || (mes === 0 && hoy.getDate() < nacimiento.getDate())) {
      edad--
    }
    return edad
  }

  const formatearFecha = (fecha: string) => {
    return new Date(fecha).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const formatearFechaCorta = (fecha: string) => {
    return new Date(fecha).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    })
  }

  const getPodologoNombre = (podologoId: number) => {
    const podo = podologos.find(p => p.id_podologo === podologoId)
    return podo ? `${podo.nombres} ${podo.apellidos}` : 'N/A'
  }

  return `
<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="UTF-8">
  <title>Expediente Clínico - ${paciente.nombres} ${paciente.apellidos}</title>
  <style>
    @page {
      size: letter;
      margin: 2cm;
    }

    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: 'Arial', sans-serif;
      font-size: 11pt;
      line-height: 1.4;
      color: #333;
    }

    .header {
      border-bottom: 3px solid #2563eb;
      padding-bottom: 15px;
      margin-bottom: 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .header-left h1 {
      font-size: 20pt;
      color: #2563eb;
      margin-bottom: 5px;
    }

    .header-left p {
      color: #666;
      font-size: 10pt;
    }

    .header-right {
      text-align: right;
    }

    .header-right .fecha-impresion {
      font-size: 9pt;
      color: #666;
    }

    .seccion {
      margin-bottom: 25px;
      page-break-inside: avoid;
    }

    .seccion-titulo {
      background-color: #f3f4f6;
      padding: 8px 12px;
      font-size: 13pt;
      font-weight: bold;
      color: #1f2937;
      border-left: 4px solid #2563eb;
      margin-bottom: 15px;
    }

    .info-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px 30px;
      margin-bottom: 15px;
    }

    .info-item {
      display: flex;
      padding: 6px 0;
      border-bottom: 1px solid #e5e7eb;
    }

    .info-label {
      font-weight: bold;
      color: #4b5563;
      min-width: 140px;
    }

    .info-valor {
      color: #1f2937;
      flex: 1;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      margin: 15px 0;
      font-size: 10pt;
    }

    thead {
      background-color: #f9fafb;
    }

    th {
      padding: 10px 8px;
      text-align: left;
      font-weight: bold;
      color: #374151;
      border-bottom: 2px solid #d1d5db;
    }

    td {
      padding: 8px;
      border-bottom: 1px solid #e5e7eb;
    }

    .tratamiento-box {
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 15px;
      margin-bottom: 15px;
      background-color: #fafafa;
      page-break-inside: avoid;
    }

    .tratamiento-header {
      font-weight: bold;
      font-size: 11pt;
      color: #1f2937;
      margin-bottom: 10px;
      padding-bottom: 8px;
      border-bottom: 1px solid #d1d5db;
    }

    .evolucion {
      background-color: white;
      border-left: 3px solid #10b981;
      padding: 10px;
      margin: 10px 0;
      font-size: 10pt;
    }

    .evolucion-fecha {
      font-weight: bold;
      color: #059669;
      margin-bottom: 5px;
    }

    .evolucion-podologo {
      color: #6b7280;
      font-size: 9pt;
      margin-bottom: 8px;
    }

    .firma-box {
      margin-top: 60px;
      border-top: 2px solid #333;
      padding-top: 10px;
      text-align: center;
      page-break-inside: avoid;
    }

    .firma-linea {
      width: 300px;
      margin: 40px auto 10px;
      border-top: 1px solid #333;
    }

    .footer {
      margin-top: 40px;
      padding-top: 15px;
      border-top: 1px solid #d1d5db;
      font-size: 8pt;
      color: #6b7280;
      text-align: center;
    }

    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 9pt;
      font-weight: 600;
    }

    .badge-activo {
      background-color: #d1fae5;
      color: #065f46;
    }

    .badge-completado {
      background-color: #dbeafe;
      color: #1e40af;
    }

    @media print {
      body {
        print-color-adjust: exact;
        -webkit-print-color-adjust: exact;
      }
      
      button {
        display: none;
      }

      .no-print {
        display: none;
      }
    }
  </style>
</head>
<body>
  <!-- Encabezado -->
  <div class="header">
    <div class="header-left">
      <h1>PodoSkin Libertad</h1>
      <p>Sistema de Gestión Clínica Podológica</p>
    </div>
    <div class="header-right">
      <div class="fecha-impresion">
        Fecha de impresión: ${formatearFecha(new Date().toISOString())}
      </div>
    </div>
  </div>

  <!-- Título del documento -->
  <div style="text-align: center; margin-bottom: 30px;">
    <h2 style="font-size: 18pt; color: #1f2937;">EXPEDIENTE CLÍNICO</h2>
    <p style="color: #6b7280; font-size: 10pt; margin-top: 5px;">
      NOM-024-SSA3-2012 - Sistemas de información de registro electrónico para la salud
    </p>
  </div>

  <!-- Datos Personales -->
  <div class="seccion">
    <div class="seccion-titulo">DATOS PERSONALES</div>
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Nombre completo:</span>
        <span class="info-valor">${paciente.nombres} ${paciente.apellidos}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Fecha de nacimiento:</span>
        <span class="info-valor">${formatearFecha(paciente.fecha_nacimiento)}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Edad:</span>
        <span class="info-valor">${calcularEdad(paciente.fecha_nacimiento)} años</span>
      </div>
      <div class="info-item">
        <span class="info-label">Sexo:</span>
        <span class="info-valor">${paciente.sexo === 'M' ? 'Masculino' : paciente.sexo === 'F' ? 'Femenino' : 'Otro'}</span>
      </div>
      <div class="info-item">
        <span class="info-label">ID Paciente:</span>
        <span class="info-valor">${paciente.documento_id || 'N/A'}</span>
      </div>
      ${paciente.curp ? `
      <div class="info-item">
        <span class="info-label">CURP:</span>
        <span class="info-valor">${paciente.curp}</span>
      </div>
      ` : ''}
    </div>
  </div>

  <!-- Datos de Contacto -->
  <div class="seccion">
    <div class="seccion-titulo">DATOS DE CONTACTO</div>
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Teléfono:</span>
        <span class="info-valor">${paciente.telefono}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Email:</span>
        <span class="info-valor">${paciente.email || 'No registrado'}</span>
      </div>
      <div class="info-item" style="grid-column: 1 / -1;">
        <span class="info-label">Domicilio:</span>
        <span class="info-valor">${paciente.domicilio || 'No registrado'}</span>
      </div>
      ${paciente.estado_residencia ? `
      <div class="info-item">
        <span class="info-label">Estado:</span>
        <span class="info-valor">${paciente.estado_residencia}</span>
      </div>
      ` : ''}
      ${paciente.municipio_residencia ? `
      <div class="info-item">
        <span class="info-label">Municipio:</span>
        <span class="info-valor">${paciente.municipio_residencia}</span>
      </div>
      ` : ''}
      ${paciente.localidad_residencia ? `
      <div class="info-item">
        <span class="info-label">Localidad:</span>
        <span class="info-valor">${paciente.localidad_residencia}</span>
      </div>
      ` : ''}
    </div>
  </div>

  <!-- Datos NOM-024 Adicionales -->
  ${paciente.nacionalidad || paciente.estado_nacimiento ? `
  <div class="seccion">
    <div class="seccion-titulo">DATOS ADICIONALES (NOM-024)</div>
    <div class="info-grid">
      ${paciente.nacionalidad ? `
      <div class="info-item">
        <span class="info-label">Nacionalidad:</span>
        <span class="info-valor">${paciente.nacionalidad}</span>
      </div>
      ` : ''}
      ${paciente.estado_nacimiento ? `
      <div class="info-item">
        <span class="info-label">Estado de nacimiento:</span>
        <span class="info-valor">${paciente.estado_nacimiento}</span>
      </div>
      ` : ''}
    </div>
  </div>
  ` : ''}

  <!-- Historial Clínico -->
  <div class="seccion" style="page-break-before: always;">
    <div class="seccion-titulo">HISTORIAL CLÍNICO</div>
    
    ${tratamientos.length === 0 ? `
      <p style="color: #6b7280; padding: 20px; text-align: center;">
        No hay tratamientos registrados
      </p>
    ` : tratamientos.map(tratamiento => {
      const evolucionesTratamiento = evoluciones.filter((e: any) => e.tratamiento_id === tratamiento.id_tratamiento)
      
      return `
        <div class="tratamiento-box">
          <div class="tratamiento-header">
            📋 ${tratamiento.problema}
            <span class="badge badge-${tratamiento.estado === 'activo' ? 'activo' : 'completado'}" style="float: right;">
              ${tratamiento.estado.toUpperCase()}
            </span>
          </div>
          
          <div style="margin-bottom: 10px;">
            <strong>Fecha inicio:</strong> ${formatearFechaCorta(tratamiento.fecha_inicio)}
            ${tratamiento.fecha_fin ? ` | <strong>Fecha fin:</strong> ${formatearFechaCorta(tratamiento.fecha_fin)}` : ''}
          </div>
          
          ${tratamiento.notas_adicionales ? `
          <div style="margin-bottom: 10px; color: #4b5563;">
            <strong>Notas:</strong> ${tratamiento.notas_adicionales}
          </div>
          ` : ''}

          ${evolucionesTratamiento.length > 0 ? `
          <div style="margin-top: 15px;">
            <strong style="color: #374151;">Evoluciones (${evolucionesTratamiento.length}):</strong>
            ${evolucionesTratamiento.map((evolucion: any) => `
              <div class="evolucion">
                <div class="evolucion-fecha">
                  📅 ${formatearFecha(evolucion.fecha_visita)}
                </div>
                <div class="evolucion-podologo">
                  👨‍⚕️ Dr(a). ${getPodologoNombre(evolucion.podologo_id)}
                  ${evolucion.tipo_visita ? ` - ${evolucion.tipo_visita}` : ''}
                </div>
                <div style="margin-top: 5px; line-height: 1.5;">
                  ${evolucion.nota}
                </div>
                ${evolucion.diagnostico_codigo_cie10 ? `
                <div style="margin-top: 8px; font-size: 9pt; color: #6b7280;">
                  <strong>Diagnóstico CIE-10:</strong> ${evolucion.diagnostico_codigo_cie10}
                </div>
                ` : ''}
                ${evolucion.procedimiento_codigo ? `
                <div style="font-size: 9pt; color: #6b7280;">
                  <strong>Procedimiento:</strong> ${evolucion.procedimiento_codigo}
                </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
          ` : `
          <div style="margin-top: 10px; color: #9ca3af; font-style: italic; font-size: 10pt;">
            Sin evoluciones registradas
          </div>
          `}
        </div>
      `
    }).join('')}
  </div>

  <!-- Firma Digital -->
  <div class="firma-box">
    <p style="font-size: 10pt; color: #6b7280; margin-bottom: 5px;">
      Este documento ha sido generado electrónicamente
    </p>
    <div class="firma-linea"></div>
    <p style="font-weight: bold; color: #1f2937;">
      Firma del Profesional de la Salud
    </p>
    <p style="font-size: 9pt; color: #6b7280; margin-top: 5px;">
      Nombre y Cédula Profesional
    </p>
  </div>

  <!-- Footer -->
  <div class="footer">
    <p>
      Este expediente clínico ha sido generado de acuerdo con la NOM-024-SSA3-2012
    </p>
    <p style="margin-top: 5px;">
      PodoSkin - Sistema de Gestión Clínica Podológica | Fecha de impresión: ${new Date().toLocaleString('es-MX')}
    </p>
  </div>

  <!-- Botón de impresión (solo visible en pantalla) -->
  <div class="no-print" style="position: fixed; bottom: 20px; right: 20px;">
    <button onclick="window.print()" style="
      background-color: #2563eb;
      color: white;
      padding: 12px 24px;
      border: none;
      border-radius: 6px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
      🖨️ Imprimir Expediente
    </button>
  </div>

  <script>
    // Auto-abrir diálogo de impresión después de cargar
    window.addEventListener('load', function() {
      setTimeout(function() {
        window.print();
      }, 500);
    });
  </script>
</body>
</html>
  `
}

/**
 * Abre una ventana nueva con el expediente listo para imprimir
 */
export function imprimirExpediente(props: ExpedienteImpresionProps) {
  const htmlContent = generarExpedienteHTML(props)
  const printWindow = window.open('', '_blank')
  
  if (!printWindow) {
    throw new Error('No se pudo abrir la ventana de impresión. Por favor, permite ventanas emergentes.')
  }
  
  printWindow.document.write(htmlContent)
  printWindow.document.close()
}
