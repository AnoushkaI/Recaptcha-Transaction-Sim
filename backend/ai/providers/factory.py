"""
backend/ai/providers/factory.py
─────────────────────────────────
Provider factory — reads MODEL_PROVIDER from config.py and returns
the correct ModelProvider instance.

Usage (everywhere in the AI layer):
    from backend.ai.providers.factory import get_provider
    provider = get_provider(role="investigator")  # or role="rule_writer"

Why a factory?
  - The orchestrator and agents never import a concrete provider directly.
  - Switching between Gemini and Local only requires changing MODEL_PROVIDER in .env.
  - The local provider (teammate's local_provider.py) is imported lazily so the app
    works even if Ollama is not installed.
"""

from __future__ import annotations

from backend.config import (
    MODEL_PROVIDER,
    GEMINI_INVESTIGATOR_MODEL,
    GEMINI_RULE_WRITER_MODEL,
)
from backend.ai.providers.base import ModelProvider


def get_provider(role: str = "investigator") -> ModelProvider:
    """Return the configured ModelProvider for a given agent role.

    Args:
        role: "investigator" → lighter/faster model (flash)
              "rule_writer"  → more capable model (pro)

    Returns:
        A concrete ModelProvider instance.

    Raises:
        ValueError: If MODEL_PROVIDER is not "gemini" or "local".
        ImportError: If "local" is selected but teammate's local_provider.py
                     is not in place yet.
    """
    if MODEL_PROVIDER == "gemini":
        return _get_gemini_provider(role)
    elif MODEL_PROVIDER == "local":
        return _get_local_provider(role)
    else:
        raise ValueError(
            f"Unknown MODEL_PROVIDER='{MODEL_PROVIDER}'. "
            "Set it to 'gemini' or 'local' in your .env file."
        )


# ── Gemini path ───────────────────────────────────────────────────────────────

def _get_gemini_provider(role: str) -> ModelProvider:
    """Instantiate a GeminiProvider with the correct model for the given role."""
    from backend.ai.providers.gemini_provider import GeminiProvider

    model = GEMINI_RULE_WRITER_MODEL if role == "rule_writer" else GEMINI_INVESTIGATOR_MODEL

    return GeminiProvider(
        model=model,
        thinking_budget=0,  # disable chain-of-thought for speed/cost in Phase 2-3
    )


# ── Local / Ollama path ───────────────────────────────────────────────────────

def _get_local_provider(role: str) -> ModelProvider:
    """Instantiate teammate's LocalProvider (imported lazily).

    This import will fail if teammate's local_provider.py is not yet in place —
    which is expected during Phases 1-4. Switch MODEL_PROVIDER back to 'gemini'
    if you see an ImportError here.
    """
    try:
        # Teammate's file — do not create or edit this
        from backend.core.local_provider import LocalProvider  # type: ignore[import]
        return LocalProvider()
    except ImportError as exc:
        raise ImportError(
            "MODEL_PROVIDER=local but 'backend/core/local_provider.py' (teammate's file) "
            "is not available. Either set MODEL_PROVIDER=gemini in .env, or wait for "
            "teammate to deliver their local provider."
        ) from exc
