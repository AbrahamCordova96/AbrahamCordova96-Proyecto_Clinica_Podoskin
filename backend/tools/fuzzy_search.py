"""
Fuzzy Search Tool - Búsqueda difusa con PostgreSQL pg_trgm
==========================================================

Proporciona búsqueda difusa para:
- Nombres de pacientes (tolerante a errores de escritura)
- Nombres de podólogos
- Tipos de tratamiento
- Servicios del catálogo

Usa la extensión pg_trgm de PostgreSQL para similitud de trigramas.
"""

import logging
from typing import List, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.core.config import get_settings
from backend.api.deps.database import get_core_db, get_ops_db
from backend.agents.state import FuzzyMatch, DatabaseTarget

logger = logging.getLogger(__name__)
settings = get_settings()


# =============================================================================
# CONFIGURACIÓN DE CAMPOS BUSCABLES
# =============================================================================

# Campos donde se puede hacer búsqueda difusa
FUZZY_SEARCHABLE_FIELDS: Dict[str, Dict[str, Any]] = {
    # Core DB - Pacientes
    "pacientes": {
        "schema": "clinic",
        "db": DatabaseTarget.CORE,
        "fields": ["nombres", "apellidos", "telefono", "email"],
        "display_template": "{nombres} {apellidos}",
        "id_field": "id_paciente",
    },
    # Core DB - Tratamientos
    "tratamientos": {
        "schema": "clinic", 
        "db": DatabaseTarget.CORE,
        "fields": ["problema", "zona_afectada"],
        "display_template": "{problema}",
        "id_field": "id_tratamiento",
    },
    # Ops DB - Podólogos
    "podologos": {
        "schema": "ops",
        "db": DatabaseTarget.OPS,
        "fields": ["nombres", "apellidos", "especialidad"],
        "display_template": "{nombres} {apellidos}",
        "id_field": "id_podologo",
    },
    # Ops DB - Catálogo de servicios
    "catalogo_servicios": {
        "schema": "ops",
        "db": DatabaseTarget.OPS,
        "fields": ["nombre_servicio", "descripcion"],
        "display_template": "{nombre_servicio}",
        "id_field": "id_servicio",
    },
    # Ops DB - Prospectos
    "solicitudes_prospectos": {
        "schema": "ops",
        "db": DatabaseTarget.OPS,
        "fields": ["nombre", "telefono", "motivo_consulta"],
        "display_template": "{nombre}",
        "id_field": "id_prospecto",
    },
}


# =============================================================================
# FUNCIONES DE BÚSQUEDA DIFUSA
# =============================================================================

def _get_session(db_target: DatabaseTarget) -> Session:
    """Obtiene sesión de BD según el target."""
    if db_target == DatabaseTarget.CORE:
        return next(get_core_db())
    elif db_target == DatabaseTarget.OPS:
        return next(get_ops_db())
    else:
        return next(get_core_db())


def fuzzy_search_field(
    search_term: str,
    table: str,
    field: str,
    threshold: float = 0.0,
    limit: int = 5,
) -> List[FuzzyMatch]:
    """
    Busca coincidencias difusas en un campo específico usando pg_trgm.
    
    Args:
        search_term: Término a buscar
        table: Nombre de la tabla
        field: Nombre del campo
        threshold: Umbral de similitud (0.0 a 1.0)
        limit: Máximo de resultados
        
    Returns:
        Lista de FuzzyMatch ordenados por similitud
    """
    effective_threshold = threshold if threshold > 0 else settings.AGENT_FUZZY_THRESHOLD
    
    if table not in FUZZY_SEARCHABLE_FIELDS:
        logger.warning(f"Tabla {table} no está configurada para búsqueda difusa")
        return []
    
    config = FUZZY_SEARCHABLE_FIELDS[table]
    if field not in config["fields"]:
        logger.warning(f"Campo {field} no es buscable en {table}")
        return []
    
    schema = config["schema"]
    db_target = config["db"]
    
    # Query con pg_trgm similarity
    sql = f"""
    SELECT 
        {field} as matched_value,
        similarity({field}, :term) as sim_score
    FROM {schema}.{table}
    WHERE {field} IS NOT NULL
      AND {field} % :term  -- Operador de similitud de pg_trgm
      AND similarity({field}, :term) >= :threshold
    ORDER BY sim_score DESC
    LIMIT :limit
    """
    
    db = None
    try:
        db = _get_session(db_target)
        result = db.execute(
            text(sql),
            {"term": search_term, "threshold": effective_threshold, "limit": limit}
        )
        
        matches: List[FuzzyMatch] = []
        for row in result.fetchall():
            matches.append(FuzzyMatch(
                original_term=search_term,
                matched_term=row.matched_value,
                similarity=float(row.sim_score),
                table=table,
                column=field,
            ))
        
        logger.info(f"Búsqueda difusa '{search_term}' en {table}.{field}: {len(matches)} coincidencias")
        return matches
        
    except Exception as e:
        logger.error(f"Error en búsqueda difusa: {str(e)}")
        return []
    finally:
        if db:
            db.close()


def fuzzy_search_patient(
    search_term: str,
    threshold: float = 0.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca pacientes por nombre completo usando búsqueda difusa.
    
    Busca en nombres y apellidos concatenados.
    
    Args:
        search_term: Nombre a buscar (parcial o completo)
        threshold: Umbral de similitud
        limit: Máximo de resultados
        
    Returns:
        Lista de pacientes con su similitud
    """
    effective_threshold = threshold if threshold > 0 else settings.AGENT_FUZZY_THRESHOLD
    
    sql = """
    SELECT 
        id_paciente,
        nombres,
        apellidos,
        telefono,
        fecha_nacimiento,
        similarity(nombres || ' ' || apellidos, :term) as sim_score
    FROM clinic.pacientes
    WHERE activo = true
      AND (nombres || ' ' || apellidos) % :term
      AND similarity(nombres || ' ' || apellidos, :term) >= :threshold
    ORDER BY sim_score DESC
    LIMIT :limit
    """
    
    db = None
    try:
        db = _get_session(DatabaseTarget.CORE)
        result = db.execute(
            text(sql),
            {"term": search_term, "threshold": effective_threshold, "limit": limit}
        )
        
        patients: List[Dict[str, Any]] = []
        for row in result.fetchall():
            patients.append({
                "id_paciente": row.id_paciente,
                "nombre_completo": f"{row.nombres} {row.apellidos}",
                "nombres": row.nombres,
                "apellidos": row.apellidos,
                "telefono": row.telefono,
                "fecha_nacimiento": str(row.fecha_nacimiento) if row.fecha_nacimiento else None,
                "similitud": round(float(row.sim_score), 3),
            })
        
        logger.info(f"Búsqueda de paciente '{search_term}': {len(patients)} coincidencias")
        return patients
        
    except Exception as e:
        logger.error(f"Error buscando paciente: {str(e)}")
        return []
    finally:
        if db:
            db.close()


def fuzzy_search_podologo(
    search_term: str,
    threshold: float = 0.0,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Busca podólogos por nombre usando búsqueda difusa.
    
    Args:
        search_term: Nombre a buscar
        threshold: Umbral de similitud
        limit: Máximo de resultados
        
    Returns:
        Lista de podólogos con su similitud
    """
    effective_threshold = threshold if threshold > 0 else settings.AGENT_FUZZY_THRESHOLD
    
    sql = """
    SELECT 
        id_podologo,
        nombres,
        apellidos,
        especialidad,
        similarity(nombres || ' ' || apellidos, :term) as sim_score
    FROM ops.podologos
    WHERE activo = true
      AND (nombres || ' ' || apellidos) % :term
      AND similarity(nombres || ' ' || apellidos, :term) >= :threshold
    ORDER BY sim_score DESC
    LIMIT :limit
    """
    
    db = None
    try:
        db = _get_session(DatabaseTarget.OPS)
        result = db.execute(
            text(sql),
            {"term": search_term, "threshold": effective_threshold, "limit": limit}
        )
        
        podologos: List[Dict[str, Any]] = []
        for row in result.fetchall():
            podologos.append({
                "id_podologo": row.id_podologo,
                "nombre_completo": f"{row.nombres} {row.apellidos}",
                "especialidad": row.especialidad,
                "similitud": round(float(row.sim_score), 3),
            })
        
        return podologos
        
    except Exception as e:
        logger.error(f"Error buscando podólogo: {str(e)}")
        return []
    finally:
        if db:
            db.close()


def get_suggestions_for_term(
    search_term: str,
    entity_type: str = "paciente",
    limit: int = 3,
) -> List[str]:
    """
    Obtiene sugerencias amigables para un término no encontrado.
    
    Útil para mensajes de error con alternativas (Decisión 5).
    
    Args:
        search_term: Término que no dio resultados exactos
        entity_type: Tipo de entidad (paciente, podologo, servicio)
        limit: Máximo de sugerencias
        
    Returns:
        Lista de sugerencias formateadas para el usuario
    """
    suggestions = []
    
    if entity_type == "paciente":
        matches = fuzzy_search_patient(search_term, threshold=0.3, limit=limit)
        suggestions = [m["nombre_completo"] for m in matches]
        
    elif entity_type == "podologo":
        matches = fuzzy_search_podologo(search_term, threshold=0.3, limit=limit)
        suggestions = [m["nombre_completo"] for m in matches]
        
    elif entity_type == "servicio":
        matches = fuzzy_search_field(
            search_term, 
            "catalogo_servicios", 
            "nombre_servicio",
            threshold=0.3,
            limit=limit
        )
        suggestions = [m.matched_term for m in matches]
    
    return suggestions


# =============================================================================
# VERIFICACIÓN DE EXTENSIÓN pg_trgm
# =============================================================================

def verify_pg_trgm_extension() -> bool:
    """
    Verifica que la extensión pg_trgm esté instalada.
    
    Returns:
        True si pg_trgm está disponible
    """
    sql = """
    SELECT EXISTS (
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    ) as has_trgm
    """
    
    db = None
    try:
        db = _get_session(DatabaseTarget.CORE)
        result = db.execute(text(sql))
        row = result.fetchone()
        has_trgm = row.has_trgm if row else False
        
        if not has_trgm:
            logger.warning("Extensión pg_trgm no está instalada. La búsqueda difusa no funcionará.")
        
        return has_trgm
        
    except Exception as e:
        logger.error(f"Error verificando pg_trgm: {str(e)}")
        return False
    finally:
        if db:
            db.close()
