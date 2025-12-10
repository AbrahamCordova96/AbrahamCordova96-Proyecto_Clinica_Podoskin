# =============================================================================
# backend/api/utils/notifications.py
# Utilidades para envío de notificaciones (email/SMS)
# =============================================================================
"""
This module provides notification utilities for appointment reminders.

Supports:
- Email notifications via SMTP
- SMS notifications (via third-party providers - to be implemented)
- Templates for different notification types
"""

from typing import Optional, Dict, Any
from datetime import datetime, date, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import aiosmtplib
from jinja2 import Template

from backend.api.core.config import get_settings

settings = get_settings()


# =============================================================================
# EMAIL CONFIGURATION
# =============================================================================

# Get SMTP configuration from settings
SMTP_HOST = settings.SMTP_HOST
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASSWORD = settings.SMTP_PASSWORD
FROM_EMAIL = settings.FROM_EMAIL


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

APPOINTMENT_REMINDER_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background-color: #4CAF50; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background-color: #f9f9f9; }
        .appointment-details { background-color: white; padding: 15px; margin: 20px 0; border-left: 4px solid #4CAF50; }
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #666; }
        .btn { display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦶 Recordatorio de Cita - PodoSkin</h1>
        </div>
        <div class="content">
            <p>Hola <strong>{{ patient_name }}</strong>,</p>
            
            <p>Este es un recordatorio de tu próxima cita en nuestra clínica podológica.</p>
            
            <div class="appointment-details">
                <h3>Detalles de la Cita</h3>
                <p><strong>Fecha:</strong> {{ appointment_date }}</p>
                <p><strong>Hora:</strong> {{ appointment_time }}</p>
                <p><strong>Podólogo:</strong> {{ podiatrist_name }}</p>
                <p><strong>Servicio:</strong> {{ service_name }}</p>
                {% if notes %}
                <p><strong>Notas:</strong> {{ notes }}</p>
                {% endif %}
            </div>
            
            <p>Por favor, llega 10 minutos antes de tu cita.</p>
            
            <p>Si necesitas cancelar o reprogramar, contáctanos lo antes posible.</p>
            
            <p>¡Te esperamos!</p>
        </div>
        <div class="footer">
            <p>Este es un mensaje automático, por favor no responder.</p>
            <p>Clínica PodoSkin - Sistema de Gestión Clínica</p>
        </div>
    </div>
</body>
</html>
"""


# =============================================================================
# NOTIFICATION FUNCTIONS
# =============================================================================

async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    from_email: str = FROM_EMAIL
) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML content of the email
        from_email: Sender email address
        
    Returns:
        True if email sent successfully, False otherwise
        
    Note:
        Requires SMTP configuration in environment variables:
        - SMTP_HOST
        - SMTP_PORT
        - SMTP_USER
        - SMTP_PASSWORD
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("Warning: SMTP credentials not configured. Email not sent.")
        return False
    
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["From"] = from_email
        message["To"] = to_email
        message["Subject"] = subject
        
        # Attach HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)
        
        # Send email
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=True
        )
        
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False


async def send_appointment_reminder(
    patient_name: str,
    patient_email: str,
    appointment_date: date,
    appointment_time: time,
    podiatrist_name: str,
    service_name: str,
    notes: Optional[str] = None
) -> bool:
    """
    Send an appointment reminder email to a patient.
    
    Args:
        patient_name: Patient's full name
        patient_email: Patient's email address
        appointment_date: Date of the appointment
        appointment_time: Time of the appointment
        podiatrist_name: Name of the attending podiatrist
        service_name: Name of the service
        notes: Optional appointment notes
        
    Returns:
        True if reminder sent successfully, False otherwise
        
    Example:
        ```python
        success = await send_appointment_reminder(
            patient_name="Juan Pérez",
            patient_email="juan@example.com",
            appointment_date=date(2025, 12, 15),
            appointment_time=time(10, 0),
            podiatrist_name="Dr. María García",
            service_name="Consulta General",
            notes="Traer estudios previos"
        )
        ```
    """
    # Format date and time for Spanish locale
    formatted_date = appointment_date.strftime("%A, %d de %B de %Y")
    formatted_time = appointment_time.strftime("%H:%M")
    
    # Render template
    template = Template(APPOINTMENT_REMINDER_TEMPLATE)
    html_content = template.render(
        patient_name=patient_name,
        appointment_date=formatted_date,
        appointment_time=formatted_time,
        podiatrist_name=podiatrist_name,
        service_name=service_name,
        notes=notes
    )
    
    # Send email
    subject = f"Recordatorio: Cita PodoSkin - {formatted_date}"
    
    return await send_email(
        to_email=patient_email,
        subject=subject,
        html_content=html_content
    )


async def send_sms(
    phone_number: str,
    message: str
) -> bool:
    """
    Send an SMS notification (to be implemented with SMS provider).
    
    Args:
        phone_number: Recipient phone number
        message: SMS message content
        
    Returns:
        True if SMS sent successfully, False otherwise
        
    Note:
        This is a placeholder. Implement with your SMS provider:
        - Twilio
        - AWS SNS
        - Nexmo
        - etc.
    """
    # TODO: Implement SMS sending with chosen provider
    print(f"SMS placeholder: Would send to {phone_number}: {message}")
    return False


def format_appointment_sms(
    patient_name: str,
    appointment_date: date,
    appointment_time: time,
    podiatrist_name: str
) -> str:
    """
    Format an appointment reminder for SMS (keep it short).
    
    Args:
        patient_name: Patient's first name
        appointment_date: Date of appointment
        appointment_time: Time of appointment
        podiatrist_name: Name of podiatrist
        
    Returns:
        Formatted SMS message (160 chars max recommended)
    """
    formatted_date = appointment_date.strftime("%d/%m/%Y")
    formatted_time = appointment_time.strftime("%H:%M")
    
    return (
        f"Hola {patient_name}! Recordatorio: "
        f"Cita PodoSkin {formatted_date} {formatted_time} "
        f"con {podiatrist_name}. Confirma tu asistencia."
    )
