"""
Comprehensive adversarial + coverage unit tests for validator.py.
Missing lines: 64, 69-70, 110, 121-126, 153, 177-178, 215
"""

import pytest
from backend.core.validator import ASTSafetyValidator


@pytest.fixture
def v():
    return ASTSafetyValidator()


# --------------- empty / syntax errors ---------------

def test_empty_string_rejected(v):
    res = v.validate("")
    assert res.valid is False
    assert res.error == "Rule code cannot be empty"


def test_whitespace_only_rejected(v):
    res = v.validate("   ")
    assert res.valid is False
    assert res.error == "Rule code cannot be empty"


def test_syntax_error_rejected(v):
    """Hits lines 69-70: SyntaxError path."""
    res = v.validate("def evaluate(tx):\n    return tx.amount >>>> 100")
    assert res.valid is False
    assert "Syntax error" in res.error
    assert res.line_number is not None


# --------------- import blocking ---------------

def test_import_os_blocked(v):
    res = v.validate("import os\ndef evaluate(tx): return True")
    assert res.valid is False
    assert "Disallowed import statement 'os'" in res.error
    assert res.line_number == 1


def test_from_sys_import_blocked(v):
    res = v.validate("from sys import exit\ndef evaluate(tx): return True")
    assert res.valid is False
    assert "Disallowed import statement" in res.error


def test_from_import_module_name_coverage(v):
    """Hits line 82-84: ImportFrom where module attr is a string (not Import)."""
    res = v.validate("from os.path import join\ndef evaluate(tx): return True")
    assert res.valid is False
    assert "Disallowed import statement" in res.error


# --------------- loop blocking ---------------

def test_while_loop_blocked(v):
    code = "def evaluate(tx):\n    while True:\n        pass"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed loop structure 'While'" in res.error


def test_for_loop_blocked(v):
    code = "def evaluate(tx):\n    for i in range(10):\n        pass\n    return True"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed loop structure 'For'" in res.error


# --------------- try/except blocking ---------------

def test_try_except_blocked(v):
    code = "def evaluate(tx):\n    try:\n        return tx.amount > 100\n    except Exception:\n        return False"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed try/except block" in res.error


# --------------- class definition blocking ---------------

def test_class_def_blocked(v):
    """Hits line 109-114: ClassDef blocking."""
    code = "class Hack:\n    pass\ndef evaluate(tx): return True"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed class definition 'Hack'" in res.error


# --------------- disallowed function calls ---------------

def test_eval_call_blocked(v):
    code = "def evaluate(tx):\n    return eval('True')"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed function call 'eval'" in res.error


def test_exec_call_blocked(v):
    code = "def evaluate(tx):\n    exec('x=1')\n    return True"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed function call 'exec'" in res.error


def test_open_call_blocked(v):
    code = "def evaluate(tx):\n    open('/etc/passwd')\n    return True"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed function call 'open'" in res.error


def test_disallowed_module_call_blocked(v):
    """Hits lines 121-130: attribute call on a disallowed module (e.g. os.system)."""
    code = "def evaluate(tx):\n    os.system('whoami')\n    return True"
    res = v.validate(code)
    assert res.valid is False
    assert "Disallowed module call 'os.system'" in res.error


def test_allowed_attribute_method_call_passes(v):
    """Hits lines 121-122 where func is Attribute but module is NOT disallowed."""
    code = "def evaluate(tx):\n    return tx.amount > 100"
    res = v.validate(code)
    assert res.valid is True


# --------------- schema field validation ---------------

def test_unknown_field_blocked(v):
    code = "def evaluate(tx):\n    return tx.credit_score > 700"
    res = v.validate(code)
    assert res.valid is False
    assert "Unknown field 'credit_score'" in res.error


# --------------- complexity cap ---------------

def test_ast_complexity_cap_exceeded(v):
    """Hits line 152-156: complexity cap (>150 AST nodes)."""
    code = "def evaluate(tx):\n    return " + " + ".join(
        [f"(tx.amount + {i})" for i in range(80)]
    )
    res = v.validate(code)
    assert res.valid is False
    assert "complexity cap exceeded" in res.error


# --------------- dry-run checks ---------------

def test_missing_evaluate_function_blocked(v):
    """Hits lines 185-189: no 'evaluate' function found in local scope."""
    code = "def check_fraud(tx):\n    return tx.amount > 500"
    res = v.validate(code)
    assert res.valid is False
    assert "must define an entry function named 'evaluate(tx)'" in res.error


def test_dry_run_type_error_caught(v):
    """Hits lines 219-223: dry-run raises TypeError."""
    code = "def evaluate(tx):\n    return tx.amount + 'invalid' > 100"
    res = v.validate(code)
    assert res.valid is False
    assert "Dry-run runtime error" in res.error
    assert "TypeError" in res.error


def test_dry_run_non_boolean_return_caught(v):
    """Hits lines 214-218: dry-run returns non-bool type."""
    code = "def evaluate(tx):\n    return 'not_a_bool'"
    res = v.validate(code)
    assert res.valid is False
    assert "non-boolean result type" in res.error


def test_dry_run_compilation_error_caught(v):
    """Hits lines 177-181: restricted exec fails on a NameError (missing builtin).
    This code passes static AST but fails inside restricted exec because print is not in SAFE_BUILTINS."""
    code = "def evaluate(tx):\n    print(tx.amount)\n    return True"
    res = v.validate(code)
    # 'print' is not in SAFE_BUILTINS, so exec() raises NameError inside dry-run
    assert res.valid is False
    assert "Dry-run" in res.error or "NameError" in res.error


# --------------- valid rules pass ---------------

def test_valid_simple_rule_passes(v):
    code = "def evaluate(tx):\n    return tx.amount > 1000.0 and tx.account_age_days < 14"
    res = v.validate(code)
    assert res.valid is True
    assert res.error is None


def test_valid_international_rule_passes(v):
    code = "def evaluate(tx):\n    return tx.is_international and tx.amount > 500"
    res = v.validate(code)
    assert res.valid is True


def test_valid_category_rule_passes(v):
    code = "def evaluate(tx):\n    return tx.merchant_category == 'crypto' and tx.amount > 2000"
    res = v.validate(code)
    assert res.valid is True
