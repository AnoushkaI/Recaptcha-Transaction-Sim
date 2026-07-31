"""
backend/ai/prompts/rule_writer_prompts.py
──────────────────────────────────────────
System and user prompt templates for the RuleWriterAgent.

Two prompt builders:
  build_rule_writer_user_prompt()  — first attempt
  build_retry_user_prompt()        — retry attempts (feeds back validator error)
"""

RULE_WRITER_SYSTEM_PROMPT = """You are an expert Python fraud detection rule engineer.

Your job is to write a single Python function that detects a specific type of fraudulent transaction.

STRICT RULES — your code will be rejected by an AST validator if you break any of these:
1. Define exactly ONE function named `detect` with this exact signature:
       def detect(transaction: dict) -> bool:
2. The function MUST return True (fraud detected) or False (not fraud).
3. DO NOT use any imports — not even `import os`, `import math`, or any stdlib module.
4. DO NOT use eval(), exec(), or any dynamic code execution.
5. Only access fields that exist on a transaction object:
       transaction["id"]          (string)
       transaction["amount"]      (float)
       transaction["location"]    (string: "new_device", "foreign_ip", "atm", "online")
       transaction["timestamp"]   (ISO 8601 string)
       transaction["account_id"]  (string)
6. Keep the logic simple and readable — one clear conditional expression.
7. Add a one-line comment above the function explaining what it detects.

OUTPUT FORMAT — return ONLY the Python code block, nothing else. No explanation, no markdown fences."""


def build_rule_writer_user_prompt(command: str, context: dict | None = None) -> str:
    """Build the initial rule generation prompt."""
    context_section = ""
    if context:
        txn = context.get("transaction", {})
        context_section = f"""
This rule is in response to this flagged alert:
  Rule that triggered  : {context.get('rule_triggered', 'unknown')}
  Severity             : {context.get('severity', 'unknown')}
  Transaction amount   : {txn.get('amount', 'unknown')}
  Transaction location : {txn.get('location', 'unknown')}
  Account              : {txn.get('account_id', 'unknown')}
"""

    return f"""Write a Python fraud detection rule for the following request:

Analyst instruction: {command}
{context_section}
Remember: return ONLY the Python function. No markdown, no explanation."""


def build_retry_user_prompt(
    command: str,
    previous_code: str,
    validator_error: str,
    attempt: int,
    max_attempts: int,
    context: dict | None = None,
) -> str:
    """Build the retry prompt that feeds the validator error back to the model.

    This is the key part of the self-correcting loop — the model sees exactly
    what went wrong and can fix it.
    """
    context_section = ""
    if context:
        txn = context.get("transaction", {})
        context_section = f"Alert context: rule={context.get('rule_triggered')}, amount={txn.get('amount')}, location={txn.get('location')}\n"

    return f"""Your previous code was REJECTED by the validator (attempt {attempt} of {max_attempts}).

VALIDATOR ERROR:
{validator_error}

YOUR PREVIOUS (REJECTED) CODE:
{previous_code}

ORIGINAL INSTRUCTION: {command}
{context_section}
Fix the code so it passes the validator. The error message tells you exactly what to change.
Return ONLY the corrected Python function — no explanation, no markdown."""
