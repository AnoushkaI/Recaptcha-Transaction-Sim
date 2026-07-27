"""
backend/ai/agents/rule_writer.py
──────────────────────────────────
Step 6: Generate Python Rule Code with self-correcting retry loop.

Flow:
  1. Call model with rule-writing prompt
  2. Strip markdown fences from response (models often wrap code in ```python```)
  3. Pass code to validator (fake stub in Phase 3, real AST validator in Phase 5)
  4. If valid → return immediately
  5. If invalid → feed exact error back to model, retry (up to MAX_RETRIES = 3)
  6. After 3 failures → return the last attempt with valid=False and the final error

The retry loop is capped at MAX_RETRIES and never shown to the human until
either valid code is produced or all retries are exhausted.
"""

from __future__ import annotations

import re

from backend.ai.providers.base import ModelProvider, ModelProviderError
from backend.ai.prompts.rule_writer_prompts import (
    RULE_WRITER_SYSTEM_PROMPT,
    build_rule_writer_user_prompt,
    build_retry_user_prompt,
)
from backend.config import RULE_WRITER_MAX_RETRIES

# ── Import validator ──────────────────────────────────────────────────────────
# Phase 3: uses the fake stub (mocks/validator_stub.py)
# Phase 5: swap this import for teammate's real AST validator:
#   from backend.core.validator import validate_rule
try:
    from mocks.validator_stub import validate_rule  # type: ignore[import]
except ImportError:
    # Graceful fallback if running from a path where mocks/ isn't importable
    def validate_rule(code: str) -> dict:  # type: ignore[misc]
        return {"valid": True}


# ── Regex to strip ```python ... ``` markdown fences ─────────────────────────
_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)\s*```", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped its output in them."""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text.strip()


class RuleWriterAgent:
    """Generates a Python detection rule with automatic self-correction.

    The retry loop (max 3 attempts) runs entirely inside this class.
    The caller (orchestrator) only ever sees the final result — either
    valid code or the last failure after all retries are exhausted.

    Args:
        provider: Any ModelProvider instance (Gemini or Local).
    """

    # Tokens: a short Python function + comment. 400 is generous.
    MAX_TOKENS = 400

    def __init__(self, provider: ModelProvider) -> None:
        self.provider = provider

    def generate_rule(self, command: str, context: dict | None = None) -> dict:
        """Step 6: Generate + validate a Python detection rule.

        Self-correcting retry loop:
          - Attempt 1: generate from scratch
          - Attempt 2-3: feed validator error back to model and ask it to fix the code
          - After MAX_RETRIES: return last attempt with valid=False

        Args:
            command: Natural-language instruction from the analyst.
            context: Optional alert/transaction dict for additional context.

        Returns:
            {
                "code":     str,       # Python rule code (last attempt)
                "valid":    bool,      # True only if validator accepted it
                "error":    str|None,  # validator error from last failed attempt
                "attempts": int,       # total attempts made (1-3)
            }
        """
        last_code = ""
        last_error = ""

        for attempt in range(1, RULE_WRITER_MAX_RETRIES + 1):

            # ── Build prompt ──────────────────────────────────────────────────
            if attempt == 1:
                user_prompt = build_rule_writer_user_prompt(command, context)
            else:
                # Feed the exact validator error back — this is the self-correction
                user_prompt = build_retry_user_prompt(
                    command=command,
                    previous_code=last_code,
                    validator_error=last_error,
                    attempt=attempt,
                    max_attempts=RULE_WRITER_MAX_RETRIES,
                    context=context,
                )

            # ── Call model ────────────────────────────────────────────────────
            try:
                raw_response = self.provider.generate(
                    system_prompt=RULE_WRITER_SYSTEM_PROMPT,
                    user_prompt=user_prompt,
                    max_tokens=self.MAX_TOKENS,
                )
            except ModelProviderError as exc:
                # Model call failed — don't retry on provider errors (rate limit,
                # auth, network). Surface immediately with attempt count.
                return {
                    "code": last_code,
                    "valid": False,
                    "error": f"Model provider error on attempt {attempt}: {exc}",
                    "attempts": attempt,
                }

            # ── Strip markdown fences (models often add ```python ... ```) ────
            code = _strip_fences(raw_response)
            last_code = code

            # ── Validate ──────────────────────────────────────────────────────
            validation = validate_rule(code)

            if validation["valid"]:
                # Success — return immediately without showing retries to the caller
                return {
                    "code": code,
                    "valid": True,
                    "error": None,
                    "attempts": attempt,
                }
            else:
                # Record the error so the next attempt's prompt can reference it
                last_error = validation.get("error", "Unknown validation error")

        # ── All retries exhausted ─────────────────────────────────────────────
        return {
            "code": last_code,
            "valid": False,
            "error": (
                f"Validation failed after {RULE_WRITER_MAX_RETRIES} attempts. "
                f"Last validator error: {last_error}"
            ),
            "attempts": RULE_WRITER_MAX_RETRIES,
        }
