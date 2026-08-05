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


def _build_dynamic_narrative(txn: dict, alert: dict, user: str, acc: str, amt: float, cat: str, loc: str, age: int, rule: str, desc: str) -> str:
    """Generates a rich, highly specific 2-3 line narrative that directly explains the transaction description details."""
    desc_clean = (desc or "").strip()
    desc_lower = desc_clean.lower()
    rule_lower = (rule or "").lower()

    # 1. Untraceable / Temporary email delivery
    if "untraceable email" in desc_lower or "disposable email" in desc_lower or "untraceable" in desc_lower:
        return (
            f"Customer {user} ({acc}) attempted a purchase of ₹{amt:,.0f} for digital gaming codes that were immediately routed to an untraceable email address. "
            f"Perpetrators frequently target digital gaming vouchers because they can be redeemed instantly without physical shipping or identity checks. "
            f"Sending purchase codes to a disposable third-party email indicates an active cashout attempt using compromised payment credentials."
        )

    # 2. Unverified recipient / Third-party voucher transfer
    if "unverified recipient" in desc_lower or "unfamiliar recipient" in desc_lower or "routed to" in desc_lower:
        return (
            f"A ₹{amt:,.0f} digital voucher transfer was initiated on account {acc} ({user}) originating from network location {loc}. "
            f"The transaction explicitly requested delivery to an unverified recipient account in a foreign jurisdiction. "
            f"This behavior is characteristic of money-mule cashout networks, where stolen funds are converted into vouchers and funneled offshore before detection."
        )

    # 3. Rapid succession / Multiple high-denomination gift cards
    if "rapid succession" in desc_lower or "multiple high-denomination" in desc_lower or "storm" in desc_lower:
        return (
            f"Customer {user} ({acc}) placed an accelerated order for ₹{amt:,.0f} across multiple high-denomination gift cards in rapid succession. "
            f"Purchasing multiple gift cards within minutes on an account registered {age} days ago from connection point {loc} is a primary indicator of automated card draining, "
            f"designed to maximize payout value before security filters block the compromised account."
        )

    # 4. Password / Email preference modification prior to transaction
    if "password" in desc_lower or "email notification" in desc_lower or "preference" in desc_lower or "changed right before" in desc_lower:
        return (
            f"Security logs recorded a critical account modification on customer {user}'s account ({acc}) right before submitting a ₹{amt:,.0f} order from location {loc}. "
            f"In account takeover (ATO) attacks, fraudsters alter notification preferences first to lock out the genuine cardholder and prevent real-time transaction alerts. "
            f"Executing a purchase immediately following credential changes confirms high ATO vulnerability."
        )

    # 5. Anonymized TOR / VPN / Proxy
    if "tor" in desc_lower or "vpn" in desc_lower or "proxy" in desc_lower:
        return (
            f"An order of ₹{amt:,.0f} for {cat} was placed on account {acc} ({user}) using an anonymized TOR or proxy relay in {loc}. "
            f"Masking true network origin while executing high-value digital orders is a high-confidence indicator of cybercrime tools operating behind hidden network relays. "
            f"The transaction was flagged to prevent untraceable unauthorized checkouts."
        )

    # 6. Micro-charge / Card testing
    if "micro" in desc_lower or "card testing" in desc_lower or "bin" in desc_lower or "1.00" in desc_lower:
        return (
            f"An automated micro-charge authorization of ₹{amt:,.0f} was attempted on account {acc} belonging to customer {user}. "
            f"Originating from location {loc}, this high-frequency charge matches card testing behavior used to validate stolen credit card numbers across merchant portals. "
            f"Automated scripts run low-value tests to confirm active card status before executing larger fraudulent purchases."
        )

    # 7. High-value / Luxury item purchase
    if "high-value" in desc_lower or "luxury" in desc_lower or "high amount" in desc_lower:
        return (
            f"An unusually large transaction of ₹{amt:,.0f} in category '{cat}' was placed on account {acc} ({user}). "
            f"The order originated from connection point {loc} and significantly exceeds typical spending patterns for an account registered {age} days ago. "
            f"Such sudden high-value spikes from foreign network points present severe unauthorized payment exposure."
        )

    # 8. New Account / Bust-out
    if age <= 14 or "new account" in desc_lower or "fresh account" in desc_lower:
        return (
            f"Customer {user} ({acc}) attempted a purchase of ₹{amt:,.0f} for {cat} from location {loc}. "
            f"The account was created only {age} days ago, exhibiting rapid high-risk order placement characteristic of synthetic identity fraud. "
            f"Newly registered accounts making substantial purchases require enhanced verification before fulfillment."
        )

    # 9. Generic Fallback incorporating full description detail
    if desc_clean and "Automated risk detection" not in desc_clean:
        return (
            f"During live risk monitoring, customer {user} ({acc}) submitted a ₹{amt:,.0f} transaction in {cat} from location {loc}. "
            f"Transaction details: \"{desc_clean}\". "
            f"This specific activity triggered security scenario '{rule}', indicating potential unauthorized checkout exposure."
        )

    return (
        f"During live risk monitoring, customer {user} ({acc}) submitted an order of ₹{amt:,.0f} in {cat} from location {loc}. "
        f"The order crossed established risk evaluation baselines for security scenario '{rule}'."
    )



def _build_dynamic_flags(txn: dict, alert: dict, user: str, acc: str, amt: float, cat: str, loc: str, age: int, rule: str, desc: str, vpn_prob: float, tor_prob: float, ip_rep: float) -> list[str]:
    """Generates a custom list of transaction-specific Key Warning Flags based on what is happening in the transaction."""
    flags = []
    desc_clean = (desc or "").strip()
    desc_lower = desc_clean.lower()
    rule_lower = (rule or "").lower()
    avg_amt = float(txn.get("average_amount") or 200.0)

    # 1. Description-specific threat flags
    if "untraceable email" in desc_lower or "disposable email" in desc_lower or "untraceable" in desc_lower:
        flags.append("- **Untraceable Email Address**: Order codes sent to a disposable/anonymous email domain (temp-mail inbox).")

    if "unverified recipient" in desc_lower or "unfamiliar recipient" in desc_lower or "routed to" in desc_lower:
        flags.append("- **Unverified Recipient Routing**: Digital assets funneled to an unverified third-party account (mule account indicator).")

    if "rapid succession" in desc_lower or "multiple high-denomination" in desc_lower or "storm" in desc_lower:
        flags.append("- **Rapid Succession Purchasing**: Multiple high-denomination gift vouchers bought within a compressed time window.")

    if "password" in desc_lower or "email notification" in desc_lower or "preference" in desc_lower or "changed right before" in desc_lower:
        flags.append("- **Recent Credential Modification**: Account email/password preferences were altered immediately prior to checkout.")
        flags.append("- **Notification Diversion Tactic**: Settings change prevents real-time SMS/email alerts from reaching genuine account owner.")

    if "micro" in desc_lower or "card testing" in desc_lower or "bin" in desc_lower:
        flags.append("- **High-Velocity Micro-Charge**: Low-value transaction matching automated card-testing validation scripts.")

    # 2. Network & Location Security Flags
    if vpn_prob >= 0.4 or tor_prob >= 0.15 or "vpn" in desc_lower or "tor" in desc_lower or "proxy" in desc_lower:
        flags.append("- **Anonymized Proxy Network**: Connection routed through a private VPN/TOR relay, masking origin network address.")

    if ip_rep <= 0.5:
        flags.append(f"- **Untrusted IP Reputation**: Connection IP address rated {ip_rep:.2f} on global threat intelligence feeds.")

    if loc in ["MUM-JMT", "DEL-NUH", "BLR-PAT", "DEL-LKO", "HYD-RNC"] or txn.get("is_international"):
        flags.append(f"- **High-Risk Overseas Region**: Transaction originated from international location {loc}, outside typical customer regional bounds.")

    # 3. Account Profile & Value Flags
    if age <= 14:
        flags.append(f"- **Fresh Account Exposure**: Account registered only {age} days ago, exhibiting high synthetic identity risk.")

    if amt > (avg_amt * 1.5):
        flags.append(f"- **Unusual Purchase Amount Spike**: Order value of ₹{amt:,.0f} in {cat} significantly exceeds baseline customer spending.")
    elif any(k in cat.lower() for k in ["digital", "gift", "gaming", "luxury", "electronics"]):
        flags.append(f"- **High-Liquidity Asset Category**: Purchase targeted easily redeemable digital/luxury merchandise ({cat}).")

    # Ensure fallback
    if not flags:
        flags.append(f"- **Elevated Risk Pattern**: Transaction metrics for scenario '{rule}' crossed security baseline thresholds.")
        flags.append(f"- **Unusual Order Activity**: ₹{amt:,.0f} checkout in category {cat} from location {loc}.")

    return flags


def generate_forensic_explanation(alert: dict) -> str:
    """Generates an official SOC Security Investigation Report without emojis or raw telemetry."""
    if not alert:
        return "No transaction selected for investigation."

    txn = alert.get("transaction") or alert
    user = txn.get("user_name") or alert.get("user_name") or "Alex Morgan"
    acc = txn.get("account_id") or alert.get("account_id") or "acc_1001"
    amt = float(txn.get("amount") or alert.get("amount") or 0.0)
    loc = str(txn.get("location") or alert.get("location") or "MUM-DEL")
    cls_name = str(txn.get("classification") or alert.get("classification") or "HIGH_RISK")
    f_risk = float(txn.get("final_risk_score") or alert.get("final_risk_score") or alert.get("score") or 0.75)
    rule = str(txn.get("title") or alert.get("rule_triggered") or alert.get("title") or "Unusual Activity Detected")
    desc = str(txn.get("description") or alert.get("description") or "")
    cat = str(txn.get("merchant_category") or "general").replace("_", " ").title()
    age = int(txn.get("account_age_days") or 30)

    # Risk Assessment string without emojis
    if cls_name == "HIGH_RISK" or f_risk >= 0.60:
        risk_status = f"High Risk ({int(f_risk * 100)}% Risk Score)"
        action_text = (
            "1. Block this transaction immediately and initiate Step-Up Two-Factor Authentication (OTP) to verify account ownership.\n"
            "2. **Attack Mitigation Option:** To terminate and prevent future attacks of this pattern across your platform, click **\"Generate rule\"** below to deploy an automated countermeasure rule."
        )
    elif cls_name == "SUSPICIOUS" or f_risk >= 0.30:
        risk_status = f"Suspicious ({int(f_risk * 100)}% Risk Score)"
        action_text = (
            "1. Hold order for secondary manual security review and request secondary identity verification.\n"
            "2. **Attack Mitigation Option:** To terminate and prevent future attacks of this pattern across your platform, click **\"Generate rule\"** below to deploy an automated countermeasure rule."
        )
    else:
        risk_status = f"Safe ({int(f_risk * 100)}% Risk Score)"
        action_text = "Transaction meets standard risk parameters and is approved for normal processing."


    vpn_prob = float(txn.get("vpn_probability") or 0)
    tor_prob = float(txn.get("tor_probability") or 0)
    ip_rep = float(txn.get("ip_reputation") or 1.0)

    # Dynamic scenario-tailored 2-3 line narrative
    what_happened_narrative = _build_dynamic_narrative(txn, alert, user, acc, amt, cat, loc, age, rule, desc)

    # Dynamic transaction-specific Key Warning Flags
    flags = _build_dynamic_flags(txn, alert, user, acc, amt, cat, loc, age, rule, desc, vpn_prob, tor_prob, ip_rep)
    flags_formatted = "\n".join(flags)

    return (
        f"### Security Investigation Report: {user} ({acc})\n\n"
        f"**Risk Assessment:** {risk_status}  \n"
        f"**Security Scenario:** \"{rule}\"\n\n"
        f"**What Happened:**  \n"
        f"{what_happened_narrative}\n\n"
        f"---\n\n"
        f"### Key Warning Flags (Risk Indicators)\n\n"
        f"{flags_formatted}\n\n"
        f"---\n\n"
        f"### Recommended Action\n\n"
        f"{action_text}"
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
