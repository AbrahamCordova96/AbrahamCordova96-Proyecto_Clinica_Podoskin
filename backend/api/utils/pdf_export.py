# =============================================================================
# backend/api/utils/pdf_export.py
# Utilidades para exportar expedientes a PDF
# =============================================================================
"""
This module provides PDF export functionality for patient records.

Uses ReportLab to generate professional PDF documents with:
- Patient demographics
- Medical history
- Treatments
- Clinical notes (SOAP)
- Photographic evidence
"""

from datetime import datetime
from io import BytesIO
from typing import List, Optional
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib import colors

from backend.schemas.core.models import Paciente, Tratamiento, EvolucionClinica

logger = logging.getLogger(__name__)


def generate_patient_pdf(
    paciente,
    tratamientos: List = None,
    evoluciones: List = None,
    include_photos: bool = False
) -> BytesIO:
    """
    Generate a comprehensive PDF report for a patient.
    
    Args:
        paciente: Paciente ORM object
        tratamientos: List of Tratamiento ORM objects (optional)
        evoluciones: List of EvolucionClinica ORM objects (optional)
        include_photos: Whether to include photo evidence (default: False)
        
    Returns:
        BytesIO buffer containing the PDF
        
    Example:
        ```python
        paciente = db.query(Paciente).filter_by(id_paciente=1).first()
        tratamientos = db.query(Tratamiento).filter_by(paciente_id=1).all()
        pdf_buffer = generate_patient_pdf(paciente, tratamientos)
        ```
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='Right', alignment=TA_RIGHT))
    
    # =============================================================================
    # HEADER
    # =============================================================================
    
    # Title
    title = Paragraph("<b>EXPEDIENTE CLÍNICO PODOLÓGICO</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.2*inch))
    
    # Clinic info (customize as needed)
    clinic_info = Paragraph(
        "<b>Clínica PodoSkin</b><br/>"
        "Sistema de Gestión Clínica<br/>"
        f"Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br/>",
        styles['Normal']
    )
    elements.append(clinic_info)
    elements.append(Spacer(1, 0.3*inch))
    
    # =============================================================================
    # PATIENT DEMOGRAPHICS
    # =============================================================================
    
    section_title = Paragraph("<b>DATOS DEL PACIENTE</b>", styles['Heading1'])
    elements.append(section_title)
    elements.append(Spacer(1, 0.1*inch))
    
    # Patient data table
    patient_data = [
        ['ID Paciente:', str(paciente.id_paciente)],
        ['Nombre completo:', f"{paciente.nombres} {paciente.apellidos}"],
        ['Fecha de nacimiento:', _format_date(paciente.fecha_nacimiento)],
        ['Edad:', str(_calculate_age(paciente.fecha_nacimiento)) if paciente.fecha_nacimiento else 'N/A'],
        ['Sexo:', paciente.sexo or 'N/A'],
        ['Teléfono:', paciente.telefono or 'N/A'],
        ['Email:', paciente.email or 'N/A'],
        ['Domicilio:', paciente.domicilio or 'N/A'],
        ['Ocupación:', paciente.ocupacion or 'N/A'],
        ['Estado civil:', paciente.estado_civil or 'N/A'],
    ]
    
    patient_table = Table(patient_data, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    elements.append(patient_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # =============================================================================
    # TREATMENTS
    # =============================================================================
    
    if tratamientos:
        section_title = Paragraph("<b>TRATAMIENTOS</b>", styles['Heading1'])
        elements.append(section_title)
        elements.append(Spacer(1, 0.1*inch))
        
        for i, trat in enumerate(tratamientos, 1):
            treatment_text = (
                f"<b>{i}. {trat.problema}</b><br/>"
                f"Estado: {trat.estado}<br/>"
                f"Fecha inicio: {trat.fecha_inicio.strftime('%d/%m/%Y') if trat.fecha_inicio else 'N/A'}<br/>"
            )
            if trat.fecha_fin:
                treatment_text += f"Fecha fin: {trat.fecha_fin.strftime('%d/%m/%Y')}<br/>"
            if trat.diagnostico_texto:
                treatment_text += f"Diagnóstico: {trat.diagnostico_texto}<br/>"
            
            elements.append(Paragraph(treatment_text, styles['Normal']))
            elements.append(Spacer(1, 0.15*inch))
    
    # =============================================================================
    # CLINICAL NOTES (EVOLUCIONES)
    # =============================================================================
    
    if evoluciones:
        section_title = Paragraph("<b>NOTAS CLÍNICAS (SOAP)</b>", styles['Heading1'])
        elements.append(section_title)
        elements.append(Spacer(1, 0.1*inch))
        
        for i, evol in enumerate(evoluciones, 1):
            note_text = (
                f"<b>Sesión {i} - {evol.fecha_sesion.strftime('%d/%m/%Y') if evol.fecha_sesion else 'N/A'}</b><br/>"
                f"<b>S (Subjetivo):</b> {evol.nota_subjetiva or 'N/A'}<br/>"
                f"<b>O (Objetivo):</b> {evol.nota_objetiva or 'N/A'}<br/>"
                f"<b>A (Análisis):</b> {evol.analisis_texto or 'N/A'}<br/>"
                f"<b>P (Plan):</b> {evol.plan_texto or 'N/A'}<br/>"
            )
            
            elements.append(Paragraph(note_text, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Page break after every 2 notes to avoid overflow
            if i % 2 == 0 and i < len(evoluciones):
                elements.append(PageBreak())
    
    # =============================================================================
    # FOOTER
    # =============================================================================
    
    elements.append(Spacer(1, 0.5*inch))
    footer = Paragraph(
        "<i>Este documento es confidencial y contiene información médica protegida.<br/>"
        "Generado por PodoSkin - Sistema de Gestión Clínica Podológica</i>",
        styles['Normal']
    )
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()
    return BytesIO(pdf)


def _format_date(date_obj) -> str:
    """Format date object to string, handling None and various types"""
    if not date_obj:
        return 'N/A'
    try:
        if hasattr(date_obj, 'strftime'):
            return date_obj.strftime('%d/%m/%Y')
        return str(date_obj)
    except:
        return 'N/A'


def _calculate_age(birth_date) -> int:
    """Calculate age from birth date"""
    if not birth_date:
        return 0
    try:
        today = datetime.now().date()
        # Handle both date and datetime objects
        if hasattr(birth_date, 'date'):
            birth_date = birth_date.date()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return 0
