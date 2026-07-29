"""
backend/ai/agents/rule_writer.py
──────────────────────────────────
Step 6: Generate Python Rule Code with self-correcting retry loop (Async).

Flow:
  1. Call model with rule-writing prompt
  2. Strip markdown fences from response (models often wrap code in ```python```)
  3. Pass code to real ASTSafetyValidator from backend.core.validator
  4. If valid → return immediately
  5. If invalid → feed exact error back to model, retry (up to MAX_RETRIES = 3)
  6. After 3 failures → return the last attempt with valid=False and the final error
"""

from __future__ import annotations

import re
from typing import Optional, Dict, Any

from backend.ai.providers.base import BaseLLMProvider, ModelProviderError
from backend.ai.prompts.rule_writer_prompts import (
    RULE_WRITER_SYSTEM_PROMPT,
    build_rule_writer_user_prompt,
    build_retry_user_prompt,
)
from backend.config import RULE_WRITER_MAX_RETRIES
from backend.core.validator import ASTSafetyValidator

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its output in them."""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


class RuleWriterAgent:
    """Generates a Python detection rule with automatic self-correction.

    Args:
        provider: Any BaseLLMProvider instance (Gemini or Local).
    """

    MAX_TOKENS = 400

    def __init__(self, provider: BaseLLMProvider) -> None:
        self.provider = provider
        self.validator = ASTSafetyValidator()

    async def generate_rule(self, command: str, context: Optional[dict] = None) -> dict:
        """Step 6: Generate + validate a Python detection rule asynchronously.

        Self-correcting retry loop:
          - Attempt 1: generate from scratch
          - Attempt 2-3: feed validator error back to model and ask it to fix the code
          - After MAX_RETRIES: return last attempt with valid=False
        """
        last_code = ""
        last_error = ""

        for attempt in range(1, RULE_WRITER_MAX_RETRIES + 1):
            if attempt == 1:
                user_prompt = build_rule_writer_user_prompt(command, context)
            else:
                user_prompt = build_retry_user_prompt(
                    command=command,
                    previous_code=last_code,
                    validator_error=last_error,
                    attempt=attempt,
                    max_attempts=RULE_WRITER_MAX_RETRIES,
                    context=context,
                )

            try:
                raw_response = await self.provider.generate(
                    prompt=user_prompt,
                    system_prompt=RULE_WRITER_SYSTEM_PROMPT,
                    max_tokens=self.MAX_TOKENS,
                )
            except ModelProviderError as exc:
                return {
                    "code": last_code,
                    "valid": False,
                    "error": f"Model provider error on attempt {attempt}: {exc}",
                    "attempts": attempt,
                }

            code = _strip_fences(raw_response)
            last_code = code

            validation = self.validator.validate(code)

            if validation.valid:
                return {
                    "code": code,
                    "valid": True,
                    "error": None,
                    "attempts": attempt,
                }
            else:
                last_error = validation.error or "Unknown validation error"

        return {
            "code": last_code,
            "valid": False,
            "error": (
                f"Validation failed after {RULE_WRITER_MAX_RETRIES} attempts. "
                f"Last validator error: {last_error}"
            ),
            "attempts": RULE_WRITER_MAX_RETRIES,
        }
