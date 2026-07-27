"""
Comprehensive unit tests for audit_log.py targeting 100% line coverage.
Missing lines: 115 (rule not found → None), 158-181 (get_audit_logs with rule_id filter),
226-227 (get_active_rules empty case)
"""

import pytest
from backend.core.schemas import Rule
from backend.core.db import init_db, get_db_connection
from backend.core.audit_log import AuditLogger, GENESIS_HASH, compute_entry_hash


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def make_rule(rule_id, name="Rule", code="def evaluate(tx): return True"):
    return Rule(
        id=rule_id, name=name, code=code,
        description="desc", created_at="2026-07-27T12:00:00Z",
        status="active", created_by_command="cmd"
    )


# --------------- DB init ---------------

def test_db_creates_all_tables(db):
    conn = get_db_connection(db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row["name"] for row in cursor.fetchall()}
    assert {"rules", "audit_log", "rule_history", "custom_profiles"}.issubset(tables)
    conn.close()


# --------------- deploy and hash chaining ---------------

def test_first_deploy_uses_genesis_hash(db):
    logger = AuditLogger(db)
    rule = make_rule("r1")
    entry = logger.log_deploy_rule(rule, "DEPLOY_RULE")
    assert entry.prev_hash == GENESIS_HASH
    assert entry.hash != GENESIS_HASH


def test_second_deploy_chains_to_first(db):
    logger = AuditLogger(db)
    e1 = logger.log_deploy_rule(make_rule("r1"), "DEPLOY")
    e2 = logger.log_deploy_rule(make_rule("r2"), "DEPLOY")
    assert e2.prev_hash == e1.hash


def test_hash_chain_integrity_valid(db):
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r1"), "DEPLOY")
    logger.log_deploy_rule(make_rule("r2"), "DEPLOY")
    valid, bad_row = logger.verify_hash_chain_integrity()
    assert valid is True
    assert bad_row is None


def test_tamper_detection_on_code_change(db):
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r_tamper"), "DEPLOY")

    conn = get_db_connection(db)
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_log SET code='TAMPERED' WHERE rule_id='r_tamper'")
    conn.commit()
    conn.close()

    valid, bad_row = logger.verify_hash_chain_integrity()
    assert valid is False
    assert bad_row is not None


def test_tamper_detection_on_prev_hash_change(db):
    """Hits the prev_hash mismatch branch in verify_hash_chain_integrity."""
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r_chain1"), "DEPLOY")
    logger.log_deploy_rule(make_rule("r_chain2"), "DEPLOY")

    conn = get_db_connection(db)
    cursor = conn.cursor()
    # Break the prev_hash link on the second record
    cursor.execute("UPDATE audit_log SET prev_hash='000000' WHERE id=2")
    conn.commit()
    conn.close()

    valid, bad_row = logger.verify_hash_chain_integrity()
    assert valid is False
    assert bad_row == 2


# --------------- revert ---------------

def test_revert_rule_marks_as_reverted(db):
    logger = AuditLogger(db)
    rule = make_rule("r_revert")
    logger.log_deploy_rule(rule, "DEPLOY")

    entry = logger.log_revert_rule("r_revert", "REVERT")
    assert entry is not None
    assert entry.status == "reverted"
    assert len(logger.get_active_rules()) == 0


def test_revert_nonexistent_rule_returns_none(db):
    """Hits line 114-115: rule not found → returns None."""
    logger = AuditLogger(db)
    result = logger.log_revert_rule("nonexistent_id", "REVERT")
    assert result is None


# --------------- get_audit_logs ---------------

def test_get_all_audit_logs(db):
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r1"), "DEPLOY")
    logger.log_deploy_rule(make_rule("r2"), "DEPLOY")
    logs = logger.get_audit_logs()
    assert len(logs) == 2


def test_get_audit_logs_filtered_by_rule_id(db):
    """Hits lines 162-163: rule_id filter branch."""
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r_filter_1"), "DEPLOY")
    logger.log_deploy_rule(make_rule("r_filter_2"), "DEPLOY")

    logs = logger.get_audit_logs(rule_id="r_filter_1")
    assert len(logs) == 1
    assert logs[0].rule_id == "r_filter_1"


def test_get_audit_logs_empty(db):
    logger = AuditLogger(db)
    logs = logger.get_audit_logs()
    assert logs == []


# --------------- get_active_rules ---------------

def test_get_active_rules_populated(db):
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r_active_1"), "DEPLOY")
    logger.log_deploy_rule(make_rule("r_active_2"), "DEPLOY")
    rules = logger.get_active_rules()
    assert len(rules) == 2
    assert all(r.status == "active" for r in rules)


def test_get_active_rules_empty_after_revert(db):
    """Hits the empty result path of get_active_rules."""
    logger = AuditLogger(db)
    logger.log_deploy_rule(make_rule("r_empty"), "DEPLOY")
    logger.log_revert_rule("r_empty", "REVERT")
    rules = logger.get_active_rules()
    assert rules == []


# --------------- compute_entry_hash ---------------

def test_compute_entry_hash_deterministic():
    h1 = compute_entry_hash("prev", "rid", "ts", "cmd", "code", "status")
    h2 = compute_entry_hash("prev", "rid", "ts", "cmd", "code", "status")
    assert h1 == h2


def test_compute_entry_hash_sensitive_to_inputs():
    h1 = compute_entry_hash("prev", "rid", "ts", "cmd", "code", "status")
    h2 = compute_entry_hash("prev", "rid", "ts", "cmd", "DIFFERENT_CODE", "status")
    assert h1 != h2


def test_integrity_check_on_empty_log(db):
    """Hits the loop body with zero rows — should return valid."""
    logger = AuditLogger(db)
    valid, bad = logger.verify_hash_chain_integrity()
    assert valid is True
    assert bad is None
