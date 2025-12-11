#!/usr/bin/env python3
"""
Script de Limpieza de Base de Datos
====================================

Este script limpia y formatea las bases de datos de prueba.

ADVERTENCIA: ¡Este script BORRA TODOS LOS DATOS!
Solo usar en entornos de desarrollo/testing.

Uso:
    python backend/tests/scripts/clean_database.py --confirm
    python backend/tests/scripts/clean_database.py --reset  # Limpia y recrea schemas
    
Opciones:
    --confirm : Confirmar limpieza (requerido)
    --reset   : Borrar y recrear schemas completos
    --db TYPE : Base de datos específica (auth|core|ops|all, default: all)
"""

import os
import sys
import argparse

# Agregar path del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Importar modelos para recrear
from backend.schemas.auth.models import Base as AuthBase
from backend.schemas.core.models import Base as CoreBase
from backend.schemas.ops.models import Base as OpsBase
from backend.schemas.finance.models import Base as FinanceBase


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

AUTH_DB_URL = os.getenv("AUTH_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_auth_db")
CORE_DB_URL = os.getenv("CORE_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_core_db")
OPS_DB_URL = os.getenv("OPS_DB_URL", "postgresql://podoskin:podoskin123@localhost:5432/clinica_ops_db")


# =============================================================================
# FUNCIONES DE LIMPIEZA
# =============================================================================

def clean_auth_db(engine, reset=False):
    """Limpiar base de datos de autenticación."""
    print("\n🔐 Limpiando base de datos AUTH...")
    
    if reset:
        print("  🔄 Modo RESET: Borrando y recreando schema...")
        with engine.connect() as conn:
            # Para PostgreSQL, borrar schema completo
            conn.execute(text("DROP SCHEMA IF EXISTS auth CASCADE"))
            conn.execute(text("CREATE SCHEMA auth"))
            conn.commit()
        
        # Recrear tablas
        AuthBase.metadata.create_all(bind=engine)
        print("  ✅ Schema 'auth' recreado")
    else:
        print("  🧹 Limpiando tablas...")
        with engine.connect() as conn:
            # Orden inverso para respetar FKs
            tables = ['audit_logs', 'sys_usuarios', 'clinicas']
            for table in tables:
                try:
                    conn.execute(text(f"DELETE FROM auth.{table}"))
                    print(f"    ✓ {table}")
                except Exception as e:
                    print(f"    ⚠️  {table}: {e}")
            conn.commit()
        print("  ✅ Tablas limpiadas")


def clean_core_db(engine, reset=False):
    """Limpiar base de datos core."""
    print("\n🏥 Limpiando base de datos CORE...")
    
    if reset:
        print("  🔄 Modo RESET: Borrando y recreando schema...")
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS clinic CASCADE"))
            conn.execute(text("CREATE SCHEMA clinic"))
            conn.commit()
        
        CoreBase.metadata.create_all(bind=engine)
        print("  ✅ Schema 'clinic' recreado")
    else:
        print("  🧹 Limpiando tablas...")
        with engine.connect() as conn:
            # Orden: hijos primero, padres después
            tables = [
                'evidencias_fotograficas',
                'evoluciones_clinicas',
                'conversaciones_ia',
                'antecedentes_familiares',
                'antecedentes_personales',
                'suplementos',
                'medicamentos',
                'alergias',
                'tratamientos',
                'pacientes'
            ]
            for table in tables:
                try:
                    conn.execute(text(f"DELETE FROM clinic.{table}"))
                    print(f"    ✓ {table}")
                except Exception as e:
                    print(f"    ⚠️  {table}: {e}")
            conn.commit()
        print("  ✅ Tablas limpiadas")


def clean_ops_db(engine, reset=False):
    """Limpiar base de datos ops."""
    print("\n📅 Limpiando base de datos OPS...")
    
    if reset:
        print("  🔄 Modo RESET: Borrando y recreando schemas...")
        with engine.connect() as conn:
            conn.execute(text("DROP SCHEMA IF EXISTS ops CASCADE"))
            conn.execute(text("DROP SCHEMA IF EXISTS finance CASCADE"))
            conn.execute(text("CREATE SCHEMA ops"))
            conn.execute(text("CREATE SCHEMA finance"))
            conn.commit()
        
        OpsBase.metadata.create_all(bind=engine)
        FinanceBase.metadata.create_all(bind=engine)
        print("  ✅ Schemas 'ops' y 'finance' recreados")
    else:
        print("  🧹 Limpiando tablas OPS...")
        with engine.connect() as conn:
            ops_tables = [
                'citas',
                'solicitudes_prospectos',
                'catalogo_servicios',
                'podologos'
            ]
            for table in ops_tables:
                try:
                    conn.execute(text(f"DELETE FROM ops.{table}"))
                    print(f"    ✓ {table}")
                except Exception as e:
                    print(f"    ⚠️  {table}: {e}")
            
            print("  🧹 Limpiando tablas FINANCE...")
            finance_tables = [
                'pagos',
                'gastos',
                'transacciones',
                'metodos_pago'
            ]
            for table in finance_tables:
                try:
                    conn.execute(text(f"DELETE FROM finance.{table}"))
                    print(f"    ✓ {table}")
                except Exception as e:
                    print(f"    ⚠️  {table}: {e}")
            
            conn.commit()
        print("  ✅ Tablas limpiadas")


def reset_sequences(engine, schema_name):
    """Reiniciar secuencias de IDs (solo PostgreSQL)."""
    print(f"  🔢 Reiniciando secuencias en schema '{schema_name}'...")
    with engine.connect() as conn:
        # Obtener todas las secuencias del schema
        result = conn.execute(text(f"""
            SELECT sequence_name 
            FROM information_schema.sequences 
            WHERE sequence_schema = '{schema_name}'
        """))
        
        for row in result:
            seq_name = row[0]
            try:
                conn.execute(text(f"ALTER SEQUENCE {schema_name}.{seq_name} RESTART WITH 1"))
                print(f"    ✓ {seq_name}")
            except Exception as e:
                print(f"    ⚠️  {seq_name}: {e}")
        
        conn.commit()


# =============================================================================
# FUNCIONES DE VERIFICACIÓN
# =============================================================================

def verify_clean(engine, schema_name, tables):
    """Verificar que las tablas estén vacías."""
    print(f"\n🔍 Verificando limpieza en '{schema_name}'...")
    
    all_empty = True
    with engine.connect() as conn:
        for table in tables:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {schema_name}.{table}"))
                count = result.scalar()
                if count > 0:
                    print(f"  ⚠️  {table}: {count} registros restantes")
                    all_empty = False
                else:
                    print(f"  ✓ {table}: vacía")
            except Exception as e:
                print(f"  ⚠️  {table}: {e}")
    
    return all_empty


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Limpiar y formatear bases de datos de PodoSkin',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--confirm',
        action='store_true',
        help='Confirmar limpieza (requerido para evitar borrados accidentales)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Borrar y recrear schemas completos'
    )
    parser.add_argument(
        '--db',
        choices=['auth', 'core', 'ops', 'all'],
        default='all',
        help='Base de datos específica a limpiar'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Solo verificar estado de las tablas sin limpiar'
    )
    
    args = parser.parse_args()
    
    # Validación de seguridad
    if not args.confirm and not args.verify:
        print("❌ ERROR: Debe usar --confirm para ejecutar la limpieza")
        print("   Esto es una medida de seguridad para evitar borrados accidentales.")
        print("\nUso:")
        print("  python clean_database.py --confirm          # Limpiar todas las BDs")
        print("  python clean_database.py --confirm --reset  # Recrear schemas")
        print("  python clean_database.py --verify           # Solo verificar")
        return 1
    
    print("="*80)
    if args.verify:
        print("🔍 VERIFICACIÓN DE ESTADO DE BASES DE DATOS")
    elif args.reset:
        print("⚠️  LIMPIEZA Y RESET COMPLETO DE BASES DE DATOS")
    else:
        print("🧹 LIMPIEZA DE BASES DE DATOS")
    print("="*80)
    print(f"🎯 Target: {args.db.upper()}")
    print(f"🔄 Modo: {'VERIFY' if args.verify else ('RESET' if args.reset else 'CLEAN')}")
    print("="*80)
    
    # Advertencia final
    if not args.verify:
        print("\n⚠️  ADVERTENCIA: Esta operación BORRARÁ TODOS LOS DATOS")
        print("   Solo continuar si está seguro.")
        response = input("\n¿Desea continuar? (escriba 'SI' para confirmar): ")
        if response != 'SI':
            print("❌ Operación cancelada")
            return 0
    
    try:
        # Crear engines
        auth_engine = create_engine(AUTH_DB_URL)
        core_engine = create_engine(CORE_DB_URL)
        ops_engine = create_engine(OPS_DB_URL)
        
        if args.verify:
            # Solo verificar
            if args.db in ['auth', 'all']:
                verify_clean(auth_engine, 'auth', ['clinicas', 'sys_usuarios', 'audit_logs'])
            
            if args.db in ['core', 'all']:
                verify_clean(core_engine, 'clinic', [
                    'pacientes', 'tratamientos', 'evoluciones_clinicas', 'evidencias_fotograficas'
                ])
            
            if args.db in ['ops', 'all']:
                verify_clean(ops_engine, 'ops', ['podologos', 'catalogo_servicios', 'citas'])
                verify_clean(ops_engine, 'finance', ['metodos_pago', 'transacciones', 'pagos', 'gastos'])
        
        else:
            # Limpiar
            if args.db in ['auth', 'all']:
                clean_auth_db(auth_engine, args.reset)
                if args.reset:
                    reset_sequences(auth_engine, 'auth')
            
            if args.db in ['core', 'all']:
                clean_core_db(core_engine, args.reset)
                if args.reset:
                    reset_sequences(core_engine, 'clinic')
            
            if args.db in ['ops', 'all']:
                clean_ops_db(ops_engine, args.reset)
                if args.reset:
                    reset_sequences(ops_engine, 'ops')
                    reset_sequences(ops_engine, 'finance')
            
            print("\n" + "="*80)
            print("✅ LIMPIEZA COMPLETADA")
            print("="*80)
            
            if args.reset:
                print("\n📝 Las tablas han sido recreadas vacías")
                print("   Ejecutar seed_test_data.py para poblar con datos de prueba")
        
        # Cerrar conexiones
        auth_engine.dispose()
        core_engine.dispose()
        ops_engine.dispose()
        
        print("\n")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
