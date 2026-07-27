"""
backend/ai/providers/base.py
─────────────────────────────
CO-OWNED shared interface — do not change unilaterally.

This is the exact ModelProvider contract specified in section 4 of the project spec.
Both the Gemini provider (my part) and the Local/Ollama provider (teammate's part)
must subclass this and implement `generate()`.
"""

from abc import ABC, abstractmethod


class ModelProvider(ABC):
    """Shared base class for all model backends.

    Any class that wraps a language model (cloud or local) must inherit this
    and implement `generate()`. The orchestrator and agents call ONLY this
    interface — they never import a concrete provider directly.
    """

    @abstractmethod
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
    ) -> str:
        """Send a prompt and return the model's text response.

        Args:
            system_prompt: The system/persona instruction for the model.
            user_prompt:   The user-facing content or task description.
            max_tokens:    Maximum tokens to generate (default 500).

        Returns:
            The raw text string from the model.

        Raises:
            ModelProviderError: On any unrecoverable API or network failure.
        """
        raise NotImplementedError


class ModelProviderError(Exception):
    """Raised by any ModelProvider implementation on failure.

    Carries the original exception so callers can surface the real cause
    rather than hiding it.
    """

    def __init__(self, message: str, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause

    def __str__(self) -> str:
        base = super().__str__()
        if self.cause:
            return f"{base} | caused by: {type(self.cause).__name__}: {self.cause}"
        return base
