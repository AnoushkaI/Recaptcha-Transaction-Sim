"""
Unit tests for database schema and SHA-256 hash-chained audit logger (`core/audit_log.py`).
"""

import pytest
import os
import sqlite3
from backend.core.schemas import Rule
from backend.core.db import init_db, get_db_connection
from backend.core.audit_log import AuditLogger, GENESIS_HASH


@pytest.fixture
def temp_db_path(tmp_path):
    db_file = str(tmp_path / "test_fraud_rules.db")
    init_db(db_file)
    return db_file


def test_init_db_creates_tables(temp_db_path):
    conn = get_db_connection(temp_db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row["name"] for row in cursor.fetchall()]
    assert "rules" in tables
    assert "audit_log" in tables
    assert "rule_history" in tables
    assert "custom_profiles" in tables
    conn.close()


def test_audit_log_hash_chaining(temp_db_path):
    logger = AuditLogger(temp_db_path)

    rule1 = Rule(
        id="rule_101",
        name="High Amount Rule",
        code="def evaluate(tx): return tx.amount > 1000",
        description="Flag >1000",
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command="Deploy high amount"
    )

    entry1 = logger.log_deploy_rule(rule1, command="Deploy high amount")
    assert entry1.prev_hash == GENESIS_HASH
    assert entry1.hash != GENESIS_HASH

    rule2 = Rule(
        id="rule_102",
        name="Crypto Rule",
        code="def evaluate(tx): return tx.merchant_category == 'crypto'",
        description="Flag crypto",
        created_at="2026-07-27T12:05:00Z",
        status="active",
        created_by_command="Deploy crypto"
    )

    entry2 = logger.log_deploy_rule(rule2, command="Deploy crypto")
    assert entry2.prev_hash == entry1.hash

    valid, tampered_id = logger.verify_hash_chain_integrity()
    assert valid is True
    assert tampered_id is None


def test_audit_log_revert(temp_db_path):
    logger = AuditLogger(temp_db_path)

    rule = Rule(
        id="rule_revert_target",
        name="Revert Target",
        code="def evaluate(tx): return True",
        description="Always trigger",
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command="Deploy trigger"
    )

    logger.log_deploy_rule(rule, command="Deploy trigger")
    active_rules = logger.get_active_rules()
    assert len(active_rules) == 1

    revert_entry = logger.log_revert_rule(rule_id="rule_revert_target", command="Revert bad rule")
    assert revert_entry is not None
    assert revert_entry.status == "reverted"

    active_rules_after = logger.get_active_rules()
    assert len(active_rules_after) == 0


def test_tamper_detection(temp_db_path):
    logger = AuditLogger(temp_db_path)

    rule = Rule(
        id="rule_tamper_target",
        name="Original Rule",
        code="def evaluate(tx): return tx.amount > 100",
        description="Original desc",
        created_at="2026-07-27T12:00:00Z",
        status="active",
        created_by_command="Deploy original"
    )

    logger.log_deploy_rule(rule, command="Deploy original")

    valid_before, _ = logger.verify_hash_chain_integrity()
    assert valid_before is True

    # Maliciously modify the database record directly (simulate unauthorized DB tampering)
    conn = get_db_connection(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_log SET code = 'def evaluate(tx): return False' WHERE rule_id = 'rule_tamper_target'")
    conn.commit()
    conn.close()

    valid_after, tampered_row_id = logger.verify_hash_chain_integrity()
    assert valid_after is False
    assert tampered_row_id == 1
