"""
Tools Package - Herramientas para el agente LangGraph
=====================================================

Contiene las herramientas que el agente usa para:
- Ejecutar consultas SQL de forma segura
- Realizar búsquedas difusas en la BD
- Obtener información del esquema
- Buscar en el vector store (embeddings)
"""

from .sql_executor import (
    execute_safe_query,
    validate_query_safety,
    detect_target_database,
    get_table_columns,
    get_schema_tables,
    SCHEMA_TO_DB,
    SENSITIVE_TABLES,
)

from .fuzzy_search import (
    fuzzy_search_field,
    fuzzy_search_patient,
    fuzzy_search_podologo,
    get_suggestions_for_term,
    verify_pg_trgm_extension,
    FUZZY_SEARCHABLE_FIELDS,
)

from .schema_info import (
    get_schema_context_for_prompt,
    get_table_info,
    resolve_entity_to_table,
    get_related_tables,
    get_column_sample_values,
    build_query_context,
    SCHEMA_DESCRIPTIONS,
    ENTITY_TO_TABLE,
)

__all__ = [
    # SQL Executor
    "execute_safe_query",
    "validate_query_safety",
    "detect_target_database",
    "get_table_columns",
    "get_schema_tables",
    "SCHEMA_TO_DB",
    "SENSITIVE_TABLES",
    # Fuzzy Search
    "fuzzy_search_field",
    "fuzzy_search_patient",
    "fuzzy_search_podologo",
    "get_suggestions_for_term",
    "verify_pg_trgm_extension",
    "FUZZY_SEARCHABLE_FIELDS",
    # Schema Info
    "get_schema_context_for_prompt",
    "get_table_info",
    "resolve_entity_to_table",
    "get_related_tables",
    "get_column_sample_values",
    "build_query_context",
    "SCHEMA_DESCRIPTIONS",
    "ENTITY_TO_TABLE",
]
