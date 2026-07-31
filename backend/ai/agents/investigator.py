"""
backend/ai/agents/investigator.py
───────────────────────────────────
Step 4: Return Forensic Explanation (Async)

Takes a flagged alert dict, calls the model once via the async provider,
and returns a plain-language explanation string. If LLM key/provider is missing or fails,
falls back to a structured deterministic forensic analysis engine.
"""

from __future__ import annotations

from typing import Optional
from backend.ai.providers.base import BaseLLMProvider, ModelProviderError
from backend.ai.prompts.investigator_prompts import (
    INVESTIGATOR_SYSTEM_PROMPT,
    build_investigator_user_prompt,
)


def generate_forensic_explanation(alert: dict) -> str:
    """Generates a structured, easy-to-understand forensic explanation for any transaction."""
    if not alert:
        return "No transaction selected for investigation."

    txn = alert.get("transaction", {}) or {}
    user = txn.get("user_name") or alert.get("user_name") or "User"
    acc = txn.get("account_id") or alert.get("account_id") or "account"
    amt = float(txn.get("amount") or alert.get("amount") or 0.0)
    avg_amt = float(txn.get("average_amount", 200.0))
    loc = str(txn.get("location") or alert.get("location") or "Unknown")
    cls_name = str(alert.get("classification") or txn.get("classification") or "HIGH_RISK")
    f_risk = float(alert.get("final_risk_score") or txn.get("final_risk_score") or 0.75)
    t_risk = float(alert.get("telemetry_risk_score") or txn.get("telemetry_risk_score") or 0.75)
    tx_risk = float(alert.get("transaction_risk_score") or txn.get("transaction_risk_score") or 0.75)
    rule = str(txn.get("title") or alert.get("rule_triggered") or alert.get("title") or "Fraud Security Threshold")
    desc = str(txn.get("description") or alert.get("description") or "")
    cat = str(txn.get("merchant_category") or "general")
    age = int(txn.get("account_age_days", 30))

    risk_label = "HIGH RISK" if cls_name == "HIGH_RISK" else ("SUSPICIOUS" if cls_name == "SUSPICIOUS" else "SAFE")

    # Evaluate telemetry & transaction risk drivers
    reasons = []

    auto_prob = float(txn.get("automation_probability", 0))
    vpn_prob = float(txn.get("vpn_probability", 0))
    tor_prob = float(txn.get("tor_probability", 0))
    ip_rep = float(txn.get("ip_reputation", 1.0))
    mouse_q = float(txn.get("mouse_movement_quality", 1.0))
    typing_err = float(txn.get("typing_error_rate", 0.05))

    if auto_prob >= 0.4:
        reasons.append(f"🤖 **High Bot/Automation Score ({auto_prob:.0%})**: Interaction mechanics show non-human velocity or automated script patterns.")
    if vpn_prob >= 0.4 or tor_prob >= 0.15:
        reasons.append(f"🌐 **Anonymized Proxy / VPN ({max(vpn_prob, tor_prob):.0%})**: Connection uses an anonymizing proxy, concealing true network origin.")
    if ip_rep <= 0.5:
        reasons.append(f"⚠️ **Low IP Reputation ({ip_rep:.2f})**: IP address has been associated with suspicious network activity.")
    if mouse_q <= 0.5:
        reasons.append(f"🖱️ **Unnatural Mouse Trajectories ({mouse_q:.2f})**: Mouse movement lacks natural human curves and micro-adjustments.")
    if typing_err >= 0.15:
        reasons.append(f"⌨️ **High Typing Anomaly ({typing_err:.0%})**: Keypress cadence and error rates deviate significantly from baseline.")

    if amt > (avg_amt * 1.5):
        reasons.append(f"💰 **High Amount Spike (₹{amt:,.0f})**: Transaction amount is noticeably higher than the historical account average (₹{avg_amt:,.0f}).")
    if txn.get("is_international") or loc in ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"]:
        reasons.append(f"📍 **High Risk Jurisdiction ({loc})**: Transaction originated from a geographically sensitive or foreign region.")
    if age <= 14:
        reasons.append(f"🆕 **New Account Risk ({age} days old)**: Account is recently created, increasing exposure to synthetic identity or rapid fraud.")
    if float(txn.get("password_changed_recently_probability", 0)) >= 0.4:
        reasons.append(f"🔑 **Recent Password Modification**: Credentials were modified shortly prior to order authorization.")
    if float(txn.get("unfamiliar_recipient_probability", 0)) >= 0.4:
        reasons.append(f"👤 **Unfamiliar Beneficiary**: Transfer directed toward an unverified third-party account.")
    if cat in ["crypto", "gift_cards", "wire_transfer", "electronics"]:
        reasons.append(f"💳 **High Liquidity Category ({cat.replace('_', ' ').title()})**: Target category allows instant monetization/cashout.")

    if not reasons:
        if desc:
            reasons.append(f"📌 {desc}")
        else:
            reasons.append("Behavioral telemetry and transactional metrics crossed elevated risk thresholds.")

    reasons_formatted = "\n".join(f"- {r}" for r in reasons)

    return (
        f"### 🔍 Forensic Investigation Summary for {user} ({acc})\n\n"
        f"This transaction was evaluated as **{risk_label}** with a **Final Risk Score of {f_risk:.2f}** "
        f"(Telemetry Risk: `{t_risk:.2f}`, Transaction Risk: `{tx_risk:.2f}`) under scenario *\"{rule}\"*.\n\n"
        f"#### **Why it was flagged:**\n"
        f"{reasons_formatted}\n\n"
        f"#### **Analyst Recommendation:**\n"
        f"The combination of telemetry risk metrics ({t_risk:.2f}) and transactional behavior ({tx_risk:.2f}) indicates elevated fraud likelihood. "
        f"You can generate an automated detection rule below to block or step-up authentication for similar patterns."
    )


class InvestigatorAgent:
    """Explains a flagged alert in plain language using a model call or forensic explainer engine."""

    MAX_TOKENS = 300

    def __init__(self, provider: Optional[BaseLLMProvider] = None) -> None:
        self.provider = provider

    async def explain(self, alert: dict) -> str:
        """Call LLM provider if available, or return clear forensic explanation."""
        if not alert:
            return "No alert data provided — cannot generate explanation."

        try:
            if self.provider:
                system_prompt = INVESTIGATOR_SYSTEM_PROMPT
                user_prompt = build_investigator_user_prompt(alert)
                explanation = await self.provider.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    max_tokens=self.MAX_TOKENS,
                )
                if explanation and len(explanation.strip()) > 15 and "ModelProviderError" not in explanation:
                    return explanation
        except Exception:
            pass

        return generate_forensic_explanation(alert)
