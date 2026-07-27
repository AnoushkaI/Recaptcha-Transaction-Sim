"""
Adversarial Security Unit Tests for AST Safety Validator (`core/validator.py`).
"""

import pytest
from backend.core.validator import ASTSafetyValidator


@pytest.fixture
def validator():
    return ASTSafetyValidator()


def test_valid_rule_passes(validator):
    code = """
def evaluate(tx):
    return tx.amount > 1000.0 and tx.account_age_days < 14
"""
    res = validator.validate(code)
    assert res.valid is True
    assert res.error is None


def test_import_os_rejected(validator):
    code = """
import os

def evaluate(tx):
    os.system("whoami")
    return True
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Disallowed import statement 'os'" in res.error
    assert res.line_number == 2


def test_import_from_sys_rejected(validator):
    code = """
from sys import exit

def evaluate(tx):
    return tx.amount > 100
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Disallowed import statement" in res.error


def test_eval_exec_call_rejected(validator):
    code_eval = """
def evaluate(tx):
    return eval("tx.amount > 100")
"""
    res = validator.validate(code_eval)
    assert res.valid is False
    assert "Disallowed function call 'eval'" in res.error

    code_exec = """
def evaluate(tx):
    exec("print(1)")
    return False
"""
    res = validator.validate(code_exec)
    assert res.valid is False
    assert "Disallowed function call 'exec'" in res.error


def test_while_loop_rejected(validator):
    code = """
def evaluate(tx):
    while True:
        pass
    return True
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Disallowed loop structure 'While'" in res.error


def test_for_loop_rejected(validator):
    code = """
def evaluate(tx):
    for i in range(10):
        pass
    return True
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Disallowed loop structure 'For'" in res.error


def test_try_except_rejected(validator):
    code = """
def evaluate(tx):
    try:
        return tx.amount > 100
    except Exception:
        return False
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Disallowed try/except block" in res.error


def test_nonexistent_transaction_field_rejected(validator):
    code = """
def evaluate(tx):
    return tx.credit_score > 700
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Unknown field 'credit_score' accessed on Transaction schema" in res.error


def test_missing_evaluate_function(validator):
    code = """
def check_fraud(tx):
    return tx.amount > 500
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "must define an entry function named 'evaluate(tx)'" in res.error


def test_dry_run_type_error_caught(validator):
    code = """
def evaluate(tx):
    return tx.amount + "invalid_string_addition" > 100
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "Dry-run runtime error" in res.error
    assert "TypeError" in res.error


def test_validator_empty_code(validator):
    assert validator.validate("").valid is False
    assert validator.validate("   ").valid is False


def test_dry_run_non_boolean_result(validator):
    code = """
def evaluate(tx):
    return "string_result"
"""
    res = validator.validate(code)
    assert res.valid is False
    assert "non-boolean result type" in res.error


def test_ast_complexity_cap(validator):
    # Generate code with >150 AST nodes
    code = "def evaluate(tx):\n    return " + " + ".join([f"(tx.amount + {i})" for i in range(80)])
    res = validator.validate(code)
    assert res.valid is False
    assert "complexity cap exceeded" in res.error

