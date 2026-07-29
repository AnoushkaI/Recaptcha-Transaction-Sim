"""
backend/ai/providers/gemini_provider.py
────────────────────────────────────────
GeminiProvider — implements BaseLLMProvider using the google-genai async SDK.
"""

from __future__ import annotations

import os
from typing import Optional

from google import genai
from google.genai import types

from backend.ai.providers.base import BaseLLMProvider, ModelProviderError
from backend.config import GEMINI_API_KEY


class GeminiProvider(BaseLLMProvider):
    """Calls the Gemini API via google-genai SDK asynchronously."""

    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        thinking_budget: int = 0,
    ) -> None:
        self.model = model
        self.thinking_budget = thinking_budget
        self._client = None

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            if not GEMINI_API_KEY:
                raise ModelProviderError("GEMINI_API_KEY is not set. Add it to your .env file.")
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 500,
        **kwargs,
    ) -> str:
        """Send a prompt to Gemini asynchronously and return text response.

        Supports both:
          - generate(prompt, system_prompt=...)
          - generate(system_prompt=..., user_prompt=..., max_tokens=...)
        """
        user_p = kwargs.get("user_prompt")
        if user_p is not None:
            sys_p = prompt
            usr_p = user_p
        else:
            usr_p = prompt
            sys_p = system_prompt or ""

        config = self._build_config(max_tokens)
        contents = self._build_contents(sys_p, usr_p)

        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            return self._extract_text(response)

        except Exception as exc:
            error_str = str(exc)

            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                raise ModelProviderError(
                    f"Gemini rate limit hit on model '{self.model}'. "
                    "Wait a moment and retry, or switch MODEL_PROVIDER=local in .env.",
                    cause=exc,
                )
            elif "404" in error_str or "NOT_FOUND" in error_str:
                raise ModelProviderError(
                    f"Model '{self.model}' is not available for your API key.",
                    cause=exc,
                )
            elif "401" in error_str or "403" in error_str or "API_KEY_INVALID" in error_str:
                raise ModelProviderError(
                    "Gemini API key is invalid or lacks permission. "
                    "Check GEMINI_API_KEY in your .env file.",
                    cause=exc,
                )
            elif "timeout" in error_str.lower() or "connection" in error_str.lower():
                raise ModelProviderError(
                    f"Network error reaching Gemini API (model: '{self.model}').",
                    cause=exc,
                )
            else:
                raise ModelProviderError(
                    f"Unexpected Gemini API error on model '{self.model}': {type(exc).__name__}",
                    cause=exc,
                )

    async def check_health(self) -> bool:
        """Check if Gemini client is initialized with valid API key."""
        if not GEMINI_API_KEY:
            return False
        return True

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
        """Extract text string from Gemini response object."""
        if response.text is not None and response.text.strip():
            return response.text.strip()

        if response.candidates:
            for part in response.candidates[0].content.parts:
                if hasattr(part, "text") and part.text and part.text.strip():
                    return part.text.strip()

        finish_reason = ""
        if response.candidates:
            finish_reason = str(response.candidates[0].finish_reason)

        raise ModelProviderError(
            f"Gemini returned an empty response from model '{self.model}'. finish_reason={finish_reason}."
        )

    def __repr__(self) -> str:
        return f"GeminiProvider(model={self.model!r})"
