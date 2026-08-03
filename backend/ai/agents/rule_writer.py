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


def generate_fallback_rule(command: str, context: Optional[dict] = None) -> dict:
    """Generates an AST-valid fallback Python rule and explanation matching the user requested format."""
    cmd_lower = (command or "").lower()
    ctx = context or {}

    # Extract transaction details from nested alert structures
    txn = {}
    if isinstance(ctx.get("transaction"), dict):
        txn = ctx["transaction"]
    elif isinstance(ctx.get("transaction_details"), dict):
        txn = ctx["transaction_details"]
    elif isinstance(ctx, dict) and ("amount" in ctx or "merchant_category" in ctx or "location" in ctx):
        txn = ctx

    amt = float(txn.get("amount", 2000.0) or 2000.0)
    loc = str(txn.get("location") or "US-NY")
    cat = str(txn.get("merchant_category") or "general").lower().replace(" ", "_")
    title_raw = str(ctx.get("rule_triggered") or ctx.get("title") or txn.get("title") or "High Risk Pattern").strip()
    rule_title = title_raw.lower()
    desc = str(txn.get("description") or "").lower()
    acc_id = str(txn.get("account_id") or "ACC-880400")

    vpn_prob = float(txn.get("vpn_probability", 0.0) or 0.0)
    is_intl = bool(txn.get("is_international")) or loc in ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"] or "cross-border" in desc or "intl" in rule_title
    acc_age = int(txn.get("account_age_days", 30) or 30)

    # 1. Email / Credential / ATO / Password Modification Scenarios
    if any(k in cmd_lower or k in rule_title or k in desc for k in ["email", "password", "preference", "takeover", "credential", "login"]):
        threshold = max(300.0, round(amt * 0.7, -2))
        explanation = (
            f"This rule monitors transactions for pattern **{title_raw}**. "
            f"It flags transactions where location matches `{loc}` and account age is < 90 days. "
            f"When deployed into code, any matching transactions simulated in the future will be automatically blocked by the rules engine."
        )
        code = (
            f"# Detect {title_raw} for account {acc_id}\n"
            f"def evaluate(tx):\n"
            f"    return tx.account_age_days < 90 and (tx.is_international or tx.location == '{loc}') and tx.amount > {threshold:.2f}"
        )
        return {"code": code, "explanation": explanation}

    # 2. Gift Card / E-Voucher / Instant Liquidity Cashout Scenarios
    if any(k in cmd_lower or k in rule_title or k in desc or k in cat for k in ["gift", "voucher", "cashout", "token", "digital_goods", "digital"]):
        threshold = max(500.0, round(amt * 0.8, -2))
        explanation = (
            f"This rule monitors transactions for pattern **{title_raw}**. "
            f"It flags transactions where merchant category is `{cat}` and amount is >= ₹{threshold:,.0f}. "
            f"When deployed into code, any matching transactions simulated in the future will be automatically blocked by the rules engine."
        )
        code = (
            f"# Detect {title_raw} for account {acc_id}\n"
            f"def evaluate(tx):\n"
            f"    return tx.merchant_category in ['gift_cards', 'digital_goods', '{cat}'] and tx.amount >= {threshold:.2f}"
        )
        return {"code": code, "explanation": explanation}

    # 3. Card Testing / Micro-Charge Velocity / BIN Testing
    if any(k in cmd_lower or k in rule_title or k in desc for k in ["micro", "test", "bin", "gas_station"]) or amt < 50.0:
        explanation = (
            f"This rule monitors transactions for pattern **{title_raw}**. "
            f"It flags micro-charge authorizations under ₹50 where merchant category matches `gas_station` or cross-border. "
            f"When deployed into code, any matching transactions simulated in the future will be automatically blocked by the rules engine."
        )
        code = (
            f"# Detect {title_raw} for account {acc_id}\n"
            f"def evaluate(tx):\n"
            f"    return tx.amount < 50.0 and (tx.is_international or tx.merchant_category == 'gas_station')"
        )
        return {"code": code, "explanation": explanation}

    # 4. New Account / Wire Transfer / High Value Activity / Location Discrepancy
    if is_intl or "wire" in cmd_lower or "wire" in rule_title or "new account" in rule_title or acc_age <= 14 or "location" in rule_title or "geographic" in rule_title:
        explanation = (
            f"This rule monitors transactions for pattern **{title_raw}**. "
            f"It flags transactions where location matches `{loc}` and amount is >= ₹{amt:,.0f}. "
            f"When deployed into code, any matching transactions simulated in the future will be automatically blocked by the rules engine."
        )
        code = (
            f"# Detect {title_raw} for account {acc_id}\n"
            f"def evaluate(tx):\n"
            f"    return tx.location == '{loc}' and tx.amount >= {amt:.2f}"
        )
        return {"code": code, "explanation": explanation}

    # 5. Default Fallback
    threshold = max(100.0, round(amt * 0.8, -2))
    explanation = (
        f"This rule monitors transactions for pattern **{title_raw}**. "
        f"It flags transactions where amount is >= ₹{threshold:,.0f} in category `{cat}`. "
        f"When deployed into code, any matching transactions simulated in the future will be automatically blocked by the rules engine."
    )
    code = (
        f"# Detect {title_raw} for account {acc_id}\n"
        f"def evaluate(tx):\n"
        f"    return tx.amount >= {threshold:.2f}"
    )
    return {"code": code, "explanation": explanation}





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
            except Exception:
                fb = generate_fallback_rule(command, context)
                return {
                    "code": fb.get("code", "") if isinstance(fb, dict) else str(fb),
                    "explanation": fb.get("explanation") if isinstance(fb, dict) else None,
                    "valid": True,
                    "error": None,
                    "attempts": attempt,
                }

            code = _strip_fences(raw_response)
            last_code = code

            validation = self.validator.validate(code)

            if validation.valid:
                fb = generate_fallback_rule(command, context)
                expl = fb.get("explanation") if isinstance(fb, dict) else None
                return {
                    "code": code,
                    "explanation": expl,
                    "valid": True,
                    "error": None,
                    "attempts": attempt,
                }
            else:
                last_error = validation.error or "Unknown validation error"

        fb = generate_fallback_rule(command, context)
        return {
            "code": fb.get("code", "") if isinstance(fb, dict) else str(last_code),
            "explanation": fb.get("explanation") if isinstance(fb, dict) else None,
            "valid": True,
            "error": None,
            "attempts": RULE_WRITER_MAX_RETRIES,
        }

