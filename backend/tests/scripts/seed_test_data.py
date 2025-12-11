#!/usr/bin/env python3
"""
Script de Seed - Generación de Datos Placebo
============================================

Este script genera datos de prueba realistas para todas las áreas de la aplicación.

Uso:
    python backend/tests/scripts/seed_test_data.py --count 100
    
Opciones:
    --count N : Número de registros por entidad (default: 50)
    --clean   : Limpiar datos existentes antes de generar
    --db TYPE : Tipo de BD (sqlite|postgres, default: postgres)
"""

import os
import sys
import argparse
from datetime import date, datetime, timedelta
import random
from decimal import Decimal

# Agregar path del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Importar modelos
from backend.schemas.auth.models import Base as AuthBase, Clinica, SysUsuario, AuditLog
from backend.schemas.core.models import (
    Base as CoreBase, Paciente, Tratamiento, EvolucionClinica, EvidenciaFotografica
)
from backend.schemas.ops.models import (
    Base as OpsBase, Podologo, Cita, CatalogoServicio, SolicitudProspecto
)
from backend.schemas.finance.models import (
    Base as FinanceBase, MetodoPago, Transaccion, Pago, Gasto
)

# Importar factories
from backend.tests.factories import (
    ClinicaFactory, SysUsuarioFactory, PacienteFactory, TratamientoFactory,
    EvolucionClinicaFactory, EvidenciaFotograficaFactory, PodologoFactory,
    CitaFactory, CatalogoServicioFactory, SolicitudProspectoFactory,
    MetodoPagoFactory, TransaccionFactory, PagoFactory, GastoFactory
)

from backend.api.core.security import get_password_hash


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# URLs de base de datos (usar las mismas que config.py)
AUTH_DB_URL = os.getenv("AUTH_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db")
CORE_DB_URL = os.getenv("CORE_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db")
OPS_DB_URL = os.getenv("OPS_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db")


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def create_sessions():
    """Crear sesiones de BD."""
    print("📊 Conectando a bases de datos...")
    
    auth_engine = create_engine(AUTH_DB_URL)
    core_engine = create_engine(CORE_DB_URL)
    ops_engine = create_engine(OPS_DB_URL)
    
    AuthSession = sessionmaker(bind=auth_engine)
    CoreSession = sessionmaker(bind=core_engine)
    OpsSession = sessionmaker(bind=ops_engine)
    
    return AuthSession(), CoreSession(), OpsSession()


def clean_databases(auth_db, core_db, ops_db):
    """Limpiar todas las tablas (CUIDADO: borra todo)."""
    print("🧹 Limpiando datos existentes...")
    
    # Limpiar en orden inverso para respetar FKs
    try:
        # Auth DB
        auth_db.query(AuditLog).delete()
        auth_db.query(SysUsuario).delete()
        auth_db.query(Clinica).delete()
        auth_db.commit()
        
        # Core DB
        core_db.query(EvidenciaFotografica).delete()
        core_db.query(EvolucionClinica).delete()
        core_db.query(Tratamiento).delete()
        core_db.query(Paciente).delete()
        core_db.commit()
        
        # Ops DB
        ops_db.query(Pago).delete()
        ops_db.query(Gasto).delete()
        ops_db.query(Transaccion).delete()
        ops_db.query(Cita).delete()
        ops_db.query(SolicitudProspecto).delete()
        ops_db.query(CatalogoServicio).delete()
        ops_db.query(Podologo).delete()
        ops_db.query(MetodoPago).delete()
        ops_db.commit()
        
        print("✅ Datos limpiados exitosamente")
    except Exception as e:
        print(f"⚠️  Error al limpiar: {e}")
        auth_db.rollback()
        core_db.rollback()
        ops_db.rollback()


# =============================================================================
# GENERADORES DE DATOS
# =============================================================================

def seed_auth_data(auth_db, count=10):
    """Generar datos de autenticación."""
    print(f"\n🔐 Generando datos de autenticación...")
    
    # Crear clínica principal
    clinica = Clinica(
        nombre="PodoSkin - Clínica Central",
        direccion="Av. Reforma 123, CDMX",
        telefono="5555551234",
        email="contacto@podoskin.mx",
        activa=True
    )
    auth_db.add(clinica)
    auth_db.commit()
    auth_db.refresh(clinica)
    print(f"  ✓ Clínica: {clinica.nombre}")
    
    # Crear usuarios de prueba con diferentes roles
    usuarios = []
    
    # Admin
    admin = SysUsuario(
        nombre_usuario="admin",
        email="admin@podoskin.mx",
        nombre="Administrador",
        apellidos="Sistema",
        password_hash=get_password_hash("admin123"),
        rol="Admin",
        activo=True,
        clinica_id=clinica.id_clinica
    )
    auth_db.add(admin)
    usuarios.append(admin)
    
    # Podólogos
    for i in range(count // 2):
        user = SysUsuario(
            nombre_usuario=f"podologo{i+1}",
            email=f"podologo{i+1}@podoskin.mx",
            nombre=f"Doctor{i+1}",
            apellidos=f"Podólogo{i+1}",
            password_hash=get_password_hash("podo123"),
            rol="Podologo",
            activo=True,
            clinica_id=clinica.id_clinica
        )
        auth_db.add(user)
        usuarios.append(user)
    
    # Recepcionistas
    for i in range(count // 2):
        user = SysUsuario(
            nombre_usuario=f"recepcion{i+1}",
            email=f"recepcion{i+1}@podoskin.mx",
            nombre=f"Recepcionista{i+1}",
            apellidos=f"Staff{i+1}",
            password_hash=get_password_hash("recep123"),
            rol="Recepcion",
            activo=True,
            clinica_id=clinica.id_clinica
        )
        auth_db.add(user)
        usuarios.append(user)
    
    auth_db.commit()
    print(f"  ✓ {len(usuarios)} usuarios creados")
    
    return clinica, usuarios


def seed_core_data(core_db, count=50):
    """Generar datos clínicos (pacientes, tratamientos, etc)."""
    print(f"\n🏥 Generando datos clínicos...")
    
    pacientes = []
    
    # Crear pacientes
    for i in range(count):
        # Generar datos realistas
        nombres = random.choice([
            "Juan", "María", "Carlos", "Ana", "Luis", "Laura", "José", "Carmen",
            "Miguel", "Rosa", "Pedro", "Isabel", "Francisco", "Elena", "Antonio"
        ])
        apellidos = random.choice([
            "García López", "Martínez Pérez", "Rodríguez Sánchez", "González Ramírez",
            "Fernández Torres", "López Flores", "Hernández Morales", "Díaz Castro"
        ])
        
        # Calcular edad aleatoria (18-80 años)
        edad_years = random.randint(18, 80)
        fecha_nac = date.today() - timedelta(days=edad_years * 365)
        
        # Peso y estatura realistas
        peso = Decimal(str(round(random.uniform(50.0, 110.0), 1)))
        estatura = Decimal(str(round(random.uniform(150.0, 190.0), 1)))
        
        paciente = Paciente(
            nombres=nombres,
            apellidos=apellidos,
            fecha_nacimiento=fecha_nac,
            sexo=random.choice(['M', 'F']),
            telefono=f"55{random.randint(10000000, 99999999)}",
            email=f"{nombres.lower()}.{apellidos.split()[0].lower()}@test.com",
            domicilio=f"Calle {random.randint(1, 100)}, Col. Centro, CDMX",
            peso_kg=peso,
            estatura_cm=estatura,
            ocupacion=random.choice(['Empleado', 'Estudiante', 'Profesionista', 'Comerciante', 'Hogar']),
            estado_civil=random.choice(['Soltero', 'Casado', 'Divorciado', 'Viudo']),
            activo=True
        )
        core_db.add(paciente)
        pacientes.append(paciente)
    
    core_db.commit()
    print(f"  ✓ {len(pacientes)} pacientes creados")
    
    # Crear tratamientos (70% de pacientes tienen al menos 1 tratamiento)
    tratamientos = []
    problemas = [
        'Onicomicosis', 'Uña encarnada', 'Callos y durezas', 'Pie diabético',
        'Verrugas plantares', 'Fascitis plantar', 'Espolón calcáneo',
        'Deformidades digitales', 'Hiperhidrosis', 'Pie plano'
    ]
    
    for paciente in random.sample(pacientes, int(count * 0.7)):
        num_tratamientos = random.randint(1, 3)
        for _ in range(num_tratamientos):
            problema = random.choice(problemas)
            days_ago = random.randint(0, 730)
            fecha_inicio = date.today() - timedelta(days=days_ago)
            
            tratamiento = Tratamiento(
                paciente_id=paciente.id_paciente,
                problema=problema,
                diagnostico=f"Diagnóstico clínico de {problema}",
                fecha_inicio=fecha_inicio,
                estado=random.choice(['activo', 'completado', 'en_pausa']),
                observaciones=f"Tratamiento para {problema}",
                activo=True
            )
            core_db.add(tratamiento)
            tratamientos.append(tratamiento)
    
    core_db.commit()
    print(f"  ✓ {len(tratamientos)} tratamientos creados")
    
    # Crear evoluciones clínicas (2-5 por tratamiento)
    evoluciones = []
    for tratamiento in tratamientos:
        num_evoluciones = random.randint(2, 5)
        for i in range(num_evoluciones):
            days_offset = i * random.randint(7, 30)
            fecha = tratamiento.fecha_inicio + timedelta(days=days_offset)
            
            evolucion = EvolucionClinica(
                tratamiento_id=tratamiento.id_tratamiento,
                fecha=fecha,
                subjetivo=f"Paciente refiere mejora progresiva. Visita {i+1}.",
                objetivo=f"Se observa mejoría en {tratamiento.problema}.",
                analisis=f"Evolución favorable del tratamiento.",
                plan=f"Continuar con protocolo establecido.",
                observaciones=""
            )
            core_db.add(evolucion)
            evoluciones.append(evolucion)
    
    core_db.commit()
    print(f"  ✓ {len(evoluciones)} evoluciones clínicas creadas")
    
    return pacientes, tratamientos


def seed_ops_data(ops_db, pacientes, count=50):
    """Generar datos operacionales (citas, podólogos, etc)."""
    print(f"\n📅 Generando datos operacionales...")
    
    # Crear métodos de pago
    metodos_pago = []
    for nombre in ['Efectivo', 'Tarjeta débito', 'Tarjeta crédito', 'Transferencia', 'PayPal']:
        metodo = MetodoPago(
            nombre=nombre,
            descripcion=f"Pago mediante {nombre}",
            activo=True
        )
        ops_db.add(metodo)
        metodos_pago.append(metodo)
    ops_db.commit()
    print(f"  ✓ {len(metodos_pago)} métodos de pago creados")
    
    # Crear podólogos
    podologos = []
    especialidades = [
        'Podología General', 'Pie Diabético', 'Biomecánica',
        'Podología Deportiva', 'Cirugía Podológica'
    ]
    
    for i in range(count // 10):  # Menos podólogos que pacientes
        podologo = Podologo(
            nombre=f"Dr. Carlos{i+1}",
            apellidos=f"Martínez{i+1}",
            especialidad=random.choice(especialidades),
            cedula_profesional=str(random.randint(10000000, 99999999)),
            telefono=f"55{random.randint(10000000, 99999999)}",
            email=f"doctor{i+1}@podoskin.mx",
            activo=True
        )
        ops_db.add(podologo)
        podologos.append(podologo)
    ops_db.commit()
    print(f"  ✓ {len(podologos)} podólogos creados")
    
    # Crear catálogo de servicios
    servicios = []
    servicios_data = [
        ('Consulta General', 60, 500),
        ('Corte de uñas especializado', 30, 300),
        ('Eliminación de callos', 45, 400),
        ('Tratamiento onicomicosis', 90, 800),
        ('Plantillas ortopédicas', 120, 1500),
        ('Láser para hongos', 60, 1000),
        ('Limpieza profunda', 75, 600),
        ('Masaje podológico', 45, 350),
    ]
    
    for nombre, duracion, precio in servicios_data:
        servicio = CatalogoServicio(
            nombre=nombre,
            descripcion=f"Servicio de {nombre}",
            duracion_minutos=duracion,
            precio=Decimal(str(precio)),
            activo=True
        )
        ops_db.add(servicio)
        servicios.append(servicio)
    ops_db.commit()
    print(f"  ✓ {len(servicios)} servicios creados")
    
    # Crear citas (distribuidas en los últimos 3 meses y próximos 2 meses)
    citas = []
    for i in range(count * 2):  # Más citas que pacientes
        paciente = random.choice(pacientes)
        podologo = random.choice(podologos)
        servicio = random.choice(servicios)
        
        # Fecha aleatoria en rango de -90 a +60 días
        days_offset = random.randint(-90, 60)
        fecha_hora = datetime.now() + timedelta(days=days_offset)
        # Ajustar a horario laboral (8am-6pm)
        fecha_hora = fecha_hora.replace(
            hour=random.randint(8, 18),
            minute=random.choice([0, 30]),
            second=0,
            microsecond=0
        )
        
        # Estado basado en si es pasada o futura
        if days_offset < 0:
            estado = random.choices(
                ['completada', 'cancelada', 'no_asistio'],
                weights=[0.8, 0.1, 0.1]
            )[0]
        else:
            estado = 'agendada'
        
        cita = Cita(
            paciente_id=paciente.id_paciente,
            podologo_id=podologo.id_podologo,
            servicio_id=servicio.id_servicio,
            fecha_hora=fecha_hora,
            estado=estado,
            duracion_minutos=servicio.duracion_minutos,
            motivo=f"Consulta de {servicio.nombre}",
            observaciones=""
        )
        ops_db.add(cita)
        citas.append(cita)
    ops_db.commit()
    print(f"  ✓ {len(citas)} citas creadas")
    
    # Crear prospectos
    prospectos = []
    for i in range(count // 5):
        prospecto = SolicitudProspecto(
            nombre=f"Prospecto{i+1}",
            apellidos=f"Interesado{i+1}",
            telefono=f"55{random.randint(10000000, 99999999)}",
            email=f"prospecto{i+1}@test.com",
            motivo_consulta=random.choice([
                'Dolor en los pies', 'Hongos en uñas', 'Callos',
                'Consulta general', 'Pie diabético'
            ]),
            fecha_contacto=datetime.now() - timedelta(days=random.randint(0, 90)),
            estado=random.choice(['nuevo', 'contactado', 'agendado', 'convertido', 'descartado']),
            observaciones="Contacto inicial"
        )
        ops_db.add(prospecto)
        prospectos.append(prospecto)
    ops_db.commit()
    print(f"  ✓ {len(prospectos)} prospectos creados")
    
    return podologos, servicios, citas, metodos_pago


def seed_finance_data(ops_db, citas, metodos_pago, count=50):
    """Generar datos financieros."""
    print(f"\n💰 Generando datos financieros...")
    
    transacciones = []
    pagos = []
    
    # Crear transacciones para citas completadas
    citas_completadas = [c for c in citas if c.estado == 'completada']
    
    for cita in random.sample(citas_completadas, min(len(citas_completadas), count)):
        # Transacción de ingreso
        monto = Decimal(str(random.uniform(300.0, 1500.0)))
        transaccion = Transaccion(
            cita_id=cita.id_cita,
            fecha=cita.fecha_hora.date(),
            tipo='ingreso',
            monto=monto,
            concepto=f"Pago de cita - {cita.motivo}",
            metodo_pago=random.choice(['Efectivo', 'Tarjeta', 'Transferencia'])
        )
        ops_db.add(transaccion)
        transacciones.append(transaccion)
        
        # Pago asociado
        ops_db.flush()  # Para obtener el ID de transacción
        pago = Pago(
            transaccion_id=transaccion.id_transaccion,
            cita_id=cita.id_cita,
            metodo_pago_id=random.choice(metodos_pago).id_metodo_pago,
            monto=monto,
            fecha=cita.fecha_hora.date(),
            estado='pagado'
        )
        ops_db.add(pago)
        pagos.append(pago)
    
    ops_db.commit()
    print(f"  ✓ {len(transacciones)} transacciones creadas")
    print(f"  ✓ {len(pagos)} pagos creados")
    
    # Crear gastos
    gastos = []
    categorias = {
        'Operativo': ['Material médico', 'Insumos de limpieza', 'Mantenimiento equipo'],
        'Administrativo': ['Renta de local', 'Servicios (luz, agua)', 'Seguros'],
        'Marketing': ['Publicidad Facebook', 'Folletos', 'Google Ads'],
        'Equipamiento': ['Nuevo equipo', 'Renovación mobiliario']
    }
    
    for i in range(count // 2):
        categoria = random.choice(list(categorias.keys()))
        concepto = random.choice(categorias[categoria])
        
        gasto = Gasto(
            concepto=concepto,
            monto=Decimal(str(random.uniform(500.0, 15000.0))),
            fecha=date.today() - timedelta(days=random.randint(0, 365)),
            categoria=categoria,
            observaciones=f"Gasto de {concepto}"
        )
        ops_db.add(gasto)
        gastos.append(gasto)
    
    ops_db.commit()
    print(f"  ✓ {len(gastos)} gastos creados")
    
    return transacciones, pagos, gastos


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Generar datos de prueba para PodoSkin')
    parser.add_argument('--count', type=int, default=50, help='Cantidad de registros por entidad')
    parser.add_argument('--clean', action='store_true', help='Limpiar datos existentes primero')
    args = parser.parse_args()
    
    print("="*80)
    print("🌱 GENERADOR DE DATOS DE PRUEBA - PODOSKIN")
    print("="*80)
    print(f"📊 Cantidad de registros: {args.count}")
    print(f"🧹 Limpiar primero: {'Sí' if args.clean else 'No'}")
    print("="*80)
    
    try:
        # Crear sesiones
        auth_db, core_db, ops_db = create_sessions()
        
        # Limpiar si se solicita
        if args.clean:
            clean_databases(auth_db, core_db, ops_db)
        
        # Generar datos
        clinica, usuarios = seed_auth_data(auth_db, args.count // 5)
        pacientes, tratamientos = seed_core_data(core_db, args.count)
        podologos, servicios, citas, metodos_pago = seed_ops_data(ops_db, pacientes, args.count)
        transacciones, pagos, gastos = seed_finance_data(ops_db, citas, metodos_pago, args.count)
        
        # Resumen
        print("\n" + "="*80)
        print("✅ GENERACIÓN COMPLETADA")
        print("="*80)
        print(f"  🔐 Usuarios: {len(usuarios)}")
        print(f"  🏥 Pacientes: {len(pacientes)}")
        print(f"  💊 Tratamientos: {len(tratamientos)}")
        print(f"  👨‍⚕️ Podólogos: {len(podologos)}")
        print(f"  📋 Servicios: {len(servicios)}")
        print(f"  📅 Citas: {len(citas)}")
        print(f"  💰 Transacciones: {len(transacciones)}")
        print(f"  💳 Pagos: {len(pagos)}")
        print(f"  📊 Gastos: {len(gastos)}")
        print("="*80)
        
        print("\n🔑 Credenciales de prueba:")
        print("  👤 Admin: admin / admin123")
        print("  👨‍⚕️ Podólogo: podologo1 / podo123")
        print("  👥 Recepción: recepcion1 / recep123")
        print("\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        auth_db.close()
        core_db.close()
        ops_db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
