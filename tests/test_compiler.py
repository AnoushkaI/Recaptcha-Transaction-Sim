"""
Unit tests for Rule Compiler (`core/compiler.py`).
"""

import pytest
from backend.core.schemas import Transaction, Rule
from backend.core.rules_engine import RulesEngine
from backend.core.compiler import RuleCompiler


def test_compile_rule_code():
    compiler = RuleCompiler()
    code = """
def evaluate(tx):
    return tx.amount > 500.0 and tx.location == 'US-NY'
"""
    func = compiler.compile_rule_code(code)
    assert callable(func)

    tx_match = Transaction(
        id="tx_1", account_id="acc_1", amount=750.0, location="US-NY",
        timestamp="2026-07-27T12:00:00Z", account_age_days=100,
        merchant_category="groceries", device_id="dev_1", is_international=False
    )
    tx_no_match = Transaction(
        id="tx_2", account_id="acc_2", amount=250.0, location="US-NY",
        timestamp="2026-07-27T12:00:00Z", account_age_days=100,
        merchant_category="groceries", device_id="dev_2", is_international=False
    )

    assert func(tx_match) is True
    assert func(tx_no_match) is False


def test_compile_and_register_hot_reload():
    compiler = RuleCompiler()
    engine = RulesEngine()

    rule = Rule(
        id="rule_compiler_test",
        name="Compiler Test Rule",
        code="def evaluate(tx):\n    return tx.account_age_days < 5",
        description="Flag new accounts",
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command="Flag new accounts"
    )

    compiler.compile_and_register(rule, engine)
    assert "rule_compiler_test" in engine.get_active_rule_ids()

    tx = Transaction(
        id="tx_new", account_id="acc_new", amount=50.0, location="US-CA",
        timestamp="2026-07-27T12:00:00Z", account_age_days=2,
        merchant_category="retail", device_id="dev_new", is_international=False
    )
    alerts = engine.score_transaction(tx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "rule_compiler_test"


def test_invalid_compilation_raises():
    compiler = RuleCompiler()
    code_invalid = "def wrong_name(tx): return True"
    with pytest.raises(ValueError, match=r"must contain a callable 'evaluate\(tx\)' function"):
        compiler.compile_rule_code(code_invalid)
