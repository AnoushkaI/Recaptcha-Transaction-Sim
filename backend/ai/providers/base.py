"""
Base LLM Provider Interface (`ai/providers/base.py`)

# CONTRACT: Confirm with Person B - Base provider signature is co-owned between
Person A (Local Fallback) and Person B (Gemini Provider).
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM model providers (Gemini & Local Ollama).
    """

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate text completion from prompt and optional system prompt.
        
        Args:
            prompt: User/agent prompt text
            system_prompt: System instruction prompt
            
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
