"""
Conversational Agents - Agentes con Criterio Controlado
=======================================================

Agentes conversacionales para interacción natural con guardrails.
Separados de los workflows para mantener arquitectura limpia.

Basado en:
https://docs.langchain.com/oss/python/langchain/agents
https://docs.langchain.com/oss/python/langgraph/workflows-agents

Agentes disponibles:
- chat_clinica: Asistente clínico con conversación natural
- evolucion_assistant: Asistente para crear notas SOAP con revisión
- general_assistant: Asistente general de la clínica
"""

from .base_agent import ConversationalAgentBase, AgentResponse, AgentRole

__all__ = [
    "ConversationalAgentBase",
    "AgentResponse",
    "AgentRole",
]
