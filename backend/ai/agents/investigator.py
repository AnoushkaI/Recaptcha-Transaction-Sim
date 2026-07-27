"""
backend/ai/agents/investigator.py
───────────────────────────────────
Step 4: Return Forensic Explanation

Takes a flagged alert dict, calls the model once via the provider,
and returns a plain-language explanation string.

Single model call — no retry loop needed here (explanations don't have a
pass/fail validator; if the model responds, we use it).
"""

from __future__ import annotations

from backend.ai.providers.base import ModelProvider, ModelProviderError
from backend.ai.prompts.investigator_prompts import (
    INVESTIGATOR_SYSTEM_PROMPT,
    build_investigator_user_prompt,
)


class InvestigatorAgent:
    """Explains a flagged alert in plain language using a single model call.

    Args:
        provider: Any ModelProvider instance (Gemini or Local).
    """

    # Tokens: ~3-5 sentence explanation. 300 is generous.
    MAX_TOKENS = 300

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def explain(self, alert: dict) -> str:
        """Step 4: Call the model with the alert context and return explanation.

        Args:
            alert: A flagged alert dict matching the shared contract:
                   { id, transaction, rule_triggered, severity, timestamp }

        Returns:
            Plain-language explanation string from the model.

        Raises:
            ModelProviderError: If the model call fails (surfaces exact error —
                                never swallowed, never silently retried here).
        """
        if not alert:
            return "No alert data provided — cannot generate explanation."

        system_prompt = INVESTIGATOR_SYSTEM_PROMPT
        user_prompt = build_investigator_user_prompt(alert)

        # Single model call — errors propagate up to the orchestrator node,
        # which catches them and puts them in state["error"]
        explanation = self.provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=self.MAX_TOKENS,
        )

        return explanation
