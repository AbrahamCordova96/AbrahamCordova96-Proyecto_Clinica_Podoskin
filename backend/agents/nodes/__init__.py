# backend/agents/nodes/__init__.py
"""
Nodos del Agente LangGraph
==========================

Cada nodo es una función que transforma el estado del agente.
El grafo conecta estos nodos con edges condicionales.

Flujo principal:
1. classify_intent → Determina qué quiere el usuario
2. check_permissions → Verifica permisos RBAC
3. generate_sql → Convierte a SQL (si aplica)
4. execute_sql → Ejecuta la query
5. generate_response → Formatea respuesta amigable
"""

# Nodos principales del flujo
from .classify_intent_node import ClassifyIntentNode, classify_intent
from .check_permissions_node import CheckPermissionsNode, check_permissions
from .nl_to_sql_node import NLToSQLNode, generate_sql
from .sql_exec_node import SQLExecNode, execute_sql
from .llm_response_node import LlmResponseNode, generate_response

# Nodos opcionales (deshabilitados por defecto)
from .vector_context_node import VectorContextNode
from .combine_context_node import CombineContextNode

__all__ = [
    # Clases de nodos (wrappers)
    "ClassifyIntentNode",
    "CheckPermissionsNode",
    "NLToSQLNode",
    "SQLExecNode", 
    "LlmResponseNode",
    "VectorContextNode",
    "CombineContextNode",
    # Funciones de nodos (para uso directo en grafo)
    "classify_intent",
    "check_permissions",
    "generate_sql",
    "execute_sql",
    "generate_response",
]
