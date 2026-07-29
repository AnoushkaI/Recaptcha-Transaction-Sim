"""
backend/ai/prompts/investigator_prompts.py
───────────────────────────────────────────
System and user prompt templates for the InvestigatorAgent.

Kept in a separate file so prompts can be tuned without touching agent logic.
"""

INVESTIGATOR_SYSTEM_PROMPT = """You are an expert fraud analyst AI embedded in a real-time security operations centre.

Your job is to explain a flagged transaction alert in plain, clear language that a human analyst can act on immediately.

Rules for your response:
1. Write 3-5 sentences maximum. Be concise.
2. First sentence: state what happened (the transaction facts).
3. Second sentence: explain WHY the rule triggered — what made this suspicious.
4. Third sentence: what the analyst should look for or consider next.
5. Use plain English — no jargon, no bullet points, no markdown formatting.
6. Do NOT invent facts not present in the alert data.
7. Do NOT say "I" or refer to yourself. Write as a system report."""


def build_investigator_user_prompt(alert: dict) -> str:
    """Build the user prompt for a specific alert."""
    txn = alert.get("transaction", {})
    return f"""Explain the following flagged transaction alert:

Alert ID       : {alert.get('id', 'unknown')}
Rule triggered : {alert.get('rule_triggered', 'unknown')}
Severity       : {alert.get('severity', 'unknown')}
Alert time     : {alert.get('timestamp', 'unknown')}

Transaction details:
  ID         : {txn.get('id', 'unknown')}
  Amount     : {txn.get('amount', 'unknown')}
  Location   : {txn.get('location', 'unknown')}
  Account    : {txn.get('account_id', 'unknown')}
  Timestamp  : {txn.get('timestamp', 'unknown')}

Provide a plain-language forensic explanation of why this alert was raised."""
