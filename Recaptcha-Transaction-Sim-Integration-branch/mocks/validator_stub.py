"""
mocks/validator_stub.py
─────────────────────────
Fake AST Safety Validator — same function signature as the real one (teammate's part).

This stub is used in Phase 1–3 so the rule-writer's retry loop can be tested
without depending on the teammate's real validator being available.

Heuristics (deliberately simple — enough to exercise the retry loop):
  VALID if:
    - code is non-empty
    - no banned imports (os, sys, subprocess, socket, eval, exec)
    - contains a function definition
  INVALID otherwise (returns specific error message matching expected format)

The real validator will apply full AST analysis. The stub is swapped out in Phase 5.
"""

import re

# Imports the real validator will block — used to trigger intentional failures in tests
BANNED_IMPORTS = ["import os", "import sys", "import subprocess", "import socket"]
BANNED_BUILTINS = ["eval(", "exec("]


def validate_rule(code: str) -> dict:
    """Validate a generated Python detection rule.

    This is the SHARED INTERFACE CONTRACT between my rule-writer and
    teammate's real AST validator. Do not change the signature or return shape.

    Args:
        code: Python source code string for the detection rule.

    Returns:
        {"valid": True}
            if the rule passes all checks.
        {"valid": False, "error": "<specific reason>"}
            if the rule fails. The error string is fed back into the rule-writer's
            retry prompt — it must be descriptive enough for the model to self-correct.
    """
    # Check 1: non-empty
    if not code or not code.strip():
        return {"valid": False, "error": "Rule code is empty. Provide a non-empty Python function."}

    # Check 2: banned imports
    for banned in BANNED_IMPORTS:
        if banned in code:
            return {
                "valid": False,
                "error": (
                    f"Unsafe import detected: '{banned}'. "
                    "Only pure Python logic is allowed — no stdlib imports."
                ),
            }

    # Check 3: banned builtins
    for banned in BANNED_BUILTINS:
        if banned in code:
            return {
                "valid": False,
                "error": (
                    f"Unsafe builtin detected: '{banned}'. "
                    "Do not use eval() or exec() in rule code."
                ),
            }

    # Check 4: must define a callable function named 'detect'
    if not re.search(r"def\s+detect\s*\(", code):
        return {
            "valid": False,
            "error": (
                "Rule must define a function named 'detect(transaction: dict) -> bool'. "
                "No 'detect' function found."
            ),
        }

    # Check 5: function must accept 'transaction' as a parameter
    if not re.search(r"def\s+detect\s*\(\s*transaction", code):
        return {
            "valid": False,
            "error": (
                "The 'detect' function must accept 'transaction' as its first parameter. "
                "Signature must be: def detect(transaction: dict) -> bool"
            ),
        }

    return {"valid": True}


# ── Quick smoke-test when run directly ────────────────────────────────────────
if __name__ == "__main__":
    cases = [
        ("valid rule", "def detect(transaction: dict) -> bool:\n    return transaction['amount'] > 5000\n"),
        ("empty code", ""),
        ("banned import", "import os\ndef detect(transaction: dict) -> bool:\n    return True\n"),
        ("wrong function name", "def check(transaction: dict) -> bool:\n    return True\n"),
        ("missing transaction param", "def detect(data: dict) -> bool:\n    return True\n"),
        ("eval usage", "def detect(transaction: dict) -> bool:\n    return eval('True')\n"),
    ]

    for label, code in cases:
        result = validate_rule(code)
        status = "valid" if result["valid"] else f"INVALID: {result.get('error')}"
        print(f"[{label}] -> {status}")
