"""
Migration Script: Add codigo_interno to Clinica and SysUsuario

Este script agrega los campos codigo_interno a las tablas clinicas y sys_usuarios
para soportar IDs estructurados (RENO-1213-00001).

Ejecutar:
    python backend/migrations/add_codigo_interno.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy import text
from backend.api.deps.database import get_auth_db
from backend.api.core.config import get_settings

def run_migration():
    """Ejecuta la migración para agregar codigo_interno"""
    
    settings = get_settings()
    db = next(get_auth_db())
    
    try:
        print("🔧 Iniciando migración: add_codigo_interno...")
        
        # 1. Agregar columna codigo_interno a clinicas
        print("   [1/4] Agregando codigo_interno a auth.clinicas...")
        db.execute(text("""
            ALTER TABLE auth.clinicas 
            ADD COLUMN IF NOT EXISTS codigo_interno VARCHAR(20) UNIQUE;
        """))
        
        # Crear índice
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_clinicas_codigo_interno 
            ON auth.clinicas(codigo_interno);
        """))
        
        # 2. Agregar columna codigo_interno a sys_usuarios
        print("   [2/4] Agregando codigo_interno a auth.sys_usuarios...")
        db.execute(text("""
            ALTER TABLE auth.sys_usuarios 
            ADD COLUMN IF NOT EXISTS codigo_interno VARCHAR(20) UNIQUE;
        """))
        
        # Crear índice
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_sysusuarios_codigo_interno 
            ON auth.sys_usuarios(codigo_interno);
        """))
        
        # 3. Verificar que las columnas existen
        print("   [3/4] Verificando columnas...")
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'auth' 
            AND table_name = 'clinicas' 
            AND column_name = 'codigo_interno';
        """))
        
        if not result.fetchone():
            raise Exception("❌ Fallo al crear codigo_interno en clinicas")
        
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'auth' 
            AND table_name = 'sys_usuarios' 
            AND column_name = 'codigo_interno';
        """))
        
        if not result.fetchone():
            raise Exception("❌ Fallo al crear codigo_interno en sys_usuarios")
        
        # 4. Commit
        print("   [4/4] Guardando cambios...")
        db.commit()
        
        print("✅ Migración completada exitosamente!")
        print("\n📋 Resumen:")
        print("   • Columna 'codigo_interno' agregada a auth.clinicas")
        print("   • Columna 'codigo_interno' agregada a auth.sys_usuarios")
        print("   • Índices creados para búsqueda rápida")
        print("\n⚠️  NOTA: Los registros existentes tendrán codigo_interno = NULL")
        print("   Ejecuta el seed script para generar códigos automáticamente.")
        
    except Exception as e:
        print(f"❌ Error en migración: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()
