"""
backend/soc/rule_store.py — SOC Condition-Based Prevention Rule Store

Stores, retrieves, and evaluates condition-based SOC prevention rules.
Rules are JSON key-value conditions (not Python code) for one-click deployment
from the investigation panel. Parallel to the existing code-based RulesEngine.

Condition keys supported:
  amount_gt          : float  — amount > threshold
  amount_lt          : float  — amount < threshold
  vpn_prob_gt        : float  — vpn_probability > threshold
  automation_score_gt: float  — automation_probability > threshold
  unknown_device     : bool   — known_device_probability < 0.5
  classification     : str    — matches HIGH_RISK / SUSPICIOUS / SAFE
  location_in        : list   — location code in list
  tor_used           : bool   — tor_probability > 0.3

Enforcement actions: ALLOW | CHALLENGE | BLOCK
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.core.db import get_db_connection, init_db, DEFAULT_DB_PATH


def _next_rule_id(cursor) -> str:
    """Auto-generate sequential SOC rule IDs: R-001, R-002, ..."""
    cursor.execute("SELECT COUNT(*) FROM soc_rules")
    count = cursor.fetchone()[0]
    return f"R-{count + 1:03d}"


def _eval_conditions(conditions: Dict[str, Any], tx: Dict[str, Any]) -> bool:
    """Evaluate ALL conditions against a transaction dict. Returns True if ALL match."""
    for key, threshold in conditions.items():
        if key == "amount_gt":
            if float(tx.get("amount", 0)) <= float(threshold):
                return False
        elif key == "amount_lt":
            if float(tx.get("amount", 0)) >= float(threshold):
                return False
        elif key == "vpn_prob_gt":
            if float(tx.get("vpn_probability", 0)) <= float(threshold):
                return False
        elif key == "automation_score_gt":
            if float(tx.get("automation_probability", 0)) <= float(threshold):
                return False
        elif key == "unknown_device":
            is_unknown = float(tx.get("known_device_probability", 1.0)) < 0.5
            if bool(threshold) != is_unknown:
                return False
        elif key == "classification":
            if str(tx.get("classification", "")).upper() != str(threshold).upper():
                return False
        elif key == "location_in":
            if tx.get("location", "") not in list(threshold):
                return False
        elif key == "tor_used":
            is_tor = float(tx.get("tor_probability", 0)) > 0.3
            if bool(threshold) != is_tor:
                return False
    return True


def deploy_soc_rule(
    profile_id: str,
    rule_name: str,
    conditions: Dict[str, Any],
    action: str = "BLOCK",
    db_path: str = DEFAULT_DB_PATH,
) -> Dict[str, Any]:
    """Deploy a new SOC condition-based rule. Returns the deployed rule dict."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        rule_id = _next_rule_id(cursor)
        created_at = datetime.now(timezone.utc).isoformat()
        conditions_json = json.dumps(conditions)
        cursor.execute(
            """
            INSERT INTO soc_rules (rule_id, profile_id, rule_name, conditions_json, action, status, created_at, hit_count)
            VALUES (?, ?, ?, ?, ?, 'ACTIVE', ?, 0)
            """,
            (rule_id, profile_id, rule_name, conditions_json, action.upper(), created_at),
        )
        conn.commit()
        return {
            "rule_id": rule_id,
            "profile_id": profile_id,
            "rule_name": rule_name,
            "conditions": conditions,
            "action": action.upper(),
            "status": "ACTIVE",
            "created_at": created_at,
            "hit_count": 0,
        }
    finally:
        conn.close()


def evaluate_transaction_against_soc_rules(
    tx: Dict[str, Any],
    db_path: str = DEFAULT_DB_PATH,
) -> Tuple[str, str, str]:
    """
    Evaluate a transaction dict against all ACTIVE SOC rules.
    Returns (action, matched_rule_id, reason).
    First matching rule wins. If no rule matches, returns ('ALLOW', '', '').
    """
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT rule_id, rule_name, conditions_json, action FROM soc_rules WHERE status = 'ACTIVE' ORDER BY created_at ASC"
        )
        rows = cursor.fetchall()
        for row in rows:
            conditions = json.loads(row["conditions_json"])
            if _eval_conditions(conditions, tx):
                reason = f"{row['rule_name']} matched: " + ", ".join(
                    f"{k}={v}" for k, v in conditions.items()
                )
                return row["action"], row["rule_id"], reason
        return "ALLOW", "", ""
    finally:
        conn.close()


def increment_rule_hit(rule_id: str, db_path: str = DEFAULT_DB_PATH) -> None:
    """Increment the hit count for a rule."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE soc_rules SET hit_count = hit_count + 1 WHERE rule_id = ?", (rule_id,)
        )
        conn.commit()
    finally:
        conn.close()


def get_all_soc_rules(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    """Return all SOC rules (active and inactive)."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM soc_rules ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [
            {
                "rule_id": r["rule_id"],
                "profile_id": r["profile_id"],
                "rule_name": r["rule_name"],
                "conditions": json.loads(r["conditions_json"]),
                "action": r["action"],
                "status": r["status"],
                "created_at": r["created_at"],
                "hit_count": r["hit_count"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def deactivate_soc_rule(rule_id: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Set a SOC rule status to INACTIVE. Returns True if found and updated."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE soc_rules SET status = 'INACTIVE' WHERE rule_id = ?", (rule_id,)
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def extract_conditions_from_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-extract meaningful conditions from a transaction dict for one-click rule deployment.
    Produces the tightest reasonable rule based on the transaction's risk signals.
    """
    conditions: Dict[str, Any] = {}

    # Amount threshold — block transactions above 80% of this amount
    amount = float(tx.get("amount", 0))
    if amount > 500:
        conditions["amount_gt"] = round(amount * 0.7, 2)

    # VPN signal
    vpn_prob = float(tx.get("vpn_probability", 0))
    if vpn_prob > 0.5:
        conditions["vpn_prob_gt"] = round(vpn_prob * 0.8, 2)

    # Automation signal
    auto_prob = float(tx.get("automation_probability", 0))
    if auto_prob > 0.6:
        conditions["automation_score_gt"] = round(auto_prob * 0.8, 2)

    # Unknown device
    known_dev = float(tx.get("known_device_probability", 1.0))
    if known_dev < 0.5:
        conditions["unknown_device"] = True

    # TOR usage
    tor_prob = float(tx.get("tor_probability", 0))
    if tor_prob > 0.3:
        conditions["tor_used"] = True

    # Classification — always include for HIGH_RISK
    cls = str(tx.get("classification", "")).upper()
    if cls == "HIGH_RISK":
        conditions["classification"] = "HIGH_RISK"

    # Fallback — if nothing extracted, use amount-based rule
    if not conditions:
        conditions["amount_gt"] = max(100.0, amount * 0.5)

    return conditions
