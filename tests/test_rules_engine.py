"""
Unit tests for live rules engine, including hot-reload and revert capabilities.
"""

import pytest
from backend.core.schemas import Transaction, Rule, FlaggedAlert
from backend.core.rules_engine import RulesEngine


def create_sample_tx(amount: float, location: str = "US-NY", age: int = 100) -> Transaction:
    return Transaction(
        id="tx_test_101",
        account_id="acc_9901",
        amount=amount,
        location=location,
        timestamp="2026-07-27T12:00:00Z",
        account_age_days=age,
        merchant_category="electronics",
        device_id="dev_001",
        is_international=False
    )


def test_rules_engine_scoring():
    engine = RulesEngine()

    rule1 = Rule(
        id="rule_high_amount",
        name="High Amount (> $1000)",
        code="def evaluate(tx): return tx.amount > 1000",
        description="Flag transactions over $1000",
        created_at="2026-07-27T10:00:00Z",
        status="active",
        created_by_command="Flag >1000"
    )

    func1 = lambda tx: tx.amount > 1000
    engine.register_rule(rule1, func1)

    tx_normal = create_sample_tx(amount=250.0)
    alerts_normal = engine.score_transaction(tx_normal)
    assert len(alerts_normal) == 0

    tx_high = create_sample_tx(amount=1500.0)
    alerts_high = engine.score_transaction(tx_high)
    assert len(alerts_high) == 1
    assert alerts_high[0].rule_id == "rule_high_amount"
    assert alerts_high[0].transaction_details.amount == 1500.0


def test_rules_engine_hot_reload():
    """
    Test hot-reload: deploy a new rule mid-run, confirm the very next transaction
    batch is scored against it without restarting.
    """
    engine = RulesEngine()

    # Initially 0 rules
    tx = create_sample_tx(amount=500.0, location="RU-MOS")
    assert len(engine.score_transaction(tx)) == 0

    # Hot-reload rule mid-run
    new_rule = Rule(
        id="rule_ru_location",
        name="Flag Moscow Location",
        code="def evaluate(tx): return tx.location == 'RU-MOS'",
        description="Flag RU-MOS",
        created_at="2026-07-27T10:05:00Z",
        status="active",
        created_by_command="Flag RU-MOS"
    )
    func_ru = lambda tx: tx.location == "RU-MOS"
    engine.register_rule(new_rule, func_ru)

    # Immediately score the very next transaction against new rule
    alerts = engine.score_transaction(tx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "rule_ru_location"


def test_rules_engine_revert():
    """
    Test revert: restore a prior ruleset snapshot and verify active scoring changes.
    """
    engine = RulesEngine()

    rule1 = Rule(
        id="rule_1",
        name="Rule 1",
        code="code1",
        description="desc1",
        created_at="2026-07-27T10:00:00Z",
        created_by_command="cmd1"
    )
    rule2 = Rule(
        id="rule_2",
        name="Rule 2",
        code="code2",
        description="desc2",
        created_at="2026-07-27T10:01:00Z",
        created_by_command="cmd2"
    )

    func1 = lambda tx: tx.amount > 100
    func2 = lambda tx: tx.account_age_days < 10

    engine.register_rule(rule1, func1)
    engine.register_rule(rule2, func2)
    assert len(engine.get_active_rule_ids()) == 2

    # Revert to snapshot containing ONLY rule1
    engine.revert_ruleset([(rule1, func1)])
    assert engine.get_active_rule_ids() == ["rule_1"]

    tx = create_sample_tx(amount=50.0, age=5)
    # Rule 2 would have triggered (age < 10), but rule 2 was reverted out!
    alerts = engine.score_transaction(tx)
    assert len(alerts) == 0


def test_rules_engine_alert_listeners():
    engine = RulesEngine()
    received_alerts = []

    def alert_handler(alert: FlaggedAlert):
        received_alerts.append(alert)

    engine.add_alert_listener(alert_handler)

    rule = Rule(
        id="rule_listener",
        name="Listener Rule",
        code="code",
        description="desc",
        created_at="2026-07-27T10:00:00Z",
        created_by_command="cmd"
    )
    engine.register_rule(rule, lambda tx: True)

    tx = create_sample_tx(amount=50.0)
    engine.score_transaction(tx)

    assert len(received_alerts) == 1
    assert received_alerts[0].rule_id == "rule_listener"

    engine.remove_alert_listener(alert_handler)
    assert alert_handler not in engine._alert_listeners


def test_rules_engine_unregister_nonexistent_and_clear():
    engine = RulesEngine()
    assert engine.unregister_rule("non_existent_id") is None

    rule = Rule(
        id="rule_clear_test",
        name="Clear Test",
        code="code",
        description="desc",
        created_at="2026-07-27T10:00:00Z",
        created_by_command="cmd"
    )
    engine.register_rule(rule, lambda tx: False)
    assert len(engine.get_active_rules()) == 1

    engine.clear_rules()
    assert len(engine.get_active_rules()) == 0


def test_rules_engine_rule_exception_handling():
    engine = RulesEngine()
    rule = Rule(
        id="rule_err",
        name="Err Rule",
        code="code",
        description="desc",
        created_at="2026-07-27T10:00:00Z",
        created_by_command="cmd"
    )
    # Register function that raises an Exception
    engine.register_rule(rule, lambda tx: 1 / 0)

    tx = create_sample_tx(amount=100.0)
    alerts = engine.score_transaction(tx)
    # Should handle exception gracefully and return 0 alerts without crashing
    assert len(alerts) == 0

