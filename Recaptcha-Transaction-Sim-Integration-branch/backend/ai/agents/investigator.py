"""
backend/ai/agents/investigator.py
───────────────────────────────────
Step 4: Return Forensic Explanation (Async)

Takes a flagged alert dict, calls the model once via the async provider,
and returns a plain-language explanation string.
"""

from __future__ import annotations

from backend.ai.providers.base import BaseLLMProvider, ModelProviderError
from backend.ai.prompts.investigator_prompts import (
    INVESTIGATOR_SYSTEM_PROMPT,
    build_investigator_user_prompt,
)


class InvestigatorAgent:
    """Explains a flagged alert in plain language using a single model call.

    Args:
        provider: Any BaseLLMProvider instance (Gemini or Local).
    """

    MAX_TOKENS = 300

    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider

    async def explain(self, alert: dict) -> str:
        """Step 4: Call the model with alert context and return explanation asynchronously."""
        if not alert:
            return "No alert data provided — cannot generate explanation."

        system_prompt = INVESTIGATOR_SYSTEM_PROMPT
        user_prompt = build_investigator_user_prompt(alert)

        explanation = await self.provider.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=self.MAX_TOKENS,
        )

        return explanation
