"""
Factories para generación de datos de prueba
============================================

Usa Factory Boy y Faker para crear datos realistas de prueba.
Cada factory corresponde a un modelo de base de datos.
"""

import factory
from factory import fuzzy
from datetime import date, datetime, timedelta
from decimal import Decimal
import random

from backend.schemas.auth.models import Clinica, SysUsuario, AuditLog
from backend.schemas.core.models import (
    Paciente, Tratamiento, EvolucionClinica, EvidenciaFotografica
)
from backend.schemas.ops.models import (
    Podologo, Cita, CatalogoServicio, SolicitudProspecto
)
from backend.schemas.finance.models import (
    MetodoPago, Transaccion, Pago, Gasto
)


# =============================================================================
# FACTORIES DE AUTENTICACIÓN
# =============================================================================

class ClinicaFactory(factory.Factory):
    """Factory para clínicas."""
    
    class Meta:
        model = Clinica
    
    nombre = factory.Faker('company', locale='es_MX')
    direccion = factory.Faker('address', locale='es_MX')
    telefono = factory.Faker('phone_number', locale='es_MX')
    email = factory.Faker('company_email', locale='es_MX')
    activa = True


class SysUsuarioFactory(factory.Factory):
    """Factory para usuarios del sistema."""
    
    class Meta:
        model = SysUsuario
    
    nombre_usuario = factory.Faker('user_name')
    email = factory.Faker('email', locale='es_MX')
    nombre = factory.Faker('first_name', locale='es_MX')
    apellidos = factory.Faker('last_name', locale='es_MX')
    password_hash = "$argon2id$v=19$m=65536,t=3,p=4$test"  # Hash de "test123"
    rol = fuzzy.FuzzyChoice(['Admin', 'Podologo', 'Recepcion'])
    activo = True
    clinica_id = None  # Se asigna manualmente


# =============================================================================
# FACTORIES DE PACIENTES Y DATOS CLÍNICOS
# =============================================================================

class PacienteFactory(factory.Factory):
    """Factory para pacientes."""
    
    class Meta:
        model = Paciente
    
    nombres = factory.Faker('first_name', locale='es_MX')
    apellidos = factory.Faker('last_name', locale='es_MX')
    
    @factory.lazy_attribute
    def fecha_nacimiento(self):
        """Generar fecha de nacimiento realista (18-80 años)."""
        today = date.today()
        years_ago = random.randint(18, 80)
        return today - timedelta(days=years_ago * 365)
    
    sexo = fuzzy.FuzzyChoice(['M', 'F'])
    
    @factory.lazy_attribute
    def telefono(self):
        """Generar teléfono mexicano."""
        return f"55{random.randint(10000000, 99999999)}"
    
    email = factory.Faker('email', locale='es_MX')
    domicilio = factory.Faker('address', locale='es_MX')
    
    @factory.lazy_attribute
    def peso_kg(self):
        """Peso en kg (45-120 kg)."""
        return Decimal(str(round(random.uniform(45.0, 120.0), 1)))
    
    @factory.lazy_attribute
    def estatura_cm(self):
        """Estatura en cm (140-200 cm)."""
        return Decimal(str(round(random.uniform(140.0, 200.0), 1)))
    
    ocupacion = factory.Faker('job', locale='es_MX')
    estado_civil = fuzzy.FuzzyChoice(['Soltero', 'Casado', 'Divorciado', 'Viudo', 'Union libre'])
    activo = True


class TratamientoFactory(factory.Factory):
    """Factory para tratamientos."""
    
    class Meta:
        model = Tratamiento
    
    paciente_id = None  # Se asigna manualmente
    
    problema = fuzzy.FuzzyChoice([
        'Onicomicosis',
        'Uña encarnada',
        'Callos y durezas',
        'Pie diabético',
        'Verrugas plantares',
        'Fascitis plantar',
        'Espolón calcáneo',
        'Deformidades digitales',
        'Hiperhidrosis',
        'Pie plano'
    ])
    
    diagnostico = factory.LazyAttribute(lambda o: f"Diagnóstico de {o.problema}")
    
    @factory.lazy_attribute
    def fecha_inicio(self):
        """Fecha de inicio en los últimos 2 años."""
        days_ago = random.randint(0, 730)
        return date.today() - timedelta(days=days_ago)
    
    fecha_fin = None  # Algunos tratamientos están en curso
    
    estado = fuzzy.FuzzyChoice(['activo', 'completado', 'en_pausa'])
    observaciones = factory.Faker('sentence', locale='es_MX')
    activo = True


class EvolucionClinicaFactory(factory.Factory):
    """Factory para evoluciones clínicas (notas SOAP)."""
    
    class Meta:
        model = EvolucionClinica
    
    tratamiento_id = None  # Se asigna manualmente
    
    @factory.lazy_attribute
    def fecha(self):
        """Fecha de la nota."""
        days_ago = random.randint(0, 180)
        return date.today() - timedelta(days=days_ago)
    
    # Formato SOAP
    subjetivo = factory.Faker('paragraph', locale='es_MX')
    objetivo = factory.Faker('paragraph', locale='es_MX')
    analisis = factory.Faker('paragraph', locale='es_MX')
    plan = factory.Faker('paragraph', locale='es_MX')
    
    observaciones = factory.Faker('sentence', locale='es_MX')


class EvidenciaFotograficaFactory(factory.Factory):
    """Factory para evidencias fotográficas."""
    
    class Meta:
        model = EvidenciaFotografica
    
    tratamiento_id = None
    
    @factory.lazy_attribute
    def fecha(self):
        days_ago = random.randint(0, 180)
        return date.today() - timedelta(days=days_ago)
    
    @factory.lazy_attribute
    def ruta_archivo(self):
        """Ruta simulada de archivo."""
        return f"/evidencias/tratamiento_{self.tratamiento_id}/foto_{random.randint(1000, 9999)}.jpg"
    
    descripcion = factory.Faker('sentence', locale='es_MX')
    tipo_imagen = fuzzy.FuzzyChoice(['Pre-tratamiento', 'Durante', 'Post-tratamiento', 'Seguimiento'])


# =============================================================================
# FACTORIES DE OPERACIONES (CITAS, PODÓLOGOS)
# =============================================================================

class PodologoFactory(factory.Factory):
    """Factory para podólogos."""
    
    class Meta:
        model = Podologo
    
    nombre = factory.Faker('first_name', locale='es_MX')
    apellidos = factory.Faker('last_name', locale='es_MX')
    especialidad = fuzzy.FuzzyChoice([
        'Podología General',
        'Pie Diabético',
        'Biomecánica',
        'Podología Deportiva',
        'Cirugía Podológica'
    ])
    
    @factory.lazy_attribute
    def cedula_profesional(self):
        return str(random.randint(10000000, 99999999))
    
    @factory.lazy_attribute
    def telefono(self):
        return f"55{random.randint(10000000, 99999999)}"
    
    email = factory.Faker('email', locale='es_MX')
    activo = True


class CatalogoServicioFactory(factory.Factory):
    """Factory para servicios."""
    
    class Meta:
        model = CatalogoServicio
    
    nombre = fuzzy.FuzzyChoice([
        'Consulta General',
        'Corte de uñas',
        'Eliminación de callos',
        'Tratamiento onicomicosis',
        'Plantillas ortopédicas',
        'Láser para hongos',
        'Limpieza profunda',
        'Masaje podológico'
    ])
    
    descripcion = factory.Faker('paragraph', locale='es_MX')
    
    @factory.lazy_attribute
    def duracion_minutos(self):
        return random.choice([30, 45, 60, 90, 120])
    
    @factory.lazy_attribute
    def precio(self):
        return Decimal(str(random.choice([300, 400, 500, 600, 800, 1000, 1200, 1500])))
    
    activo = True


class CitaFactory(factory.Factory):
    """Factory para citas."""
    
    class Meta:
        model = Cita
    
    paciente_id = None  # Se asigna manualmente
    podologo_id = None  # Se asigna manualmente
    servicio_id = None  # Se asigna manualmente
    
    @factory.lazy_attribute
    def fecha_hora(self):
        """Generar fecha/hora de cita en el futuro cercano o pasado reciente."""
        days_offset = random.randint(-30, 60)  # 30 días atrás a 60 días adelante
        hour = random.randint(8, 18)  # Horario de 8am a 6pm
        minute = random.choice([0, 30])  # Intervalos de 30 minutos
        base_date = datetime.now() + timedelta(days=days_offset)
        return base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    estado = fuzzy.FuzzyChoice(['agendada', 'completada', 'cancelada', 'no_asistio'])
    
    @factory.lazy_attribute
    def duracion_minutos(self):
        return random.choice([30, 45, 60, 90])
    
    motivo = factory.Faker('sentence', locale='es_MX')
    observaciones = factory.Faker('sentence', locale='es_MX')


class SolicitudProspectoFactory(factory.Factory):
    """Factory para solicitudes de prospectos."""
    
    class Meta:
        model = SolicitudProspecto
    
    nombre = factory.Faker('first_name', locale='es_MX')
    apellidos = factory.Faker('last_name', locale='es_MX')
    
    @factory.lazy_attribute
    def telefono(self):
        return f"55{random.randint(10000000, 99999999)}"
    
    email = factory.Faker('email', locale='es_MX')
    motivo_consulta = factory.Faker('sentence', locale='es_MX')
    
    @factory.lazy_attribute
    def fecha_contacto(self):
        days_ago = random.randint(0, 90)
        return datetime.now() - timedelta(days=days_ago)
    
    estado = fuzzy.FuzzyChoice(['nuevo', 'contactado', 'agendado', 'convertido', 'descartado'])
    observaciones = factory.Faker('paragraph', locale='es_MX')


# =============================================================================
# FACTORIES FINANCIERAS
# =============================================================================

class MetodoPagoFactory(factory.Factory):
    """Factory para métodos de pago."""
    
    class Meta:
        model = MetodoPago
    
    nombre = fuzzy.FuzzyChoice(['Efectivo', 'Tarjeta', 'Transferencia', 'PayPal'])
    descripcion = factory.Faker('sentence', locale='es_MX')
    activo = True


class TransaccionFactory(factory.Factory):
    """Factory para transacciones."""
    
    class Meta:
        model = Transaccion
    
    cita_id = None  # Se asigna manualmente
    
    @factory.lazy_attribute
    def fecha(self):
        days_ago = random.randint(0, 180)
        return date.today() - timedelta(days=days_ago)
    
    tipo = fuzzy.FuzzyChoice(['ingreso', 'gasto'])
    
    @factory.lazy_attribute
    def monto(self):
        return Decimal(str(random.uniform(100.0, 2000.0)))
    
    concepto = factory.Faker('sentence', locale='es_MX')
    metodo_pago = fuzzy.FuzzyChoice(['Efectivo', 'Tarjeta', 'Transferencia'])


class PagoFactory(factory.Factory):
    """Factory para pagos."""
    
    class Meta:
        model = Pago
    
    transaccion_id = None
    cita_id = None
    metodo_pago_id = None
    
    @factory.lazy_attribute
    def monto(self):
        return Decimal(str(random.uniform(100.0, 2000.0)))
    
    @factory.lazy_attribute
    def fecha(self):
        days_ago = random.randint(0, 180)
        return date.today() - timedelta(days=days_ago)
    
    estado = fuzzy.FuzzyChoice(['pendiente', 'pagado', 'cancelado'])


class GastoFactory(factory.Factory):
    """Factory para gastos."""
    
    class Meta:
        model = Gasto
    
    concepto = fuzzy.FuzzyChoice([
        'Renta de local',
        'Servicios (luz, agua)',
        'Material médico',
        'Insumos de limpieza',
        'Mantenimiento equipo',
        'Publicidad',
        'Salarios',
        'Seguros'
    ])
    
    @factory.lazy_attribute
    def monto(self):
        return Decimal(str(random.uniform(500.0, 20000.0)))
    
    @factory.lazy_attribute
    def fecha(self):
        days_ago = random.randint(0, 365)
        return date.today() - timedelta(days=days_ago)
    
    categoria = fuzzy.FuzzyChoice(['Operativo', 'Administrativo', 'Marketing', 'Equipamiento'])
    observaciones = factory.Faker('sentence', locale='es_MX')
