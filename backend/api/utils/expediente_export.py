# =============================================================================
# backend/api/utils/expediente_export.py
# NOM-024 Compliance: Patient Record Export Utilities
# =============================================================================
# Funciones para exportar expedientes completos en múltiples formatos:
#   - HTML: Formato elegante para impresión y visualización
#   - JSON: Formato estructurado preparado para HL7 CDA
#   - XML: Estructura preparada para interoperabilidad futura
#
# NOM-024 requiere la capacidad de exportar expedientes completos
# para intercambio con otras instituciones.
# =============================================================================

from typing import Dict, Any, List
from datetime import date, datetime
from sqlalchemy.orm import Session
from jinja2 import Template, Environment, FileSystemLoader
import json
import os
import logging

from backend.schemas.core.models import (
    Paciente, HistorialMedicoGeneral, Tratamiento, EvolucionClinica
)
from backend.schemas.ops.models import Podologo

logger = logging.getLogger(__name__)


def calcular_edad(fecha_nacimiento: date) -> int:
    """
    Calcula la edad a partir de la fecha de nacimiento.
    
    Args:
        fecha_nacimiento: Fecha de nacimiento del paciente
    
    Returns:
        Edad en años
    """
    hoy = date.today()
    edad = hoy.year - fecha_nacimiento.year
    
    # Ajustar si aún no ha cumplido años este año
    if (hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day):
        edad -= 1
    
    return edad


def exportar_expediente_html(
    core_db: Session,
    ops_db: Session,
    paciente_id: int
) -> str:
    """
    Exporta el expediente completo de un paciente en formato HTML.
    
    Genera un documento HTML profesional y elegante que incluye:
    - Datos personales del paciente
    - Historial médico general
    - Tratamientos registrados
    - Evoluciones clínicas (notas SOAP)
    - Formato listo para imprimir (CSS optimizado)
    
    Args:
        core_db: Sesión de base de datos clinica_core_db
        ops_db: Sesión de base de datos clinica_ops_db
        paciente_id: ID del paciente a exportar
    
    Returns:
        String con HTML completo del expediente
    
    Raises:
        ValueError: Si el paciente no existe
    """
    # Obtener datos del paciente
    paciente = core_db.query(Paciente).filter_by(id_paciente=paciente_id).first()
    if not paciente:
        raise ValueError(f"Paciente con ID {paciente_id} no encontrado")
    
    # Obtener historial médico
    historial_medico = core_db.query(HistorialMedicoGeneral).filter_by(
        paciente_id=paciente_id
    ).first()
    
    # Obtener tratamientos
    tratamientos = core_db.query(Tratamiento).filter_by(
        paciente_id=paciente_id
    ).order_by(Tratamiento.fecha_inicio.desc()).all()
    
    # Obtener evoluciones clínicas con información del podólogo
    evoluciones_data = []
    for tratamiento in tratamientos:
        evoluciones = core_db.query(EvolucionClinica).filter_by(
            tratamiento_id=tratamiento.id_tratamiento
        ).order_by(EvolucionClinica.fecha_visita.desc()).all()
        
        for evolucion in evoluciones:
            # Obtener nombre del podólogo (cross-database query)
            podologo_nombre = None
            if evolucion.podologo_id:
                podologo = ops_db.query(Podologo).filter_by(
                    id_podologo=evolucion.podologo_id
                ).first()
                if podologo:
                    podologo_nombre = podologo.nombre_completo
            
            evoluciones_data.append({
                "fecha_visita": evolucion.fecha_visita.strftime("%d/%m/%Y %H:%M"),
                "podologo_nombre": podologo_nombre,
                "nota_subjetiva": evolucion.nota_subjetiva,
                "nota_objetiva": evolucion.nota_objetiva,
                "analisis_texto": evolucion.analisis_texto,
                "plan_texto": evolucion.plan_texto,
                "signos_vitales_visita": evolucion.signos_vitales_visita
            })
    
    # Preparar datos para el template
    template_data = {
        "paciente": paciente,
        "edad": calcular_edad(paciente.fecha_nacimiento),
        "sexo_texto": "Masculino" if paciente.sexo == "M" else "Femenino" if paciente.sexo == "F" else "No especificado",
        "historial_medico": historial_medico,
        "tratamientos": tratamientos,
        "evoluciones": evoluciones_data,
        "fecha_generacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    }
    
    # Cargar y renderizar template
    template_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "templates"
    )
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("expediente.html")
    
    html_output = template.render(**template_data)
    
    logger.info(f"Expediente HTML generado para paciente {paciente_id}")
    
    return html_output


def exportar_expediente_json(
    core_db: Session,
    ops_db: Session,
    paciente_id: int
) -> Dict[str, Any]:
    """
    Exporta el expediente en formato JSON estructurado.
    
    El formato está inspirado en HL7 CDA (Clinical Document Architecture)
    para facilitar futura interoperabilidad.
    
    Args:
        core_db: Sesión de base de datos clinica_core_db
        ops_db: Sesión de base de datos clinica_ops_db
        paciente_id: ID del paciente a exportar
    
    Returns:
        Dict con el expediente estructurado en formato JSON
    
    Structure:
        {
            "clinicalDocument": {
                "patient": {...},
                "medicalHistory": {...},
                "treatments": [...],
                "encounters": [...]  # Evoluciones/consultas
            }
        }
    """
    # Obtener datos del paciente
    paciente = core_db.query(Paciente).filter_by(id_paciente=paciente_id).first()
    if not paciente:
        raise ValueError(f"Paciente con ID {paciente_id} no encontrado")
    
    # Estructurar datos del paciente (HL7-like)
    patient_data = {
        "id": paciente.id_paciente,
        "name": {
            "given": paciente.nombres,
            "family": paciente.apellidos
        },
        "birthDate": paciente.fecha_nacimiento.isoformat() if paciente.fecha_nacimiento else None,
        "gender": paciente.sexo,
        "telecom": [
            {"system": "phone", "value": paciente.telefono},
            {"system": "email", "value": paciente.email}
        ],
        "address": paciente.domicilio,
        "identifiers": [
            {"system": "CURP", "value": paciente.curp}
        ] if paciente.curp else []
    }
    
    # Historial médico
    historial = core_db.query(HistorialMedicoGeneral).filter_by(
        paciente_id=paciente_id
    ).first()
    
    medical_history = None
    if historial:
        medical_history = {
            "weight": float(historial.peso_kg) if historial.peso_kg else None,
            "height": float(historial.talla_cm) if historial.talla_cm else None,
            "bmi": float(historial.imc) if historial.imc else None,
            "bloodType": historial.tipos_sangre,
            "allergies": {
                "active": historial.alergias_activas,
                "list": historial.lista_alergias
            },
            "familyHistory": {
                "diabetes": historial.ahf_diabetes,
                "hypertension": historial.ahf_hipertension,
                "cancer": historial.ahf_cancer,
                "cardiac": historial.ahf_cardiacas
            }
        }
    
    # Tratamientos
    tratamientos = core_db.query(Tratamiento).filter_by(
        paciente_id=paciente_id
    ).order_by(Tratamiento.fecha_inicio.desc()).all()
    
    treatments_data = []
    for tratamiento in tratamientos:
        treatments_data.append({
            "id": tratamiento.id_tratamiento,
            "chiefComplaint": tratamiento.motivo_consulta_principal,
            "diagnosis": tratamiento.diagnostico_inicial,
            "startDate": tratamiento.fecha_inicio.isoformat() if tratamiento.fecha_inicio else None,
            "status": tratamiento.estado_tratamiento,
            "plan": tratamiento.plan_general
        })
    
    # Evoluciones (encounters/consultas)
    encounters_data = []
    for tratamiento in tratamientos:
        evoluciones = core_db.query(EvolucionClinica).filter_by(
            tratamiento_id=tratamiento.id_tratamiento
        ).order_by(EvolucionClinica.fecha_visita.desc()).all()
        
        for evolucion in evoluciones:
            # Obtener podólogo
            practitioner_name = None
            if evolucion.podologo_id:
                podologo = ops_db.query(Podologo).filter_by(
                    id_podologo=evolucion.podologo_id
                ).first()
                if podologo:
                    practitioner_name = podologo.nombre_completo
            
            encounters_data.append({
                "id": evolucion.id_evolucion,
                "date": evolucion.fecha_visita.isoformat(),
                "practitioner": practitioner_name,
                "soapNote": {
                    "subjective": evolucion.nota_subjetiva,
                    "objective": evolucion.nota_objetiva,
                    "assessment": evolucion.analisis_texto,
                    "plan": evolucion.plan_texto
                },
                "vitalSigns": evolucion.signos_vitales_visita,
                "treatmentId": tratamiento.id_tratamiento
            })
    
    # Documento clínico estructurado (HL7 CDA-like)
    clinical_document = {
        "clinicalDocument": {
            "version": "1.0",
            "generatedAt": datetime.now().isoformat(),
            "standard": "NOM-024-SSA3-2012",
            "patient": patient_data,
            "medicalHistory": medical_history,
            "treatments": treatments_data,
            "encounters": encounters_data
        }
    }
    
    logger.info(f"Expediente JSON generado para paciente {paciente_id}")
    
    return clinical_document


def exportar_expediente_xml(
    core_db: Session,
    ops_db: Session,
    paciente_id: int
) -> str:
    """
    Exporta el expediente en formato XML.
    
    Estructura preparada para interoperabilidad futura con HL7 CDA.
    
    Args:
        core_db: Sesión de base de datos clinica_core_db
        ops_db: Sesión de base de datos clinica_ops_db
        paciente_id: ID del paciente a exportar
    
    Returns:
        String con XML del expediente
    
    Note:
        Por ahora genera XML básico. En el futuro se puede implementar
        HL7 CDA completo cuando se necesite certificación.
    """
    # Obtener datos en formato JSON primero
    json_data = exportar_expediente_json(core_db, ops_db, paciente_id)
    
    # Convertir JSON a XML básico
    # TODO: Implementar conversión completa a HL7 CDA cuando se necesite
    
    xml_output = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_output += '<ClinicalDocument xmlns="urn:hl7-org:v3">\n'
    xml_output += f'  <version>{json_data["clinicalDocument"]["version"]}</version>\n'
    xml_output += f'  <generatedAt>{json_data["clinicalDocument"]["generatedAt"]}</generatedAt>\n'
    xml_output += f'  <standard>{json_data["clinicalDocument"]["standard"]}</standard>\n'
    
    # Patient
    patient = json_data["clinicalDocument"]["patient"]
    xml_output += '  <patient>\n'
    xml_output += f'    <id>{patient["id"]}</id>\n'
    xml_output += f'    <name>\n'
    xml_output += f'      <given>{patient["name"]["given"]}</given>\n'
    xml_output += f'      <family>{patient["name"]["family"]}</family>\n'
    xml_output += f'    </name>\n'
    xml_output += f'    <birthDate>{patient["birthDate"]}</birthDate>\n'
    xml_output += f'    <gender>{patient["gender"]}</gender>\n'
    xml_output += '  </patient>\n'
    
    # Tratamientos
    xml_output += '  <treatments>\n'
    for treatment in json_data["clinicalDocument"]["treatments"]:
        xml_output += '    <treatment>\n'
        xml_output += f'      <id>{treatment["id"]}</id>\n'
        xml_output += f'      <chiefComplaint>{treatment["chiefComplaint"]}</chiefComplaint>\n'
        xml_output += f'      <status>{treatment["status"]}</status>\n'
        xml_output += '    </treatment>\n'
    xml_output += '  </treatments>\n'
    
    xml_output += '</ClinicalDocument>\n'
    
    logger.info(f"Expediente XML generado para paciente {paciente_id}")
    
    return xml_output
