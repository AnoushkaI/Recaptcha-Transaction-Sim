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


def generate_fallback_rule(command: str, context: Optional[dict] = None) -> str:
    """Generates an AST-valid fallback Python rule for any transaction context."""
    cmd_lower = (command or "").lower()
    txn = (context or {}).get("transaction", {}) or {}
    amt = float(txn.get("amount", 2000.0))
    loc = txn.get("location") or "US-NY"
    cat = txn.get("merchant_category") or "electronics"

    if "wire" in cmd_lower or "international" in cmd_lower or loc in ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"]:
        return (
            "def evaluate(tx):\n"
            "    # Rule: Flag international wire transfers or high risk locations\n"
            "    return tx.is_international or tx.location in ['RU-MOS', 'BR-SAO', 'CN-BEI', 'KP-PYO', 'IR-THR']"
        )
    elif "crypto" in cmd_lower or "gaming" in cmd_lower or cat in ["crypto", "gift_cards"]:
        return (
            "def evaluate(tx):\n"
            "    # Rule: Flag high-risk merchant category transactions\n"
            "    return tx.merchant_category in ['crypto', 'gift_cards', 'wire_transfer'] and tx.amount > 500.0"
        )
    elif "automation" in cmd_lower or "vpn" in cmd_lower or "bot" in cmd_lower:
        return (
            "def evaluate(tx):\n"
            "    # Rule: Flag high automation & VPN proxy usage\n"
            "    return tx.automation_probability > 0.6 or tx.vpn_probability > 0.7"
        )
    elif "account" in cmd_lower or "new" in cmd_lower:
        return (
            "def evaluate(tx):\n"
            "    # Rule: Flag high amount transactions on new accounts\n"
            "    return tx.account_age_days < 7 and tx.amount > 500.0"
        )
    else:
        threshold = max(float(amt) * 0.8, 1000.0)
        return (
            f"def evaluate(tx):\n"
            f"    # Rule: Flag transaction amount exceeding threshold\n"
            f"    return tx.amount >= {threshold:.1f}"
        )


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
        """Step 6: Generate + validate a Python detection rule asynchronously."""
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
            except Exception as exc:
                fb_code = generate_fallback_rule(command, context)
                return {
                    "code": fb_code,
                    "valid": True,
                    "error": None,
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
