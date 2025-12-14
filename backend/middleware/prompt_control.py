"""
Prompt Control - Control y Sanitización de Prompts
==================================================

Middleware para validar y sanitizar prompts antes de enviarlos al LLM.
Previene inyección de prompts y contenido malicioso.
"""

import re
import logging
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PromptRisk(str, Enum):
    """Niveles de riesgo de un prompt."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PromptValidationResult(BaseModel):
    """Resultado de la validación de un prompt."""
    is_valid: bool
    risk_level: PromptRisk
    sanitized_prompt: str
    warnings: List[str] = Field(default_factory=list)
    blocked_patterns: List[str] = Field(default_factory=list)


class PromptController:
    """Controlador de prompts para validación y sanitización."""
    
    # Patrones peligrosos
    DANGEROUS_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions|rules)",
        r"forget\s+(everything|all|previous)",
        r"<\s*script\s*>",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM",
    ]
    
    MAX_PROMPT_LENGTH = 2000
    
    def validate_and_sanitize(
        self,
        prompt: str,
        user_role: str
    ) -> PromptValidationResult:
        """
        Validar y sanitizar un prompt.
        
        Args:
            prompt: Prompt del usuario
            user_role: Rol del usuario (Admin, Podologo, Recepcion)
            
        Returns:
            PromptValidationResult
        """
        warnings = []
        blocked_patterns = []
        risk_level = PromptRisk.SAFE
        
        # Validar longitud
        if len(prompt) > self.MAX_PROMPT_LENGTH:
            return PromptValidationResult(
                is_valid=False,
                risk_level=PromptRisk.HIGH,
                sanitized_prompt="",
                warnings=[f"Prompt demasiado largo ({len(prompt)})"],
                blocked_patterns=[]
            )
        
        # Detectar patrones peligrosos
        prompt_lower = prompt.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, prompt_lower, re.IGNORECASE):
                blocked_patterns.append(pattern)
                risk_level = PromptRisk.CRITICAL
        
        if blocked_patterns:
            return PromptValidationResult(
                is_valid=False,
                risk_level=risk_level,
                sanitized_prompt="",
                warnings=["Patrón de ataque detectado"],
                blocked_patterns=blocked_patterns
            )
        
        # Sanitizar
        sanitized = self._sanitize(prompt)
        
        return PromptValidationResult(
            is_valid=True,
            risk_level=risk_level,
            sanitized_prompt=sanitized,
            warnings=warnings,
            blocked_patterns=[]
        )
    
    def _sanitize(self, prompt: str) -> str:
        """Sanitizar un prompt."""
        # Remover espacios extra
        sanitized = " ".join(prompt.split())
        
        # Remover HTML tags
        sanitized = re.sub(r"<[^>]+>", "", sanitized)
        
        # Limitar longitud
        if len(sanitized) > self.MAX_PROMPT_LENGTH:
            sanitized = sanitized[:self.MAX_PROMPT_LENGTH]
        
        return sanitized
