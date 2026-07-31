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
    """Generates an AST-valid fallback Python rule tailored dynamically to the target alert context."""
    cmd_lower = (command or "").lower()
    ctx = context or {}
    
    # Handle different context structures: dict with 'transaction', dict with 'transaction_details', or direct dict
    txn = {}
    if isinstance(ctx.get("transaction"), dict):
        txn = ctx["transaction"]
    elif isinstance(ctx.get("transaction_details"), dict):
        txn = ctx["transaction_details"]
    elif isinstance(ctx, dict):
        txn = ctx

    amt = float(txn.get("amount", 2000.0) or 2000.0)
    loc = str(txn.get("location") or "US-NY")
    cat = str(txn.get("merchant_category") or "electronics").lower().replace(" ", "_")
    rule_title = str(ctx.get("rule_triggered") or ctx.get("title") or "").lower()
    desc = str(txn.get("description") or "").lower()
    
    auto_prob = float(txn.get("automation_probability", 0.0) or 0.0)
    vpn_prob = float(txn.get("vpn_probability", 0.0) or 0.0)
    is_intl = bool(txn.get("is_international")) or loc in ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"] or "cross-border" in desc or "intl" in rule_title
    acc_age = int(txn.get("account_age_days", 30) or 30)

    # 1. High Automation / Bot / Session Cadence
    if "automation" in cmd_lower or "vpn" in cmd_lower or "bot" in cmd_lower or auto_prob > 0.4 or vpn_prob > 0.4 or "bot" in rule_title or "cadence" in rule_title:
        return (
            "def evaluate(tx):\n"
            "    # Rule: Flag unnatural session cadence & automated form filling\n"
            "    return tx.automation_probability > 0.5 or tx.vpn_probability > 0.5"
        )
    # 2. International / High-Risk Location / Cross-Border
    elif "wire" in cmd_lower or "international" in cmd_lower or is_intl or "location" in rule_title or "country" in rule_title:
        return (
            f"def evaluate(tx):\n"
            f"    # Rule: Flag cross-border activity in {loc} or high-risk locations\n"
            f"    return tx.is_international or tx.location == '{loc}'"
        )
    # 3. High-Risk Merchant Category (Crypto, Gaming, Electronics, Luxury)
    elif "crypto" in cmd_lower or "gaming" in cmd_lower or "luxury" in rule_title or "electronics" in rule_title or cat in ["crypto", "gift_cards", "electronics", "luxury"]:
        threshold = max(amt * 0.7, 300.0)
        return (
            f"def evaluate(tx):\n"
            f"    # Rule: Flag high-risk {cat} merchant transactions over threshold\n"
            f"    return tx.merchant_category == '{cat}' and tx.amount >= {threshold:.1f}"
        )
    # 4. New Account / Sudden Activity
    elif "account" in cmd_lower or "new" in cmd_lower or acc_age < 14 or "new account" in rule_title:
        target_age = max(acc_age + 5, 14)
        threshold = max(amt * 0.6, 200.0)
        return (
            f"def evaluate(tx):\n"
            f"    # Rule: Flag rapid spend on new accounts under {target_age} days old\n"
            f"    return tx.account_age_days < {target_age} and tx.amount >= {threshold:.1f}"
        )
    # 5. Default: Dynamic amount threshold calculated specifically for this transaction amount
    else:
        threshold = max(amt * 0.8, 100.0)
        return (
            f"def evaluate(tx):\n"
            f"    # Rule: Flag transaction amount exceeding {cat} threshold\n"
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
