"""
Unit tests for Rule Guard (`core/rule_guard.py`).
"""

import pytest
from backend.core.schemas import Rule
from backend.core.rule_guard import RuleGuard, canonicalize_rule


def create_dummy_rule(rule_id: str, name: str, code: str, desc: str, cmd: str) -> Rule:
    return Rule(
        id=rule_id,
        name=name,
        code=code,
        description=desc,
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command=cmd
    )


def test_rule_cap_exceeded():
    guard = RuleGuard(max_rules_cap=20)
    
    # Create 20 active rules
    active_rules = [
        create_dummy_rule(
            rule_id=f"rule_{i}",
            name=f"Rule {i}",
            code=f"def evaluate(tx): return tx.amount > {1000 + i}",
            desc=f"Rule description {i}",
            cmd=f"command {i}"
        ) for i in range(20)
    ]

    proposed = create_dummy_rule(
        rule_id="rule_21",
        name="Rule 21",
        code="def evaluate(tx): return tx.account_age_days < 5",
        desc="New account check",
        cmd="Flag new account"
    )

    res = guard.evaluate_rule(proposed, active_rules)
    assert res.passed is False
    assert "20/20 active rules" in res.reason


def test_duplicate_rule_rejected():
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.80)

    existing = create_dummy_rule(
        rule_id="rule_high_crypto",
        name="High Crypto Transaction",
        code="def evaluate(tx):\n    return tx.amount > 2000 and tx.merchant_category == 'crypto'",
        desc="Flag high amount crypto transactions over $2000",
        cmd="Flag high crypto transactions over $2000"
    )

    proposed_duplicate = create_dummy_rule(
        rule_id="rule_crypto_high",
        name="High Crypto Transaction Alert",
        code="def evaluate(tx):\n    return tx.amount > 2000 and tx.merchant_category == 'crypto'",
        desc="Flag high amount crypto transactions over $2000",
        cmd="Flag high crypto transactions over $2000"
    )

    res = guard.evaluate_rule(proposed_duplicate, [existing])
    assert res.passed is False
    assert res.duplicate_rule_id == "rule_high_crypto"
    assert res.similarity_score is not None
    assert res.similarity_score >= 0.80


def test_distinct_rule_passes():
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.85)

    existing = create_dummy_rule(
        rule_id="rule_high_amount",
        name="High Amount Rule",
        code="def evaluate(tx): return tx.amount > 5000",
        desc="Flag transactions over $5000",
        cmd="Flag transactions over $5000"
    )

    proposed_distinct = create_dummy_rule(
        rule_id="rule_international_new_acc",
        name="International New Account",
        code="def evaluate(tx): return tx.is_international and tx.account_age_days < 7",
        desc="Flag cross border transactions on accounts younger than 7 days",
        cmd="Flag cross border new accounts"
    )

    res = guard.evaluate_rule(proposed_distinct, [existing])
    assert res.passed is True
    assert res.reason is None
