"""
Unit and Integration Tests for Telemetry & Risk Scoring Engine (`backend/scoring/engine.py`).

Verifies calculations, sub-score logic, risk weightings, and deterministic classifications
against the authoritative specification in formulae.docx.
"""

import pytest
from backend.scoring.engine import (
    calculate_typing_score,
    calculate_telemetry_score,
    calculate_telemetry_risk_score,
    calculate_merchant_risk,
    calculate_transaction_risk_score,
    calculate_final_risk_score,
    classify_risk,
    evaluate_transaction,
    ScoringResult,
    MERCHANT_RISK_MAP,
)
from backend.core.schemas import Transaction


def test_typing_score_perfect_human():
    """Verify typing score for average CPM (220) and 0 error rate."""
    score = calculate_typing_score(typing_speed_cpm=220.0, typing_error_rate=0.0)
    assert score == 1.0


def test_typing_score_deviation():
    """Verify typing score degradation when typing speed or error rate deviates."""
    score = calculate_typing_score(typing_speed_cpm=110.0, typing_error_rate=0.1)
    # speed_diff = |110 - 220| / 220 = 0.5
    # speed_score = 1 - 0.5 = 0.5
    # error_score = 1 - 0.1 = 0.9
    # T = 0.7 * 0.5 + 0.3 * 0.9 = 0.35 + 0.27 = 0.62
    assert score == 0.62


def test_telemetry_score_worked_example():
    """
    Verify TelemetryScore & TelemetryRiskScore matching formulae.docx worked example (Page 5).
    Mouse=0.20, Typing=0.40, Scroll=0.30, DeviceRep=0.30, IPRep=0.25,
    Automation=0.90, VPN=0.80, Tor=0.20
    """
    telemetry_score = calculate_telemetry_score(
        mouse_movement_quality=0.20,
        typing_score=0.40,
        scroll_behavior=0.30,
        device_reputation=0.30,
        ip_reputation=0.25,
        automation_probability=0.90,
        vpn_probability=0.80,
        tor_probability=0.20,
    )
    # 0.18(0.20)+0.17(0.40)+0.10(0.30)+0.18(0.30)+0.17(0.25)+0.10(0.10)+0.05(0.20)+0.05(0.80)
    # = 0.036 + 0.068 + 0.030 + 0.054 + 0.0425 + 0.010 + 0.010 + 0.040 = 0.2905
    assert abs(telemetry_score - 0.2905) < 1e-3

    telemetry_risk = calculate_telemetry_risk_score(telemetry_score)
    assert abs(telemetry_risk - (1.0 - 0.2905)) < 1e-3


def test_merchant_risk_mappings():
    """Verify fixed merchant category risk mapping from formulae.docx 3E."""
    assert calculate_merchant_risk("gift_cards") == 1.00
    assert calculate_merchant_risk("crypto") == 0.90
    assert calculate_merchant_risk("digital_goods") == 0.80
    assert calculate_merchant_risk("electronics") == 0.60
    assert calculate_merchant_risk("fashion") == 0.40
    assert calculate_merchant_risk("groceries") == 0.10
    assert calculate_merchant_risk("utilities") == 0.05
    assert calculate_merchant_risk("unknown_merchant_type") == 0.30


def test_transaction_risk_worked_example():
    """
    Verify TransactionRiskScore matching formulae.docx worked example (Page 6).
    Sub-scores: Amount=0.80, Account=0.90, Device=0.70, Velocity=0.80, Merchant=0.60, Security=0.75
    TransactionRiskScore = 0.30(0.80)+0.20(0.90)+0.15(0.70)+0.15(0.80)+0.10(0.60)+0.10(0.75) = 0.78
    """
    payload = {
        "sub_scores": {
            "amount_risk": 0.80,
            "account_risk": 0.90,
            "device_risk": 0.70,
            "velocity_risk": 0.80,
            "merchant_risk": 0.60,
            "security_risk": 0.75,
        },
        "typing_score": 0.40,
        "mouse_movement_quality": 0.20,
        "scroll_behavior": 0.30,
        "device_reputation": 0.30,
        "ip_reputation": 0.25,
        "automation_probability": 0.90,
        "vpn_probability": 0.80,
        "tor_probability": 0.20,
    }

    result = evaluate_transaction(payload)
    assert abs(result.transaction_risk_score - 0.78) < 1e-2


def test_final_risk_score_and_classification_worked_example():
    """
    Verify FinalRiskScore and Classification matching formulae.docx (Page 6).
    TelemetryRiskScore = 0.75, TransactionRiskScore = 0.78
    FinalRiskScore = 0.40(0.75) + 0.60(0.78) = 0.768 -> 0.77
    Classification = HIGH_RISK
    """
    final_score = calculate_final_risk_score(telemetry_risk_score=0.75, transaction_risk_score=0.78)
    assert abs(final_score - 0.768) < 1e-3
    assert classify_risk(final_score) == "HIGH_RISK"


def test_classification_thresholds():
    """Verify deterministic classification boundaries."""
    assert classify_risk(0.00) == "SAFE"
    assert classify_risk(0.29) == "SAFE"
    assert classify_risk(0.30) == "SUSPICIOUS"
    assert classify_risk(0.59) == "SUSPICIOUS"
    assert classify_risk(0.60) == "HIGH_RISK"
    assert classify_risk(1.00) == "HIGH_RISK"


def test_evaluate_transaction_dashboard_response_format():
    """
    Verify evaluate_transaction returns all mandatory fields expected by backend response:
    telemetry_risk_score, transaction_risk_score, final_risk_score, classification.
    """
    tx = Transaction(
        id="tx_test_99",
        account_id="acc_1001",
        amount=1500.0,
        location="US-NY",
        timestamp="2026-07-30T10:00:00Z",
        account_age_days=10,
        merchant_category="crypto",
        device_id="dev_55",
        is_international=True,
        mouse_movement_quality=0.20,
        typing_speed_cpm=100.0,
        typing_error_rate=0.25,
        automation_probability=0.85,
        vpn_probability=0.75,
        tor_probability=0.30,
        refund_attempts=2,
    )

    result = evaluate_transaction(tx)

    assert isinstance(result, ScoringResult)
    assert 0.0 <= result.telemetry_risk_score <= 1.0
    assert 0.0 <= result.transaction_risk_score <= 1.0
    assert 0.0 <= result.final_risk_score <= 1.0
    assert result.classification in ["SAFE", "SUSPICIOUS", "HIGH_RISK"]
