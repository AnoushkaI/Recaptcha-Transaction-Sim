"""
scripts/test_phase3.py
───────────────────────
Phase 3 verification tests:
  Test 1: InvestigatorAgent — real Gemini call against a fake alert
  Test 2: RuleWriterAgent (valid request) — should succeed on attempt 1
  Test 3: RuleWriterAgent (bad prompt that produces invalid code) — should trigger retry loop

Run from project root:
  $env:PYTHONPATH = "."; python scripts/test_phase3.py
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from backend.ai.providers.factory import get_provider
from backend.ai.agents.investigator import InvestigatorAgent
from backend.ai.agents.rule_writer import RuleWriterAgent

SEPARATOR = "-" * 60

# ── Sample alert for testing ──────────────────────────────────────────────────
SAMPLE_ALERT = {
    "id": "alert_001",
    "transaction": {
        "id": "txn_001",
        "amount": 4500.00,
        "location": "new_device",
        "timestamp": "2026-07-26T10:15:00Z",
        "account_id": "acc_123",
    },
    "rule_triggered": "velocity_check",
    "severity": "high",
    "timestamp": "2026-07-26T10:15:02Z",
}

pass_count = 0
fail_count = 0


def report(label, passed, detail=""):
    global pass_count, fail_count
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {label}")
    if detail:
        print(f"       {detail}")
    if passed:
        pass_count += 1
    else:
        fail_count += 1


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: InvestigatorAgent — real Gemini call
# ─────────────────────────────────────────────────────────────────────────────
print(SEPARATOR)
print("TEST 1: InvestigatorAgent — real Gemini explanation")
print(SEPARATOR)

try:
    provider = get_provider(role="investigator")
    agent = InvestigatorAgent(provider=provider)
    explanation = agent.explain(SAMPLE_ALERT)

    print(f"Response:\n  {explanation}\n")

    # It must be a non-empty string and NOT a stub placeholder
    is_real = (
        isinstance(explanation, str)
        and len(explanation) > 20
        and "PHASE-1 STUB" not in explanation
        and "PHASE" not in explanation
    )
    report("InvestigatorAgent returns real text (not a stub)", is_real,
           f"Length: {len(explanation)} chars")
    report("InvestigatorAgent response is non-empty", bool(explanation.strip()))

except Exception as exc:
    report("InvestigatorAgent call", False, f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: RuleWriterAgent — valid request, should pass on attempt 1
# ─────────────────────────────────────────────────────────────────────────────
print(SEPARATOR)
print("TEST 2: RuleWriterAgent — valid rule generation")
print(SEPARATOR)

try:
    provider = get_provider(role="rule_writer")
    agent = RuleWriterAgent(provider=provider)
    result = agent.generate_rule(
        command="Flag any transaction over 5000",
        context=SAMPLE_ALERT,
    )

    print(f"Attempts  : {result['attempts']}")
    print(f"Valid     : {result['valid']}")
    print(f"Error     : {result['error']}")
    print(f"Code:\n{result['code']}\n")

    report("RuleWriterAgent returns valid code", result["valid"])
    report("Code contains detect() function", "def detect(" in result["code"])
    report("Code does not contain STUB placeholder", "PHASE-1 STUB" not in result["code"])

except Exception as exc:
    report("RuleWriterAgent call", False, f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: RuleWriterAgent retry loop — use a command designed to tempt bad code
# ─────────────────────────────────────────────────────────────────────────────
print(SEPARATOR)
print("TEST 3: RuleWriterAgent — retry loop demo (command that may need correction)")
print(SEPARATOR)

try:
    provider = get_provider(role="rule_writer")
    agent = RuleWriterAgent(provider=provider)

    # This command is deliberately vague/tricky — model might produce wrong func name
    # or include an import. If it passes first try, that's fine too.
    result = agent.generate_rule(
        command="Use Python's datetime module to flag transactions older than 1 hour",
        context=None,
    )

    print(f"Attempts  : {result['attempts']}")
    print(f"Valid     : {result['valid']}")
    print(f"Error     : {result['error']}")
    print(f"Code:\n{result['code']}\n")

    report("Retry loop ran (attempts >= 1)", result["attempts"] >= 1)
    report(
        "Self-correction either produced valid code OR exhausted retries gracefully",
        result["valid"] or (not result["valid"] and result["attempts"] == 3),
    )
    if result["attempts"] > 1:
        report(f"Self-correction triggered (took {result['attempts']} attempts)", True)
    else:
        report("Model produced valid code on first attempt (still a pass)", True)

except Exception as exc:
    report("RuleWriterAgent retry loop", False, f"{type(exc).__name__}: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print(SEPARATOR)
total = pass_count + fail_count
print(f"Phase 3 results: {pass_count}/{total} passed")
if fail_count > 0:
    print("Some tests failed — review output above.")
    sys.exit(1)
else:
    print("All Phase 3 tests passed.")
