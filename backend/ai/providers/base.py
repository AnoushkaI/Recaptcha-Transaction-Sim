"""
Base LLM Provider Interface (`backend/ai/providers/base.py`)

Shared abstract interface for LLM model providers (Gemini & Local Ollama).
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM model providers (Gemini & Local Ollama).
    """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500
    ) -> str:
        """
        Generate text completion from prompt and optional system prompt.
        
        Args:
            prompt: User/agent prompt text (or system prompt when called positionally as system_prompt)
            system_prompt: Optional system instruction prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text string response
        """
        pass

    @abstractmethod
    async def check_health(self) -> bool:
        """
        Check if provider service is reachable and operational.
        """
        pass


# Alias for backward compatibility across AI module
ModelProvider = BaseLLMProvider


class ModelProviderError(Exception):
    """Raised by any LLM Provider implementation on failure."""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        base = super().__str__()
        if self.cause:
            return f"{base} | caused by: {type(self.cause).__name__}: {self.cause}"
        return base
