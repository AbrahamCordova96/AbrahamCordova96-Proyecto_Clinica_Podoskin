"""
Schema Info Tool - Información de esquema de BD para el agente
==============================================================

Proporciona al agente contexto sobre:
- Tablas disponibles y sus columnas
- Relaciones entre tablas
- Ejemplos de valores para campos clave

Esta información se usa para generar queries SQL correctas.
"""

import logging
from typing import Dict, Any, List, Optional
from functools import lru_cache

from sqlalchemy import text

from backend.api.deps.database import get_auth_db, get_core_db, get_ops_db

logger = logging.getLogger(__name__)


# =============================================================================
# METADATA ESTÁTICA DEL ESQUEMA (para consultas rápidas)
# =============================================================================

# Descripción de tablas para el prompt del LLM
# IMPORTANTE: Usa deleted_at IS NULL para filtrar registros activos (soft delete)
SCHEMA_DESCRIPTIONS: Dict[str, Dict[str, Any]] = {
    # === AUTH DB ===
    "auth.clinicas": {
        "description": "Clínicas registradas en el sistema (multi-tenant)",
        "main_columns": ["id_clinica", "nombre", "direccion", "telefono"],
        "soft_delete": "deleted_at",  # deleted_at IS NULL = activo
    },
    "auth.sys_usuarios": {
        "description": "Usuarios del sistema con sus credenciales y roles",
        "main_columns": ["id_usuario", "username", "email", "rol", "activo"],
        "common_filters": ["rol", "activo"],
        "sensitive": True,
    },
    "auth.audit_logs": {
        "description": "Registro de auditoría de cambios en el sistema",
        "main_columns": ["id", "tabla_afectada", "accion", "usuario_id", "timestamp"],
        "common_filters": ["tabla_afectada", "accion", "usuario_id"],
        "sensitive": True,
    },
    
    # === CORE DB ===
    "clinic.pacientes": {
        "description": "Expedientes de pacientes con datos personales",
        "main_columns": ["id_paciente", "nombres", "apellidos", "fecha_nacimiento", "sexo", "telefono", "email", "domicilio"],
        "searchable_columns": ["nombres", "apellidos", "telefono", "email"],
        "soft_delete": "deleted_at",  # deleted_at IS NULL = activo
        "example_query": "SELECT * FROM clinic.pacientes WHERE nombres ILIKE '%Juan%' AND deleted_at IS NULL",
    },
    "clinic.tratamientos": {
        "description": "Carpetas de problemas/tratamientos por paciente",
        "main_columns": ["id_tratamiento", "paciente_id", "motivo_consulta_principal", "diagnostico_inicial", "estado_tratamiento", "fecha_inicio", "plan_general"],
        "common_filters": ["estado_tratamiento", "paciente_id"],
        "valid_states": ["En Curso", "Alta", "Pausado", "Abandonado"],
        "soft_delete": "deleted_at",
        "relations": {"paciente_id": "clinic.pacientes.id_paciente"},
    },
    "clinic.evoluciones_clinicas": {
        "description": "Notas clínicas SOAP de cada visita",
        "main_columns": ["id_evolucion", "tratamiento_id", "podologo_id", "fecha_consulta", "subjetivo", "objetivo", "analisis", "plan"],
        "common_filters": ["tratamiento_id", "podologo_id", "fecha_consulta"],
        "soft_delete": "deleted_at",
        "relations": {
            "tratamiento_id": "clinic.tratamientos.id_tratamiento",
            "podologo_id": "ops.podologos.id_podologo",
        },
    },
    "clinic.evidencias": {
        "description": "Fotos clínicas asociadas a evoluciones",
        "main_columns": ["id_evidencia", "evolucion_id", "tipo", "url", "descripcion"],
        "common_filters": ["evolucion_id", "tipo"],
        "soft_delete": "deleted_at",
    },
    
    # === OPS DB ===
    "ops.podologos": {
        "description": "Personal clínico (podólogos)",
        "main_columns": ["id_podologo", "nombre_completo", "cedula_profesional", "especialidad", "activo"],
        "searchable_columns": ["nombre_completo"],
        "common_filters": ["activo", "especialidad"],
        "soft_delete": "deleted_at",
    },
    "ops.citas": {
        "description": "Agenda de citas de la clínica",
        "main_columns": ["id_cita", "paciente_id", "podologo_id", "servicio_id", "fecha_cita", "hora_inicio", "hora_fin", "status", "notas_agendamiento"],
        "common_filters": ["status", "fecha_cita", "podologo_id", "paciente_id"],
        "valid_status": ["Pendiente", "Confirmada", "En Sala", "Realizada", "Cancelada", "No Asistió"],
        "soft_delete": "deleted_at",
        "relations": {
            "paciente_id": "clinic.pacientes.id_paciente",
            "podologo_id": "ops.podologos.id_podologo",
            "servicio_id": "ops.catalogo_servicios.id_servicio",
        },
    },
    "ops.catalogo_servicios": {
        "description": "Catálogo de servicios ofrecidos con precios",
        "main_columns": ["id_servicio", "nombre_servicio", "descripcion", "precio_base", "duracion_minutos", "requiere_seguimiento", "activo"],
        "searchable_columns": ["nombre_servicio"],
        "common_filters": ["activo"],
    },
    "ops.solicitudes_prospectos": {
        "description": "Leads/prospectos que solicitan información",
        "main_columns": ["id_prospecto", "nombre", "telefono", "email", "motivo_consulta", "estado"],
        "common_filters": ["estado"],
    },
    
    # === FINANCE (en OPS DB) ===
    "finance.metodos_pago": {
        "description": "Métodos de pago disponibles",
        "main_columns": ["id_metodo", "nombre", "activo"],
        "common_filters": ["activo"],
        "searchable_columns": ["nombre"],
    },
    "finance.pagos": {
        "description": "Pagos recibidos de pacientes",
        "main_columns": ["id_pago", "paciente_id", "fecha_emision", "total_facturado", "monto_pagado", "saldo_pendiente", "status_pago"],
        "common_filters": ["status_pago", "fecha_emision"],
        "valid_status": ["Pendiente", "Parcial", "Pagado", "Cancelado"],
        "soft_delete": "deleted_at",
        "sensitive": True,
    },
    "finance.transacciones": {
        "description": "Registro detallado de transacciones financieras",
        "main_columns": ["id_transaccion", "pago_id", "monto", "metodo_pago_id", "fecha", "recibido_por", "notas"],
        "common_filters": ["metodo_pago_id", "fecha", "pago_id"],
        "relations": {
            "pago_id": "finance.pagos.id_pago",
            "metodo_pago_id": "finance.metodos_pago.id_metodo",
        },
        "sensitive": True,
    },
    "finance.gastos": {
        "description": "Gastos operativos de la clínica",
        "main_columns": ["id_gasto", "categoria_id", "proveedor_id", "monto", "iva", "monto_total", "concepto", "fecha_gasto", "fecha_pago", "status"],
        "common_filters": ["categoria_id", "fecha_gasto", "status", "proveedor_id"],
        "valid_status": ["Pendiente", "Pagado", "Cancelado"],
        "soft_delete": "deleted_at",
        "relations": {
            "categoria_id": "finance.categorias_gasto.id_categoria",
            "proveedor_id": "finance.proveedores.id_proveedor",
            "metodo_pago_id": "finance.metodos_pago.id_metodo",
        },
        "sensitive": True,
    },
}


# Mapeo de entidades del lenguaje natural a tablas
ENTITY_TO_TABLE = {
    # Pacientes
    "paciente": "clinic.pacientes",
    "pacientes": "clinic.pacientes",
    "cliente": "clinic.pacientes",
    "clientes": "clinic.pacientes",
    
    # Tratamientos
    "tratamiento": "clinic.tratamientos",
    "tratamientos": "clinic.tratamientos",
    "problema": "clinic.tratamientos",
    "problemas": "clinic.tratamientos",
    "padecimiento": "clinic.tratamientos",
    
    # Evoluciones (nombre real: evoluciones_clinicas)
    "evolución": "clinic.evoluciones_clinicas",
    "evoluciones": "clinic.evoluciones_clinicas",
    "nota": "clinic.evoluciones_clinicas",
    "notas": "clinic.evoluciones_clinicas",
    "visita": "clinic.evoluciones_clinicas",
    "visitas": "clinic.evoluciones_clinicas",
    "consulta": "clinic.evoluciones_clinicas",
    "consultas": "clinic.evoluciones_clinicas",
    
    # Citas
    "cita": "ops.citas",
    "citas": "ops.citas",
    "agenda": "ops.citas",
    "turno": "ops.citas",
    "turnos": "ops.citas",
    
    # Podólogos
    "podólogo": "ops.podologos",
    "podologo": "ops.podologos",
    "podólogos": "ops.podologos",
    "podologos": "ops.podologos",
    "doctor": "ops.podologos",
    "doctores": "ops.podologos",
    "especialista": "ops.podologos",
    
    # Servicios
    "servicio": "ops.catalogo_servicios",
    "servicios": "ops.catalogo_servicios",
    "procedimiento": "ops.catalogo_servicios",
    
    # Prospectos
    "prospecto": "ops.solicitudes_prospectos",
    "prospectos": "ops.solicitudes_prospectos",
    "lead": "ops.solicitudes_prospectos",
    "leads": "ops.solicitudes_prospectos",
    
    # Finanzas
    "pago": "finance.pagos",
    "pagos": "finance.pagos",
    "transacción": "finance.transacciones",
    "transacciones": "finance.transacciones",
    "gasto": "finance.gastos",
    "gastos": "finance.gastos",
}


# =============================================================================
# FUNCIONES DE CONSULTA DE ESQUEMA
# =============================================================================

def get_schema_context_for_prompt() -> str:
    """
    Genera un contexto de esquema formateado para el prompt del LLM.
    
    Returns:
        String con descripción de tablas para incluir en el prompt
    """
    lines = [
        "## Esquema de Base de Datos\n",
        "### IMPORTANTE: Soft Delete",
        "La mayoría de tablas usan `deleted_at IS NULL` para filtrar registros activos.",
        "NO uses `WHERE activo = true` en pacientes o tratamientos.",
        "Usa: `WHERE deleted_at IS NULL` para obtener solo registros activos.\n",
    ]
    
    current_db = None
    for table_name, info in SCHEMA_DESCRIPTIONS.items():
        schema = table_name.split(".")[0]
        
        # Header por base de datos
        if schema == "auth" and current_db != "auth":
            lines.append("\n### Base de Datos: Autenticación (auth)")
            current_db = "auth"
        elif schema == "clinic" and current_db != "clinic":
            lines.append("\n### Base de Datos: Clínica (core)")
            current_db = "clinic"
        elif schema == "ops" and current_db != "ops":
            lines.append("\n### Base de Datos: Operaciones (ops)")
            current_db = "ops"
        elif schema == "finance" and current_db != "finance":
            lines.append("\n### Base de Datos: Finanzas (en ops)")
            current_db = "finance"
        
        # Info de tabla
        lines.append(f"\n**{table_name}**: {info['description']}")
        lines.append(f"  - Columnas: {', '.join(info['main_columns'])}")
        
        if info.get("searchable_columns"):
            lines.append(f"  - Búsqueda por: {', '.join(info['searchable_columns'])}")
        
        if info.get("soft_delete"):
            lines.append(f"  - Soft delete: usa `{info['soft_delete']} IS NULL` para activos")
        
        if info.get("valid_states"):
            lines.append(f"  - Estados válidos: {', '.join(info['valid_states'])}")
            
        if info.get("valid_status"):
            lines.append(f"  - Status válidos: {', '.join(info['valid_status'])}")
        
        if info.get("common_filters"):
            lines.append(f"  - Filtros comunes: {', '.join(info['common_filters'])}")
        
        if info.get("sensitive"):
            lines.append("  - ⚠️ Tabla sensible (requiere permisos especiales)")
    
    return "\n".join(lines)


def get_table_info(table_name: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene información detallada de una tabla.
    
    Args:
        table_name: Nombre completo (schema.tabla) o solo tabla
        
    Returns:
        Dict con metadata de la tabla o None si no existe
    """
    # Normalizar nombre
    if "." not in table_name:
        # Buscar en todas las tablas
        for full_name, info in SCHEMA_DESCRIPTIONS.items():
            if full_name.endswith(f".{table_name}"):
                return {"name": full_name, **info}
        return None
    
    return SCHEMA_DESCRIPTIONS.get(table_name)


def resolve_entity_to_table(entity: str) -> Optional[str]:
    """
    Resuelve una entidad del lenguaje natural a su tabla correspondiente.
    
    Args:
        entity: Entidad mencionada por el usuario (ej: "pacientes", "citas")
        
    Returns:
        Nombre completo de la tabla o None
    """
    return ENTITY_TO_TABLE.get(entity.lower().strip())


def get_related_tables(table_name: str) -> List[str]:
    """
    Obtiene las tablas relacionadas con una tabla dada.
    
    Útil para sugerir JOINs al LLM.
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        Lista de tablas relacionadas
    """
    info = get_table_info(table_name)
    if not info or "relations" not in info:
        return []
    
    related: List[str] = []
    relations_dict: Dict[str, str] = info.get("relations", {})
    for _fk, target in relations_dict.items():
        target_table = ".".join(target.split(".")[:2])
        related.append(target_table)
    
    return list(set(related))


@lru_cache(maxsize=10)
def get_column_sample_values(
    table_name: str,
    column_name: str,
    limit: int = 5
) -> List[str]:
    """
    Obtiene valores de ejemplo de una columna para ayudar al LLM.
    
    Args:
        table_name: Nombre de la tabla (con schema)
        column_name: Nombre de la columna
        limit: Número de ejemplos
        
    Returns:
        Lista de valores de ejemplo
    """
    schema = table_name.split(".")[0]
    _table = table_name.split(".")[1]  # Unused but extracted for validation
    
    # Determinar BD
    if schema == "auth":
        db = next(get_auth_db())
    elif schema in ["ops", "finance"]:
        db = next(get_ops_db())
    else:
        db = next(get_core_db())
    
    try:
        sql = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
        LIMIT :limit
        """
        result = db.execute(text(sql), {"limit": limit})
        return [str(row[0]) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Error obteniendo sample values: {e}")
        return []
    finally:
        db.close()


def build_query_context(entities: List[str]) -> Dict[str, Any]:
    """
    Construye el contexto completo de esquema para las entidades detectadas.
    
    Usado por el nodo generate_sql para dar contexto al LLM.
    
    Args:
        entities: Lista de entidades mencionadas en la consulta
        
    Returns:
        Dict con tablas, relaciones y ejemplos relevantes
    """
    context: Dict[str, Any] = {
        "tables": {},
        "relations": [],
        "suggested_joins": [],
    }
    
    tables_found: set[str] = set()
    
    for entity in entities:
        table = resolve_entity_to_table(entity)
        if table:
            tables_found.add(table)
            context["tables"][table] = get_table_info(table)
            
            # Agregar tablas relacionadas
            related = get_related_tables(table)
            for rel in related:
                tables_found.add(rel)
                context["tables"][rel] = get_table_info(rel)
    
    # Sugerir JOINs basados en relaciones
    for tbl in tables_found:
        info = get_table_info(tbl)
        if info and "relations" in info:
            relations_dict: Dict[str, str] = info.get("relations", {})
            for fk, target in relations_dict.items():
                context["suggested_joins"].append({
                    "from_table": tbl,
                    "from_column": fk,
                    "to_table": ".".join(target.split(".")[:2]),
                    "to_column": target.split(".")[-1],
                })
    
    return context
