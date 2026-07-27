"""
backend/ai/providers/gemini_provider.py
────────────────────────────────────────
GeminiProvider — implements ModelProvider using the google-genai SDK.

Handles:
  - Rate limit errors (429)  → raises ModelProviderError with clear message
  - Network/timeout errors   → raises ModelProviderError with cause attached
  - Model unavailable (404)  → raises ModelProviderError immediately (no retry here;
                                retry logic lives in rule_writer.py for rule tasks)
  - Empty/None responses     → raises ModelProviderError so callers always get a string
                                or a clear exception, never None

Design note:
  This class makes ONE attempt per call. The self-correcting retry loop (capped at 3
  attempts) lives in RuleWriterAgent — not here — so each retry is a full new call
  through this provider. That keeps the retry logic in one place and this class simple.
"""

from __future__ import annotations

import os
import time
from typing import Optional

from google import genai
from google.genai import types
from google.api_core import exceptions as google_exceptions

from backend.ai.providers.base import ModelProvider, ModelProviderError
from backend.config import GEMINI_API_KEY


class GeminiProvider(ModelProvider):
    """Calls the Gemini API via google-genai SDK.

    Args:
        model: The Gemini model name to use (e.g. "gemini-2.5-flash").
               Passed in by the provider factory, not hardcoded here.
        thinking_budget: Set to 0 to disable chain-of-thought thinking (faster,
                         cheaper). Set to None to let the model decide.
    """

    def __init__(
        self,
        model: str,
        thinking_budget: int = 0,
    ) -> None:
        self.model = model
        self.thinking_budget = thinking_budget
        self._client = genai.Client(api_key=GEMINI_API_KEY)

    # ── Public interface ──────────────────────────────────────────────────────

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 500,
    ) -> str:
        """Send a prompt to Gemini and return the text response.

        Args:
            system_prompt: The system/persona instruction.
            user_prompt:   The user-facing content or task.
            max_tokens:    Maximum tokens to generate.

        Returns:
            The model's text response as a plain string.

        Raises:
            ModelProviderError: On rate limits, network errors, model errors,
                                or empty responses. Always carries the original
                                exception in `.cause` so nothing is hidden.
        """
        config = self._build_config(max_tokens)
        contents = self._build_contents(system_prompt, user_prompt)

        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)

        # ── Rate limit (429) ─────────────────────────────────────────────
        except Exception as exc:
            error_str = str(exc)

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                raise ModelProviderError(
                    f"Gemini rate limit hit on model '{self.model}'. "
                    "Wait a moment and retry, or switch MODEL_PROVIDER=local in .env.",
                    cause=exc,
                )

            # ── Model not found / deprecated (404) ───────────────────────
            elif "404" in error_str or "NOT_FOUND" in error_str:
                raise ModelProviderError(
                    f"Model '{self.model}' is not available for your API key. "
                    "Run 'python scripts/verify_gemini.py' to find a working model "
                    "and update GEMINI_INVESTIGATOR_MODEL / GEMINI_RULE_WRITER_MODEL in config.py.",
                    cause=exc,
                )

            # ── Auth / key invalid (401, 403) ────────────────────────────
            elif "401" in error_str or "403" in error_str or "API_KEY_INVALID" in error_str:
                raise ModelProviderError(
                    "Gemini API key is invalid or lacks permission. "
                    "Check GEMINI_API_KEY in your .env file.",
                    cause=exc,
                )

            # ── Network / timeout ─────────────────────────────────────────
            elif "timeout" in error_str.lower() or "connection" in error_str.lower():
                raise ModelProviderError(
                    f"Network error reaching Gemini API (model: '{self.model}'). "
                    "Check your internet connection.",
                    cause=exc,
                )

            # ── Any other unexpected error ────────────────────────────────
            else:
                raise ModelProviderError(
                    f"Unexpected Gemini API error on model '{self.model}': {type(exc).__name__}",
                    cause=exc,
                )

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_config(self, max_tokens: int) -> types.GenerateContentConfig:
        """Build the generation config, including thinking settings."""
        kwargs: dict = {"max_output_tokens": max_tokens}
        if self.thinking_budget is not None:
            kwargs["thinking_config"] = types.ThinkingConfig(
                thinking_budget=self.thinking_budget
            )
        return types.GenerateContentConfig(**kwargs)

    def _build_contents(self, system_prompt: str, user_prompt: str) -> list:
        """Build the contents list with system instruction + user message."""
        return [
            types.Content(
                role="user",
                parts=[
                    types.Part(text=f"System: {system_prompt}\n\nUser: {user_prompt}")
                ],
            )
        ]

    def _extract_text(self, response) -> str:
        """Extract the text string from a Gemini response object.

        Handles thinking models (where response.text may be None) by iterating
        the candidate parts directly.

        Raises:
            ModelProviderError: If no usable text is found in the response.
        """
        # Fast path — most non-thinking models
        if response.text is not None and response.text.strip():
            return response.text.strip()

        # Thinking model path — walk the parts
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text and part.text.strip():
                    return part.text.strip()

        # Empty response — surface clearly rather than returning ""
        finish_reason = ""
        if response.candidates:
            finish_reason = str(response.candidates[0].finish_reason)

        raise ModelProviderError(
            f"Gemini returned an empty response from model '{self.model}'. "
            f"finish_reason={finish_reason}. "
            "Try increasing max_tokens or simplifying the prompt."
        )

    def __repr__(self) -> str:
        return f"GeminiProvider(model={self.model!r})"
