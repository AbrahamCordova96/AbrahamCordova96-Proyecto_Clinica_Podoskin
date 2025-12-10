"""
SQL Executor Tool - Ejecución segura de consultas SQL
=====================================================

Proporciona ejecución segura de consultas SQL con:
- Detección automática de base de datos objetivo
- Validación de queries (solo SELECT para lecturas)
- Timeout configurable
- Límite de resultados
- Logging de consultas

Usa las conexiones centralizadas de deps/database.py (Decisión 2).
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Literal
from contextlib import contextmanager
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from backend.api.core.config import get_settings
from backend.api.deps.database import get_auth_db, get_core_db, get_ops_db
from backend.agents.state import (
    DatabaseTarget, 
    ExecutionResult, 
    SQLQuery,
    ErrorType,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONSTANTES Y PATRONES
# =============================================================================

# Palabras clave peligrosas que NO deben ejecutarse desde el agente
FORBIDDEN_KEYWORDS = [
    "DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE",
    "EXECUTE", "EXEC", "sp_", "xp_", "--", "/*", "*/", ";"
]

# Tablas sensibles que requieren permisos especiales
SENSITIVE_TABLES = {
    "auth.sys_usuarios": ["Admin"],           # Solo Admin
    "auth.audit_logs": ["Admin", "Podologo"], # Admin y Podologo
    "finance.transacciones": ["Admin"],       # Solo Admin
}

# Mapeo de esquemas a bases de datos
SCHEMA_TO_DB: Dict[str, DatabaseTarget] = {
    "auth": DatabaseTarget.AUTH,
    "clinic": DatabaseTarget.CORE,
    "ops": DatabaseTarget.OPS,
    "finance": DatabaseTarget.OPS,  # Finance está en ops_db
}


# =============================================================================
# FUNCIONES DE VALIDACIÓN
# =============================================================================

def detect_target_database(sql: str, tables: List[str] = None) -> DatabaseTarget:
    """
    Detecta automáticamente la base de datos objetivo basándose en la query.
    
    Args:
        sql: Query SQL a analizar
        tables: Lista de tablas involucradas (opcional)
        
    Returns:
        DatabaseTarget correspondiente
    """
    sql_lower = sql.lower()
    
    # Detectar por esquema explícito en la query
    for schema, db in SCHEMA_TO_DB.items():
        if f"{schema}." in sql_lower:
            return db
    
    # Detectar por tablas conocidas
    table_db_map = {
        # Auth DB
        "sys_usuarios": DatabaseTarget.AUTH,
        "clinicas": DatabaseTarget.AUTH,
        "audit_logs": DatabaseTarget.AUTH,
        # Core DB
        "pacientes": DatabaseTarget.CORE,
        "tratamientos": DatabaseTarget.CORE,
        "evoluciones": DatabaseTarget.CORE,
        "evidencias": DatabaseTarget.CORE,
        # Ops DB
        "podologos": DatabaseTarget.OPS,
        "citas": DatabaseTarget.OPS,
        "catalogo_servicios": DatabaseTarget.OPS,
        "prospectos": DatabaseTarget.OPS,
        "pagos": DatabaseTarget.OPS,
        "transacciones": DatabaseTarget.OPS,
        "gastos": DatabaseTarget.OPS,
    }
    
    for table, db in table_db_map.items():
        if table in sql_lower:
            return db
    
    # Por defecto, usar Core (datos clínicos)
    return DatabaseTarget.CORE


def validate_query_safety(sql: str, user_role: str) -> Tuple[bool, Optional[str]]:
    """
    Valida que la query sea segura para ejecutar.
    
    Args:
        sql: Query SQL a validar
        user_role: Rol del usuario que ejecuta
        
    Returns:
        Tuple (es_valida, mensaje_error)
    """
    sql_upper = sql.upper().strip()
    
    # 1. Verificar palabras clave prohibidas
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword.upper() in sql_upper:
            return False, f"Operación no permitida: {keyword}"
    
    # 2. Solo permitir SELECT para consultas de lectura
    if not sql_upper.startswith("SELECT"):
        return False, "Solo se permiten consultas de lectura (SELECT)"
    
    # 3. Verificar acceso a tablas sensibles
    sql_lower = sql.lower()
    for table, allowed_roles in SENSITIVE_TABLES.items():
        if table in sql_lower and user_role not in allowed_roles:
            return False, f"Sin permisos para acceder a {table}"
    
    # 4. Verificar que no haya subqueries peligrosas
    if "into" in sql_lower or "outfile" in sql_lower:
        return False, "Cláusulas INTO/OUTFILE no permitidas"
    
    return True, None


def sanitize_query(sql: str) -> str:
    """
    Limpia la query de caracteres potencialmente peligrosos.
    
    Args:
        sql: Query SQL a limpiar
        
    Returns:
        Query sanitizada
    """
    # Remover comentarios
    sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
    
    # Remover múltiples espacios
    sql = re.sub(r'\s+', ' ', sql).strip()
    
    # Remover punto y coma final (prevenir múltiples statements)
    sql = sql.rstrip(';')
    
    return sql


# =============================================================================
# OBTENCIÓN DE SESIONES DE BD
# =============================================================================

def get_db_session(target: DatabaseTarget) -> Session:
    """
    Obtiene una sesión de base de datos según el target.
    
    Usa los generadores centralizados de deps/database.py (Decisión 2).
    
    Args:
        target: DatabaseTarget indicando qué BD usar
        
    Returns:
        Session de SQLAlchemy
    """
    if target == DatabaseTarget.AUTH:
        return next(get_auth_db())
    elif target == DatabaseTarget.CORE:
        return next(get_core_db())
    elif target == DatabaseTarget.OPS:
        return next(get_ops_db())
    else:
        # Por defecto, Core
        return next(get_core_db())


# =============================================================================
# EJECUTOR PRINCIPAL
# =============================================================================

def execute_safe_query(
    sql_query: SQLQuery,
    user_role: str,
    max_results: int = None,
    timeout_seconds: int = None,
) -> ExecutionResult:
    """
    Ejecuta una consulta SQL de forma segura.
    
    Esta es la función principal que los nodos del agente deben usar.
    
    Args:
        sql_query: SQLQuery con la consulta y metadata
        user_role: Rol del usuario que ejecuta
        max_results: Límite de filas (default de config)
        timeout_seconds: Timeout en segundos (default de config)
        
    Returns:
        ExecutionResult con los datos o error
    """
    max_results = max_results or settings.AGENT_MAX_RESULTS
    timeout_seconds = timeout_seconds or settings.AGENT_TIMEOUT_SECONDS
    
    start_time = time.time()
    
    # 1. Sanitizar query
    clean_sql = sanitize_query(sql_query.query)
    
    # 2. Validar seguridad
    is_valid, error_msg = validate_query_safety(clean_sql, user_role)
    if not is_valid:
        logger.warning(f"Query rechazada por seguridad: {error_msg}")
        return ExecutionResult(
            success=False,
            error_message=error_msg,
            execution_time_ms=(time.time() - start_time) * 1000,
        )
    
    # 3. Detectar BD target si no está especificada
    target_db = sql_query.target_db or detect_target_database(clean_sql)
    
    # 4. Agregar LIMIT si no existe
    if "limit" not in clean_sql.lower():
        clean_sql = f"{clean_sql} LIMIT {max_results}"
    
    # 5. Ejecutar query
    db = None
    try:
        db = get_db_session(target_db)
        
        # Log de query si está habilitado
        if settings.AGENT_LOG_QUERIES:
            logger.info(f"Ejecutando query en {target_db.value}: {clean_sql[:200]}...")
        
        # Ejecutar con parámetros
        result = db.execute(
            text(clean_sql),
            sql_query.params or {}
        )
        
        # Obtener columnas y filas
        columns = list(result.keys()) if result.returns_rows else []
        rows = [dict(row._mapping) for row in result.fetchall()] if result.returns_rows else []
        
        execution_time = (time.time() - start_time) * 1000
        
        logger.info(f"Query exitosa: {len(rows)} filas en {execution_time:.2f}ms")
        
        return ExecutionResult(
            success=True,
            data=rows,
            row_count=len(rows),
            columns=columns,
            execution_time_ms=execution_time,
        )
        
    except OperationalError as e:
        logger.error(f"Error de conexión: {str(e)}")
        return ExecutionResult(
            success=False,
            error_message="Error de conexión a la base de datos",
            execution_time_ms=(time.time() - start_time) * 1000,
        )
        
    except SQLAlchemyError as e:
        logger.error(f"Error SQL: {str(e)}")
        return ExecutionResult(
            success=False,
            error_message=f"Error en la consulta: {str(e)[:100]}",
            execution_time_ms=(time.time() - start_time) * 1000,
        )
        
    except Exception as e:
        logger.exception(f"Error inesperado ejecutando query")
        return ExecutionResult(
            success=False,
            error_message="Error interno al procesar la consulta",
            execution_time_ms=(time.time() - start_time) * 1000,
        )
        
    finally:
        if db:
            db.close()


# =============================================================================
# FUNCIONES AUXILIARES PARA INTROSPECCIÓN
# =============================================================================

def get_table_columns(table_name: str, schema: str = "clinic") -> List[Dict[str, Any]]:
    """
    Obtiene las columnas de una tabla con sus tipos.
    
    Args:
        table_name: Nombre de la tabla
        schema: Esquema (auth, clinic, ops, finance)
        
    Returns:
        Lista de dicts con información de columnas
    """
    target = SCHEMA_TO_DB.get(schema, DatabaseTarget.CORE)
    
    sql = """
    SELECT 
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM information_schema.columns
    WHERE table_schema = :schema
      AND table_name = :table
    ORDER BY ordinal_position
    """
    
    query = SQLQuery(
        query=sql,
        params={"schema": schema, "table": table_name},
        target_db=target,
    )
    
    result = execute_safe_query(query, user_role="Admin")
    return result.data if result.success else []


def get_schema_tables(schema: str = "clinic") -> List[str]:
    """
    Obtiene la lista de tablas de un esquema.
    
    Args:
        schema: Nombre del esquema
        
    Returns:
        Lista de nombres de tablas
    """
    target = SCHEMA_TO_DB.get(schema, DatabaseTarget.CORE)
    
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = :schema
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    
    query = SQLQuery(
        query=sql,
        params={"schema": schema},
        target_db=target,
    )
    
    result = execute_safe_query(query, user_role="Admin")
    return [row["table_name"] for row in result.data] if result.success else []
