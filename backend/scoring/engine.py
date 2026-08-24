"""
Deterministic Telemetry & Risk Scoring Engine (`backend/scoring/engine.py`)

Authoritative Implementation of formulae.docx specification.

Calculates:
1. Typing Score & Telemetry Score
2. Telemetry Risk Score
3. Transaction Sub-Scores & Transaction Risk Score
4. Final Risk Score
5. Deterministic Risk Classification (SAFE, SUSPICIOUS, HIGH_RISK)
"""

from typing import Dict, Any, Union, Optional
from pydantic import BaseModel, Field, ConfigDict


# Merchant category fixed risk lookup table (from formulae.docx 3E)
MERCHANT_RISK_MAP: Dict[str, float] = {
    "gift_cards": 1.00,
    "gift_card": 1.00,
    "giftcards": 1.00,
    "crypto": 0.90,
    "cryptocurrency": 0.90,
    "digital_goods": 0.80,
    "digital": 0.80,
    "electronics": 0.60,
    "fashion": 0.40,
    "clothing": 0.40,
    "groceries": 0.10,
    "grocery": 0.10,
    "utilities": 0.05,
    "utility": 0.05,
}
DEFAULT_MERCHANT_RISK: float = 0.30


class SubScores(BaseModel):
    """Breakdown of individual transaction risk sub-scores."""
    amount_risk: float = Field(..., ge=0.0, le=1.0)
    account_risk: float = Field(..., ge=0.0, le=1.0)
    device_risk: float = Field(..., ge=0.0, le=1.0)
    velocity_risk: float = Field(..., ge=0.0, le=1.0)
    merchant_risk: float = Field(..., ge=0.0, le=1.0)
    security_risk: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(extra="ignore")


class ScoringResult(BaseModel):
    """Complete scoring pipeline output conforming to dashboard specification."""
    typing_score: float = Field(..., ge=0.0, le=1.0)
    telemetry_score: float = Field(..., ge=0.0, le=1.0)
    telemetry_risk_score: float = Field(..., ge=0.0, le=1.0)
    transaction_risk_score: float = Field(..., ge=0.0, le=1.0)
    final_risk_score: float = Field(..., ge=0.0, le=1.0)
    classification: str = Field(..., description="SAFE, SUSPICIOUS, or HIGH_RISK")
    sub_scores: Optional[SubScores] = Field(default=None)

    model_config = ConfigDict(extra="ignore")


def calculate_typing_score(typing_speed_cpm: float, typing_error_rate: float) -> float:
    """
    1A. Typing score formula:
    TypingScore = 0.7 * (1 - |CPM - 220| / 220) + 0.3 * (1 - ErrorRate)
    """
    cpm_diff = abs(typing_speed_cpm - 220.0) / 220.0
    speed_score = max(0.0, min(1.0, 1.0 - cpm_diff))
    error_score = max(0.0, min(1.0, 1.0 - float(typing_error_rate)))
    typing_score = 0.7 * speed_score + 0.3 * error_score
    return round(max(0.0, min(1.0, typing_score)), 4)


def calculate_telemetry_score(
    mouse_movement_quality: float,
    typing_score: float,
    scroll_behavior: float,
    device_reputation: float,
    ip_reputation: float,
    automation_probability: float,
    vpn_probability: float,
    tor_probability: float,
) -> float:
    """
    1B. Telemetry score formula:
    TelemetryScore = 0.18*M + 0.17*T + 0.10*S + 0.18*D + 0.17*I + 0.10*(1-A) + 0.05*(1-V) + 0.05*(1-R)
    """
    m = max(0.0, min(1.0, float(mouse_movement_quality)))
    t = max(0.0, min(1.0, float(typing_score)))
    s = max(0.0, min(1.0, float(scroll_behavior)))
    d = max(0.0, min(1.0, float(device_reputation)))
    i = max(0.0, min(1.0, float(ip_reputation)))
    a = max(0.0, min(1.0, float(automation_probability)))
    v = max(0.0, min(1.0, float(vpn_probability)))
    r = max(0.0, min(1.0, float(tor_probability)))

    score = (
        0.18 * m
        + 0.17 * t
        + 0.10 * s
        + 0.18 * d
        + 0.17 * i
        + 0.10 * (1.0 - a)
        + 0.05 * (1.0 - v)
        + 0.05 * (1.0 - r)
    )
    return round(max(0.0, min(1.0, score)), 4)


def calculate_telemetry_risk_score(telemetry_score: float) -> float:
    """
    Step 2: Calculate telemetry risk score
    TelemetryRiskScore = 1 - TelemetryScore
    """
    risk = 1.0 - float(telemetry_score)
    return round(max(0.0, min(1.0, risk)), 4)


def calculate_merchant_risk(merchant_category: str) -> float:
    """3E. Merchant risk category lookup."""
    cat = (merchant_category or "").strip().lower().replace(" ", "_")
    return MERCHANT_RISK_MAP.get(cat, DEFAULT_MERCHANT_RISK)


def calculate_transaction_risk_score(
    amount: float,
    average_amount: float,
    account_age_days: int,
    previous_transactions: int,
    known_device_probability: float,
    transaction_frequency_per_day: float,
    merchant_category: str,
    unfamiliar_recipient_probability: float,
    password_changed_recently_probability: float,
    refund_attempts: int,
) -> tuple[float, SubScores]:
    """
    Step 3: Calculate transaction risk score and normalized sub-scores.
    
    3A. Amount Risk = min(1, CurrentAmount / (AverageAmount * 3))
    3B. Account Risk = 0.6 * AgeFactor + 0.4 * HistoryFactor
        AgeFactor = 1 - min(1, AccountAgeDays / 365)
        HistoryFactor = 1 - min(1, PreviousTransactions / 100)
    3C. Device Risk = 1 - KnownDeviceProbability
    3D. Velocity Risk = min(1, TransactionFrequencyPerDay / 20)
    3E. Merchant Risk = Category Fixed Value
    3F. Security Risk = 0.4*UUU + 0.3*PPP + 0.3*min(1, RefundAttempts / 3)
    3G. TransactionRiskScore = 0.30*AmountRisk + 0.20*AccountRisk + 0.15*DeviceRisk + 0.15*VelocityRisk + 0.10*MerchantRisk + 0.10*SecurityRisk
    """
    # 3A. Amount Risk
    avg_amt = float(average_amount) if average_amount and float(average_amount) > 0 else float(amount)
    if avg_amt <= 0:
        avg_amt = 100.0
    amount_risk = min(1.0, float(amount) / (avg_amt * 3.0))

    # 3B. Account Risk
    age_factor = 1.0 - min(1.0, float(account_age_days) / 365.0)
    history_factor = 1.0 - min(1.0, float(previous_transactions) / 100.0)
    account_risk = 0.6 * age_factor + 0.4 * history_factor

    # 3C. Device Risk
    device_risk = 1.0 - max(0.0, min(1.0, float(known_device_probability)))

    # 3D. Velocity Risk
    velocity_risk = min(1.0, float(transaction_frequency_per_day) / 20.0)

    # 3E. Merchant Risk
    merchant_risk = calculate_merchant_risk(merchant_category)

    # 3F. Security Risk
    u = max(0.0, min(1.0, float(unfamiliar_recipient_probability)))
    p = max(0.0, min(1.0, float(password_changed_recently_probability)))
    refund_factor = min(1.0, float(refund_attempts) / 3.0)
    security_risk = 0.4 * u + 0.3 * p + 0.3 * refund_factor

    # Clamp sub-scores
    amount_risk = round(max(0.0, min(1.0, amount_risk)), 4)
    account_risk = round(max(0.0, min(1.0, account_risk)), 4)
    device_risk = round(max(0.0, min(1.0, device_risk)), 4)
    velocity_risk = round(max(0.0, min(1.0, velocity_risk)), 4)
    merchant_risk = round(max(0.0, min(1.0, merchant_risk)), 4)
    security_risk = round(max(0.0, min(1.0, security_risk)), 4)

    sub_scores = SubScores(
        amount_risk=amount_risk,
        account_risk=account_risk,
        device_risk=device_risk,
        velocity_risk=velocity_risk,
        merchant_risk=merchant_risk,
        security_risk=security_risk,
    )

    # 3G. Transaction Risk Score
    tx_risk_score = (
        0.30 * amount_risk
        + 0.20 * account_risk
        + 0.15 * device_risk
        + 0.15 * velocity_risk
        + 0.10 * merchant_risk
        + 0.10 * security_risk
    )
    tx_risk_score = round(max(0.0, min(1.0, tx_risk_score)), 4)

    return tx_risk_score, sub_scores


def calculate_final_risk_score(telemetry_risk_score: float, transaction_risk_score: float) -> float:
    """
    Step 4: Calculate final risk score
    FinalRiskScore = 0.40 * TelemetryRiskScore + 0.60 * TransactionRiskScore
    """
    final_score = 0.40 * float(telemetry_risk_score) + 0.60 * float(transaction_risk_score)
    return round(max(0.0, min(1.0, final_score)), 4)


def classify_risk(final_risk_score: float) -> str:
    """
    Step 5: Classify transaction based on deterministic thresholds
    0.00-0.30: SAFE
    0.30-0.60: SUSPICIOUS
    0.60-1.00: HIGH_RISK
    """
    score = float(final_risk_score)
    if score < 0.30:
        return "SAFE"
    elif score < 0.60:
        return "SUSPICIOUS"
    else:
        return "HIGH_RISK"


def evaluate_transaction(data: Union[Dict[str, Any], Any]) -> ScoringResult:
    """
    Main evaluation pipeline entry point.
    Accepts a dictionary or object with transaction & behavioral fields,
    computes all sub-scores, telemetry score, telemetry risk score,
    transaction risk score, final risk score, and classification.
    """
    def get_val(key: str, default: Any) -> Any:
        if isinstance(data, dict):
            val = data.get(key)
        else:
            val = getattr(data, key, None)
        return val if val is not None else default

    # Extract behavioral fields
    typing_speed_cpm = float(get_val("typing_speed_cpm", 220.0))
    typing_error_rate = float(get_val("typing_error_rate", 0.05))
    mouse_movement_quality = float(get_val("mouse_movement_quality", 0.80))
    scroll_behavior = float(get_val("scroll_behavior", 0.70))
    device_reputation = float(get_val("device_reputation", 0.85))
    ip_reputation = float(get_val("ip_reputation", 0.85))
    automation_probability = float(get_val("automation_probability", 0.05))
    vpn_probability = float(get_val("vpn_probability", 0.05))
    tor_probability = float(get_val("tor_probability", 0.01))

    # Allow direct override of typing_score if pre-calculated
    direct_typing_score = get_val("typing_score", None)
    if direct_typing_score is not None:
        typing_score = float(direct_typing_score)
    else:
        typing_score = calculate_typing_score(typing_speed_cpm, typing_error_rate)

    # 1. Telemetry Score
    telemetry_score = calculate_telemetry_score(
        mouse_movement_quality=mouse_movement_quality,
        typing_score=typing_score,
        scroll_behavior=scroll_behavior,
        device_reputation=device_reputation,
        ip_reputation=ip_reputation,
        automation_probability=automation_probability,
        vpn_probability=vpn_probability,
        tor_probability=tor_probability,
    )

    # 2. Telemetry Risk Score
    telemetry_risk_score = calculate_telemetry_risk_score(telemetry_score)

    # Extract transactional fields
    amount = float(get_val("amount", 100.0))
    average_amount = float(get_val("average_amount", get_val("average_transaction_amount_usd", amount)))
    account_age_days = int(get_val("account_age_days", 365))
    previous_transactions = int(get_val("previous_transactions", 50))
    known_device_prob = float(get_val("known_device_probability", 0.90))
    tx_freq_per_day = float(get_val("transaction_frequency_per_day", 3.0))
    merchant_category = str(get_val("merchant_category", "retail"))
    unfamiliar_recipient_prob = float(get_val("unfamiliar_recipient_probability", 0.10))
    password_changed_prob = float(get_val("password_changed_recently_probability", 0.05))
    refund_attempts = int(get_val("refund_attempts", 0))

    # Allow direct sub-scores if already calculated (e.g. in test benchmarks)
    direct_sub_scores = get_val("sub_scores", None)
    if direct_sub_scores and isinstance(direct_sub_scores, dict):
        sub_scores = SubScores(**direct_sub_scores)
        tx_risk_score = round(
            0.30 * sub_scores.amount_risk
            + 0.20 * sub_scores.account_risk
            + 0.15 * sub_scores.device_risk
            + 0.15 * sub_scores.velocity_risk
            + 0.10 * sub_scores.merchant_risk
            + 0.10 * sub_scores.security_risk,
            4
        )
    else:
        # 3. Transaction Risk Score
        tx_risk_score, sub_scores = calculate_transaction_risk_score(
            amount=amount,
            average_amount=average_amount,
            account_age_days=account_age_days,
            previous_transactions=previous_transactions,
            known_device_probability=known_device_prob,
            transaction_frequency_per_day=tx_freq_per_day,
            merchant_category=merchant_category,
            unfamiliar_recipient_probability=unfamiliar_recipient_prob,
            password_changed_recently_probability=password_changed_prob,
            refund_attempts=refund_attempts,
        )

    # 4. Final Risk Score
    final_risk_score = calculate_final_risk_score(telemetry_risk_score, tx_risk_score)

    # 5. Classification
    classification = classify_risk(final_risk_score)

    return ScoringResult(
        typing_score=typing_score,
        telemetry_score=telemetry_score,
        telemetry_risk_score=telemetry_risk_score,
        transaction_risk_score=tx_risk_score,
        final_risk_score=final_risk_score,
        classification=classification,
        sub_scores=sub_scores,
    )
