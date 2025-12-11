"""
Subgrafos de LangGraph por Origen
==================================

Este módulo contiene los subgrafos especializados para diferentes orígenes
de conversación (webapp, whatsapp_paciente, whatsapp_user).

Autor: Sistema
Fecha: 11 de Diciembre, 2025
"""

from .webapp_subgraph import build_webapp_subgraph
from .whatsapp_paciente_subgraph import build_whatsapp_paciente_subgraph
from .whatsapp_user_subgraph import build_whatsapp_user_subgraph

__all__ = [
    "build_webapp_subgraph",
    "build_whatsapp_paciente_subgraph",
    "build_whatsapp_user_subgraph",
]
