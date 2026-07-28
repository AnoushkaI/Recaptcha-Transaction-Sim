"""
backend/ai/providers/factory.py
─────────────────────────────────
Provider factory — reads MODEL_PROVIDER / LLM_PROVIDER from config.py and returns
the correct BaseLLMProvider instance.
"""

from __future__ import annotations

from backend.config import (
    MODEL_PROVIDER,
    GEMINI_INVESTIGATOR_MODEL,
    GEMINI_RULE_WRITER_MODEL,
)
from backend.ai.providers.base import BaseLLMProvider


def get_provider(role: str = "investigator") -> BaseLLMProvider:
    """Return the configured BaseLLMProvider for a given agent role."""
    provider_name = MODEL_PROVIDER.lower()
    if provider_name == "gemini":
        return _get_gemini_provider(role)
    elif provider_name == "local":
        return _get_local_provider(role)
    else:
        raise ValueError(
            f"Unknown MODEL_PROVIDER='{MODEL_PROVIDER}'. "
            "Set it to 'gemini' or 'local' in your .env file."
        )


def _get_gemini_provider(role: str) -> BaseLLMProvider:
    """Instantiate a GeminiProvider with the correct model for the given role."""
    from backend.ai.providers.gemini_provider import GeminiProvider

    model = GEMINI_RULE_WRITER_MODEL if role == "rule_writer" else GEMINI_INVESTIGATOR_MODEL

    return GeminiProvider(
        model=model,
        thinking_budget=0,
    )


def _get_local_provider(role: str) -> BaseLLMProvider:
    """Instantiate LocalOllamaProvider (imported lazily)."""
    try:
        from backend.ai.providers.local_provider import LocalOllamaProvider
        return LocalOllamaProvider()
    except ImportError:
        try:
            from backend.core.local_provider import LocalProvider
            return LocalProvider()
        except ImportError as exc:
            raise ImportError(
                "MODEL_PROVIDER=local but LocalOllamaProvider is not available."
            ) from exc
