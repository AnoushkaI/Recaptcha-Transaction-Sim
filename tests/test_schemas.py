"""
Unit tests for core schemas (Data Contracts).
"""

import pytest
from datetime import datetime
from backend.core.schemas import (
    Transaction,
    FlaggedAlert,
    Rule,
    CustomProfile,
    ValidationResult,
    GuardResult,
    AuditLogEntry
)


def test_transaction_schema():
    tx_data = {
        "id": "tx_1001",
        "account_id": "acc_550",
        "amount": 1250.75,
        "location": "US-CA",
        "timestamp": "2026-07-27T11:00:00Z",
        "account_age_days": 10,
        "merchant_category": "electronics",
        "device_id": "dev_9910",
        "is_international": False
    }
    tx = Transaction(**tx_data)
    assert tx.id == "tx_1001"
    assert tx.amount == 1250.75
    assert tx.is_international is False
    assert tx.model_dump()["merchant_category"] == "electronics"


def test_flagged_alert_schema():
    tx = Transaction(
        id="tx_1002",
        account_id="acc_551",
        amount=5000.0,
        location="RU-MOS",
        timestamp="2026-07-27T11:05:00Z",
        account_age_days=2,
        merchant_category="crypto",
        device_id="dev_8812",
        is_international=True
    )
    alert = FlaggedAlert(
        id="alt_001",
        transaction_id=tx.id,
        rule_id="rule_high_crypto",
        rule_name="High Crypto New Account",
        score=0.95,
        flagged_at="2026-07-27T11:05:01Z",
        transaction_details=tx
    )
    assert alert.transaction_details.amount == 5000.0
    assert alert.score == 0.95


def test_rule_schema():
    rule = Rule(
        id="rule_001",
        name="High Amount Rule",
        code="def evaluate(tx):\n    return tx.amount > 1000",
        description="Flag transactions over $1000",
        created_at="2026-07-27T10:00:00Z",
        status="active",
        created_by_command="Flag high amount transactions"
    )
    assert rule.status == "active"
    assert "tx.amount > 1000" in rule.code


def test_custom_profile_defaults():
    profile = CustomProfile(name="high_risk")
    assert profile.name == "high_risk"
    assert profile.high_risk_location_bias == 0.0
    assert profile.amount_min is None


def test_validation_result():
    res_valid = ValidationResult(valid=True)
    assert res_valid.valid is True
    assert res_valid.error is None

    res_invalid = ValidationResult(valid=False, error="Disallowed import 'os' on line 2", line_number=2)
    assert res_invalid.valid is False
    assert "os" in res_invalid.error
    assert res_invalid.line_number == 2


def test_guard_result():
    guard_pass = GuardResult(passed=True)
    assert guard_pass.passed is True

    guard_fail = GuardResult(
        passed=False,
        reason="Rule cap of 20 active rules reached",
        similarity_score=None
    )
    assert guard_fail.passed is False
    assert "20 active rules" in guard_fail.reason


def test_audit_log_entry():
    entry = AuditLogEntry(
        id=1,
        rule_id="rule_001",
        timestamp="2026-07-27T11:00:00Z",
        command="DEPLOY_RULE",
        code="def evaluate(tx): return tx.amount > 1000",
        status="ACTIVE",
        prev_hash="0000000000000000000000000000000000000000000000000000000000000000",
        hash="a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890a1b2c3d4e5f67890"
    )
    assert entry.command == "DEPLOY_RULE"
    assert entry.hash.startswith("a1b2")
