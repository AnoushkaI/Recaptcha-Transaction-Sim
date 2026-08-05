"""
Comprehensive unit tests for core schemas (Data Contracts) targeting 100% coverage.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from backend.core.schemas import (
    Transaction,
    FlaggedAlert,
    Rule,
    CustomProfile,
    ValidationResult,
    GuardResult,
    AuditLogEntry
)


# --------------- Transaction ---------------

def test_transaction_all_fields():
    tx = Transaction(
        id="tx_1001", account_id="acc_550", amount=1250.75,
        location="DEL-BLR", timestamp="2026-07-27T11:00:00Z",
        account_age_days=10, merchant_category="electronics",
        device_id="dev_9910", is_international=False
    )
    assert tx.id == "tx_1001"
    assert tx.amount == 1250.75
    assert tx.is_international is False
    assert tx.model_dump()["merchant_category"] == "electronics"


def test_transaction_default_is_international():
    """is_international defaults to False."""
    tx = Transaction(
        id="tx_def", account_id="acc_1", amount=100.0,
        location="MUM-DEL", timestamp="2026-07-27T10:00:00Z",
        account_age_days=30, merchant_category="groceries",
        device_id="dev_1"
    )
    assert tx.is_international is False


def test_transaction_missing_required_field_raises():
    with pytest.raises(ValidationError):
        Transaction(
            id="tx_bad", account_id="acc_1", amount=100.0
            # Missing required fields
        )


def test_transaction_json_schema_extra_example():
    """Exercises ConfigDict json_schema_extra path."""
    schema = Transaction.model_json_schema()
    assert "example" in schema


def test_transaction_model_fields_set():
    """model_fields should expose all declared field names for validator use."""
    fields = set(Transaction.model_fields.keys())
    assert "id" in fields
    assert "amount" in fields
    assert "merchant_category" in fields
    assert "is_international" in fields


# --------------- FlaggedAlert ---------------

def test_flagged_alert_full():
    tx = Transaction(
        id="tx_1002", account_id="acc_551", amount=5000.0,
        location="MUM-JMT", timestamp="2026-07-27T11:05:00Z",
        account_age_days=2, merchant_category="crypto",
        device_id="dev_8812", is_international=True
    )
    alert = FlaggedAlert(
        id="alt_001", transaction_id=tx.id, rule_id="rule_high_crypto",
        rule_name="High Crypto New Account", score=0.95,
        flagged_at="2026-07-27T11:05:01Z", transaction_details=tx
    )
    assert alert.transaction_details.amount == 5000.0
    assert alert.score == 0.95
    assert alert.transaction_details.is_international is True


def test_flagged_alert_default_score():
    """score defaults to 1.0."""
    tx = Transaction(
        id="tx_score", account_id="acc_1", amount=100.0,
        location="MUM-DEL", timestamp="2026-07-27T10:00:00Z",
        account_age_days=30, merchant_category="groceries", device_id="dev_1"
    )
    alert = FlaggedAlert(
        id="alt_default", transaction_id="tx_score",
        rule_id="rule_x", rule_name="X", flagged_at="2026-07-27T10:00:01Z",
        transaction_details=tx
    )
    assert alert.score == 1.0


def test_flagged_alert_missing_required_raises():
    with pytest.raises(ValidationError):
        FlaggedAlert(id="alt_bad")


# --------------- Rule ---------------

def test_rule_all_fields():
    rule = Rule(
        id="rule_001", name="High Amount Rule",
        code="def evaluate(tx):\n    return tx.amount > 1000",
        description="Flag transactions over $1000",
        created_at="2026-07-27T10:00:00Z", status="active",
        created_by_command="Flag high amount transactions"
    )
    assert rule.status == "active"
    assert "tx.amount > 1000" in rule.code


def test_rule_default_status():
    """status defaults to 'active'."""
    rule = Rule(
        id="rule_002", name="New Rule",
        code="def evaluate(tx): return True",
        description="desc", created_at="2026-07-27T10:00:00Z",
        created_by_command="cmd"
    )
    assert rule.status == "active"


def test_rule_reverted_status():
    rule = Rule(
        id="rule_003", name="Reverted Rule",
        code="def evaluate(tx): return True",
        description="desc", created_at="2026-07-27T10:00:00Z",
        status="reverted", created_by_command="cmd"
    )
    assert rule.status == "reverted"


# --------------- CustomProfile ---------------

def test_custom_profile_defaults():
    profile = CustomProfile(name="high_risk")
    assert profile.name == "high_risk"
    assert profile.high_risk_location_bias == 0.0
    assert profile.new_account_bias == 0.0
    assert profile.amount_min is None
    assert profile.amount_max is None
    assert profile.merchant_category_filter is None


def test_custom_profile_default_name():
    """name defaults to 'custom'."""
    profile = CustomProfile()
    assert profile.name == "custom"


def test_custom_profile_all_fields():
    profile = CustomProfile(
        name="extreme_risk",
        amount_min=5000.0,
        amount_max=15000.0,
        high_risk_location_bias=0.9,
        new_account_bias=0.8,
        merchant_category_filter=["crypto", "wire_transfer"]
    )
    assert profile.amount_min == 5000.0
    assert profile.amount_max == 15000.0
    assert profile.merchant_category_filter == ["crypto", "wire_transfer"]


# --------------- ValidationResult ---------------

def test_validation_result_valid():
    res = ValidationResult(valid=True)
    assert res.valid is True
    assert res.error is None
    assert res.line_number is None


def test_validation_result_invalid_with_line():
    res = ValidationResult(valid=False, error="Disallowed import 'os' on line 2", line_number=2)
    assert res.valid is False
    assert "os" in res.error
    assert res.line_number == 2


def test_validation_result_invalid_without_line():
    res = ValidationResult(valid=False, error="Rule code cannot be empty")
    assert res.valid is False
    assert res.line_number is None


# --------------- GuardResult ---------------

def test_guard_result_pass():
    guard = GuardResult(passed=True)
    assert guard.passed is True
    assert guard.reason is None
    assert guard.similarity_score is None
    assert guard.duplicate_rule_id is None


def test_guard_result_fail_cap():
    guard = GuardResult(passed=False, reason="Rule capacity cap reached (20/20 active rules)")
    assert guard.passed is False
    assert "cap reached" in guard.reason


def test_guard_result_fail_duplicate():
    guard = GuardResult(
        passed=False,
        reason="Duplicate rule detected (similarity 0.91 >= threshold 0.85) with existing rule 'rule_abc'.",
        similarity_score=0.91,
        duplicate_rule_id="rule_abc"
    )
    assert guard.similarity_score == 0.91
    assert guard.duplicate_rule_id == "rule_abc"


# --------------- AuditLogEntry ---------------

def test_audit_log_entry_full():
    entry = AuditLogEntry(
        id=1, rule_id="rule_001", timestamp="2026-07-27T11:00:00Z",
        command="DEPLOY_RULE", code="def evaluate(tx): return tx.amount > 1000",
        status="ACTIVE",
        prev_hash="0" * 64, hash="a1b2c3d4" + "0" * 56
    )
    assert entry.command == "DEPLOY_RULE"
    assert entry.id == 1
    assert entry.hash.startswith("a1b2c3d4")


def test_audit_log_entry_no_id():
    """id is optional (None default)."""
    entry = AuditLogEntry(
        rule_id="rule_002", timestamp="2026-07-27T11:00:00Z",
        command="REVERT_RULE", code="def evaluate(tx): return True",
        status="REVERTED", prev_hash="0" * 64, hash="b2c3d4e5" + "0" * 56
    )
    assert entry.id is None
