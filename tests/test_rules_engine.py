"""
Comprehensive unit tests for rules_engine.py targeting 100% line coverage.
Missing lines: 33-34, 37-40, 56, 60, 68, 105-106, 115-116, 121-124
"""

import asyncio
import pytest
from backend.core.schemas import Transaction, Rule, FlaggedAlert
from backend.core.rules_engine import RulesEngine


def make_tx(amount=500.0, location="MUM-DEL", age=100, international=False):
    return Transaction(
        id="tx_test_001",
        account_id="acc_001",
        amount=amount,
        location=location,
        timestamp="2026-07-27T12:00:00Z",
        account_age_days=age,
        merchant_category="electronics",
        device_id="dev_001",
        is_international=international
    )


def make_rule(rule_id="rule_x", name="Test Rule"):
    return Rule(
        id=rule_id,
        name=name,
        code="def evaluate(tx): return True",
        description="desc",
        created_at="2026-07-27T10:00:00Z",
        status="active",
        created_by_command="cmd"
    )


# --------------- listener management ---------------

def test_add_alert_listener_deduplication():
    engine = RulesEngine()
    cb = lambda alert: None
    engine.add_alert_listener(cb)
    engine.add_alert_listener(cb)  # duplicate — guard on line 28-29
    assert engine._alert_listeners.count(cb) == 1


def test_add_async_alert_listener_deduplication():
    engine = RulesEngine()
    async def acb(alert): pass
    engine.add_async_alert_listener(acb)
    engine.add_async_alert_listener(acb)  # duplicate — guard on line 33-34
    assert engine._async_alert_listeners.count(acb) == 1


def test_remove_sync_alert_listener():
    engine = RulesEngine()
    cb = lambda alert: None
    engine.add_alert_listener(cb)
    engine.remove_alert_listener(cb)  # hits line 37-38
    assert cb not in engine._alert_listeners


def test_remove_async_alert_listener():
    engine = RulesEngine()
    async def acb(alert): pass
    engine.add_async_alert_listener(acb)
    engine.remove_alert_listener(acb)  # hits line 39-40
    assert acb not in engine._async_alert_listeners


def test_remove_nonexistent_listener_is_safe():
    engine = RulesEngine()
    engine.remove_alert_listener(lambda x: None)  # should not raise


# --------------- rule management ---------------

def test_register_and_get_rules():
    engine = RulesEngine()
    rule = make_rule("rule_1")
    engine.register_rule(rule, lambda tx: False)
    assert "rule_1" in engine.get_active_rule_ids()
    assert len(engine.get_active_rules()) == 1


def test_unregister_existing_rule():
    engine = RulesEngine()
    rule = make_rule("rule_2")
    engine.register_rule(rule, lambda tx: False)
    removed = engine.unregister_rule("rule_2")  # hits line 52-55
    assert removed is not None
    assert removed.id == "rule_2"


def test_unregister_nonexistent_rule_returns_none():
    engine = RulesEngine()
    result = engine.unregister_rule("nonexistent")  # hits line 56
    assert result is None


def test_get_active_rule_ids():
    engine = RulesEngine()
    rule = make_rule("rule_ids")
    engine.register_rule(rule, lambda tx: False)
    assert "rule_ids" in engine.get_active_rule_ids()  # hits line 64


def test_clear_rules():
    engine = RulesEngine()
    engine.register_rule(make_rule("rule_c1"), lambda tx: False)
    engine.register_rule(make_rule("rule_c2"), lambda tx: False)
    engine.clear_rules()  # hits line 68
    assert len(engine.get_active_rules()) == 0


def test_revert_ruleset():
    engine = RulesEngine()
    rule1 = make_rule("rule_r1", "Rule R1")
    rule2 = make_rule("rule_r2", "Rule R2")
    func1 = lambda tx: tx.amount > 100
    func2 = lambda tx: tx.account_age_days < 10

    engine.register_rule(rule1, func1)
    engine.register_rule(rule2, func2)
    assert len(engine.get_active_rule_ids()) == 2

    engine.revert_ruleset([(rule1, func1)])
    assert engine.get_active_rule_ids() == ["rule_r1"]


# --------------- scoring ---------------

def test_score_transaction_no_rules():
    engine = RulesEngine()
    tx = make_tx(amount=9999.0)
    alerts = engine.score_transaction(tx)
    assert alerts == []


def test_score_transaction_rule_triggers():
    engine = RulesEngine()
    rule = make_rule("rule_trigger")
    engine.register_rule(rule, lambda tx: tx.amount > 1000)

    alerts = engine.score_transaction(make_tx(amount=2000.0))
    assert len(alerts) == 1
    assert alerts[0].rule_id == "rule_trigger"


def test_score_transaction_rule_does_not_trigger():
    engine = RulesEngine()
    rule = make_rule("rule_no_trigger")
    engine.register_rule(rule, lambda tx: tx.amount > 1000)

    alerts = engine.score_transaction(make_tx(amount=50.0))
    assert len(alerts) == 0


def test_score_transaction_exception_is_handled():
    """Hits lines 105-106: exception path inside score loop."""
    engine = RulesEngine()
    rule = make_rule("rule_crash")
    engine.register_rule(rule, lambda tx: 1 / 0)  # always raises ZeroDivisionError

    alerts = engine.score_transaction(make_tx())
    assert alerts == []  # engine swallows exception, returns empty list


# --------------- alert listeners on emit ---------------

def test_sync_listener_receives_alert():
    engine = RulesEngine()
    received = []
    engine.add_alert_listener(lambda alert: received.append(alert))
    engine.register_rule(make_rule("rule_emit"), lambda tx: True)

    engine.score_transaction(make_tx())
    assert len(received) == 1


def test_sync_listener_exception_is_handled():
    """Hits lines 115-116: crashing sync listener is logged, not propagated."""
    engine = RulesEngine()

    def crashing_cb(alert):
        raise RuntimeError("listener crash")

    engine.add_alert_listener(crashing_cb)
    engine.register_rule(make_rule("rule_listener_crash"), lambda tx: True)

    alerts = engine.score_transaction(make_tx())
    assert len(alerts) == 1  # alert still generated despite listener crash


@pytest.mark.asyncio
async def test_async_listener_receives_alert_via_event_loop():
    """Hits lines 119-124: async listener scheduled via running event loop."""
    engine = RulesEngine()
    received = []

    async def async_alert_handler(alert):
        received.append(alert)

    engine.add_async_alert_listener(async_alert_handler)
    engine.register_rule(make_rule("rule_async_emit"), lambda tx: True)

    engine.score_transaction(make_tx())
    # Give the event loop a tick to schedule the async coroutine
    await asyncio.sleep(0.05)
    assert len(received) == 1


def test_hot_reload_mid_stream():
    """Deploy rule mid-run → next tx immediately scored against it."""
    engine = RulesEngine()
    tx = make_tx(location="MUM-JMT")

    # Before hot-reload: no rules
    assert len(engine.score_transaction(tx)) == 0

    # Hot-reload new rule
    rule = make_rule("rule_hotreload")
    engine.register_rule(rule, lambda tx: tx.location == "MUM-JMT")

    # Next transaction immediately scored against it
    alerts = engine.score_transaction(tx)
    assert len(alerts) == 1
    assert alerts[0].rule_id == "rule_hotreload"
