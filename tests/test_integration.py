"""
Full Standalone Integration Test (`tests/test_integration.py`)

Proves Person A's engine pipeline operates 100% standalone with zero AI dependency:
Simulator -> AST Validator -> Rule Guard -> Compiler -> Rules Engine -> FlaggedAlert -> Audit Log (Hash Chain).
"""

import pytest
from backend.core.schemas import Transaction, CustomProfile
from backend.core.db import init_db
from backend.core.validator import ASTSafetyValidator
from backend.core.rule_guard import RuleGuard
from backend.core.compiler import RuleCompiler
from backend.core.rules_engine import RulesEngine
from backend.core.audit_log import AuditLogger
from backend.core.simulator import TransactionSimulator


@pytest.fixture
def standalone_engine(tmp_path):
    db_file = str(tmp_path / "integration_fraud.db")
    init_db(db_file)

    validator = ASTSafetyValidator()
    guard = RuleGuard(max_rules_cap=20, similarity_threshold=0.85)
    compiler = RuleCompiler()
    engine = RulesEngine()
    logger = AuditLogger(db_path=db_file)
    simulator = TransactionSimulator()

    return {
        "db_file": db_file,
        "validator": validator,
        "guard": guard,
        "compiler": compiler,
        "engine": engine,
        "logger": logger,
        "simulator": simulator
    }


def test_full_standalone_pipeline(standalone_engine):
    validator = standalone_engine["validator"]
    guard = standalone_engine["guard"]
    compiler = standalone_engine["compiler"]
    engine = standalone_engine["engine"]
    logger = standalone_engine["logger"]
    simulator = standalone_engine["simulator"]

    # 1. Analyst proposes a hardcoded fraud detection rule
    rule_code = """
def evaluate(tx):
    return tx.amount > 1000.0 and tx.is_international and tx.account_age_days < 30
"""
    cmd = "Flag international transactions > $1000 on accounts younger than 30 days"

    # 2. Step 1: AST Safety Validation
    val_res = validator.validate(rule_code)
    assert val_res.valid is True
    assert val_res.error is None

    # 3. Step 2: Rule Guard Check
    active_rules = logger.get_active_rules()
    temp_rule = compiler.compile_rule_code(rule_code)
    
    from backend.core.schemas import Rule
    import uuid, datetime
    
    proposed_rule = Rule(
        id="rule_integ_01",
        name="International High Risk New Account",
        code=rule_code,
        description="Flag international >1000 age <30",
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command=cmd
    )

    guard_res = guard.evaluate_rule(proposed_rule, active_rules)
    assert guard_res.passed is True

    # 4. Step 3: Compile and Hot-reload into live Rules Engine
    compiler.compile_and_register(proposed_rule, engine)
    assert "rule_integ_01" in engine.get_active_rule_ids()

    # 5. Step 4: Persist in tamper-evident SHA-256 Audit Log
    audit_entry = logger.log_deploy_rule(proposed_rule, command=cmd)
    assert audit_entry.hash is not None

    # 6. Step 5: Run Simulator and Score Live Transactions
    profile = CustomProfile(
        name="test_integration_profile",
        amount_min=1500.0,
        amount_max=3000.0,
        high_risk_location_bias=1.0,
        new_account_bias=1.0
    )
    simulator.set_profile(profile)

    # Generate matching transaction
    matching_tx = simulator.generate_single_transaction()
    # Force matching properties for deterministic assertion
    matching_tx.amount = 2500.0
    matching_tx.is_international = True
    matching_tx.account_age_days = 5

    alerts = engine.score_transaction(matching_tx)
    assert len(alerts) == 1
    alert = alerts[0]

    assert alert.rule_id == "rule_integ_01"
    assert alert.transaction_id == matching_tx.id
    assert alert.score == 1.0
    assert alert.transaction_details.amount == 2500.0

    # Non-matching transaction
    non_matching_tx = simulator.generate_single_transaction()
    non_matching_tx.amount = 50.0  # Under $1000
    non_matching_tx.is_international = False

    no_alerts = engine.score_transaction(non_matching_tx)
    assert len(no_alerts) == 0

    # 7. Step 6: Test Revert Capability
    engine.unregister_rule("rule_integ_01")
    logger.log_revert_rule("rule_integ_01", command="Revert test rule")

    assert len(engine.get_active_rule_ids()) == 0
    reverted_alerts = engine.score_transaction(matching_tx)
    assert len(reverted_alerts) == 0

    # 8. Step 7: Verify Audit Log Cryptographic Integrity
    is_valid, tampered_row = logger.verify_hash_chain_integrity()
    assert is_valid is True
    assert tampered_row is None
