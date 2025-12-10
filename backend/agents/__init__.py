# backend/agents/__init__.py
# LangGraph agents for PodoSkin AI assistant
# 
# Structure following LangGraph best practices:
#   - graph.py: StateGraph definition and compilation
#   - state.py: TypedDict state definition
#   - workflow.py: Workflow orchestration
#   - nodes/: Individual node implementations

from .state import (
    AgentState,
    IntentType,
    ErrorType,
    DatabaseTarget,
    SQLQuery,
    ExecutionResult,
    FuzzyMatch,
    create_initial_state,
    format_friendly_error,
    add_log_entry,
    FRIENDLY_MESSAGES,
)

__all__ = [
    # State
    "AgentState",
    "IntentType",
    "ErrorType", 
    "DatabaseTarget",
    "SQLQuery",
    "ExecutionResult",
    "FuzzyMatch",
    # Helpers
    "create_initial_state",
    "format_friendly_error",
    "add_log_entry",
    "FRIENDLY_MESSAGES",
]
