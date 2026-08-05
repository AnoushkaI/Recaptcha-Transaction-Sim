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


def _parse_json(val: Any) -> Dict[str, Any]:
    """Safely parse JSON data — handles dict/list objects returned directly by PostgreSQL JSONB."""
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return {}
    return {}


def _to_str(val: Any) -> str:
    """Safely convert value to string — handles datetime objects from PostgreSQL TIMESTAMPTZ."""
    if val is None:
        return ""
    if isinstance(val, str):
        return val
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)



def _next_rule_id(cursor) -> str:
    """Auto-generate sequential SOC rule IDs: R-001, R-002, ... safely avoiding UNIQUE constraint conflicts."""
    cursor.execute("SELECT rule_id FROM soc_rules")
    rows = cursor.fetchall()
    max_num = 0
    for r in rows:
        rid = r[0] if isinstance(r, (tuple, list)) else r["rule_id"]
        if rid and str(rid).startswith("R-"):
            try:
                num = int(str(rid).replace("R-", ""))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return f"R-{max_num + 1:03d}"


def _eval_conditions(
    conditions: Dict[str, Any],
    tx: Dict[str, Any],
    rule_profile_id: Optional[str] = None,
) -> bool:
    """
    Evaluate ALL conditions against a transaction dict.
    Enforces strict profile scoping so rules belonging to one fraud profile
    do not over-block transactions from other fraud profiles.
    """
    tx_profile = str(
        tx.get("profile_id")
        or tx.get("profile")
        or tx.get("profile_name")
        or ""
    ).upper()

    # 1. Strict Profile scoping from rule table column
    if rule_profile_id and rule_profile_id.upper() not in ("UNKNOWN", "ALL", ""):
        if tx_profile != rule_profile_id.upper():
            return False

    # 2. Check profile_id from conditions dict if present
    if "profile_id" in conditions:
        cond_prof = str(conditions["profile_id"]).upper()
        if tx_profile != cond_prof:
            return False

    for key, threshold in conditions.items():
        if key == "profile_id":
            continue
        elif key == "amount_gt":
            if float(tx.get("amount", 0)) <= float(threshold):
                return False
        elif key == "amount_lt":
            if float(tx.get("amount", 0)) >= float(threshold):
                return False
        elif key == "merchant_category":
            tx_cat = str(tx.get("merchant_category") or tx.get("category") or "")
            if tx_cat.lower() != str(threshold).lower():
                return False
        elif key == "vpn_prob_gt":
            if float(tx.get("vpn_probability", 0)) <= float(threshold):
                return False
        elif key == "automation_score_gt":
            if float(tx.get("automation_probability", 0)) <= float(threshold):
                return False
        elif key == "known_device_lt":
            if float(tx.get("known_device_probability", 1.0)) >= float(threshold):
                return False
        elif key == "unknown_device":
            is_unknown = float(tx.get("known_device_probability", 1.0)) < 0.5
            if bool(threshold) != is_unknown:
                return False
        elif key == "classification":
            tx_cls = str(tx.get("classification", "")).upper()
            target_cls = str(threshold).upper()
            if target_cls in ("HIGH_RISK", "SUSPICIOUS"):
                if tx_cls not in ("HIGH_RISK", "SUSPICIOUS"):
                    return False
            elif tx_cls != target_cls:
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
            "SELECT rule_id, profile_id, rule_name, conditions_json, action FROM soc_rules WHERE status = 'ACTIVE' ORDER BY created_at ASC"
        )
        rows = cursor.fetchall()
        for row in rows:
            conditions = _parse_json(row["conditions_json"])
            r_profile = row["profile_id"]
            if _eval_conditions(conditions, tx, rule_profile_id=r_profile):
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
                "conditions": _parse_json(r["conditions_json"]),
                "action": r["action"],
                "status": r["status"],
                "created_at": _to_str(r["created_at"]),
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


def delete_soc_rule(rule_id: str, db_path: str = DEFAULT_DB_PATH) -> bool:
    """Permanently delete a SOC rule by ID. Returns True if deleted."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM soc_rules WHERE rule_id = ?", (rule_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_all_soc_rules(db_path: str = DEFAULT_DB_PATH) -> int:
    """Permanently delete all SOC rules. Returns count of deleted rules."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM soc_rules")
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def update_soc_rule(
    rule_id: str,
    rule_name: Optional[str] = None,
    action: Optional[str] = None,
    conditions: Optional[Dict[str, Any]] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> Optional[Dict[str, Any]]:
    """Update name, action, and/or conditions of an existing SOC rule."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM soc_rules WHERE rule_id = ?", (rule_id,))
        row = cursor.fetchone()
        if not row:
            return None

        new_name = rule_name if rule_name is not None else row["rule_name"]
        new_action = action.upper() if action is not None else row["action"]
        new_conditions_json = (
            json.dumps(conditions) if conditions is not None else row["conditions_json"]
        )

        cursor.execute(
            """
            UPDATE soc_rules
            SET rule_name = ?, action = ?, conditions_json = ?
            WHERE rule_id = ?
            """,
            (new_name, new_action, new_conditions_json, rule_id),
        )
        conn.commit()

        cursor.execute("SELECT * FROM soc_rules WHERE rule_id = ?", (rule_id,))
        updated = cursor.fetchone()
        return {
            "rule_id": updated["rule_id"],
            "profile_id": updated["profile_id"],
            "rule_name": updated["rule_name"],
            "conditions": _parse_json(updated["conditions_json"]),
            "action": updated["action"],
            "status": updated["status"],
            "created_at": _to_str(updated["created_at"]),
            "hit_count": updated["hit_count"],
        }
    finally:
        conn.close()


def get_soc_rule_by_id(rule_id: str, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    """Retrieve a single SOC rule by ID."""
    init_db(db_path)
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM soc_rules WHERE rule_id = ?", (rule_id,))
        r = cursor.fetchone()
        if not r:
            return None
        return {
            "rule_id": r["rule_id"],
            "profile_id": r["profile_id"],
            "rule_name": r["rule_name"],
            "conditions": _parse_json(r["conditions_json"]),
            "action": r["action"],
            "status": r["status"],
            "created_at": _to_str(r["created_at"]),
            "hit_count": r["hit_count"],
        }
    finally:
        conn.close()


def format_soc_rule_code(
    rule_id: str,
    rule_name: str,
    profile_id: str,
    conditions: Dict[str, Any],
    action: str = "BLOCK",
    description: str = "",
) -> str:
    """Format SOC rule conditions into standard syntax-highlighted Python code representation matching SOC specs."""
    clean_name = rule_name.replace(" Prevention", "").strip()
    header = (
        f"# Prevent {clean_name}\n"
        f"# Rule ID: {rule_id}\n"
    )

    cond_lines = []
    if "profile_id" in conditions:
        cond_lines.append(f'tx.profile_id == "{conditions["profile_id"]}"')
    elif profile_id and profile_id.upper() not in ("UNKNOWN", "ALL", ""):
        cond_lines.append(f'tx.profile_id == "{profile_id}"')

    if "amount_lt" in conditions:
        cond_lines.append(f"tx.amount < {float(conditions['amount_lt']):.1f}")
    if "amount_gt" in conditions:
        cond_lines.append(f"tx.amount >= {float(conditions['amount_gt']):.2f}")
    if "merchant_category" in conditions:
        cond_lines.append(f'tx.merchant_category == "{conditions["merchant_category"]}"')
    if "vpn_prob_gt" in conditions:
        cond_lines.append(f"tx.vpn_probability > {float(conditions['vpn_prob_gt']):.2f}")
    if "automation_score_gt" in conditions:
        cond_lines.append(f"tx.automation_probability > {float(conditions['automation_score_gt']):.2f}")
    if "known_device_lt" in conditions:
        cond_lines.append(f"tx.known_device_probability < {float(conditions['known_device_lt']):.2f}")
    elif conditions.get("unknown_device"):
        cond_lines.append("tx.known_device_probability < 0.30")
    if conditions.get("tor_used"):
        cond_lines.append("tx.tor_probability > 0.30")
    if "classification" in conditions:
        cls_val = str(conditions["classification"]).upper()
        if cls_val in ("HIGH_RISK", "SUSPICIOUS"):
            cond_lines.append('tx.classification in ("HIGH_RISK", "SUSPICIOUS")')
        else:
            cond_lines.append(f'tx.classification == "{cls_val}"')
    if "location_in" in conditions:
        cond_lines.append(f'tx.location in {conditions["location_in"]}')

    if not cond_lines:
        cond_lines.append("tx.final_risk_score >= 0.60")

    indented_conds = "\n        and ".join(cond_lines)
    func_code = f"def evaluate(tx):\n    return (\n        {indented_conds}\n    )\n\nACTION = \"{action.upper()}\""
    return header + "\n" + func_code


def extract_conditions_from_transaction(tx: Dict[str, Any]) -> Dict[str, Any]:
    """
    Auto-extract precise, tight multi-signal conditions from a transaction dict.
    Ensures that only transactions specifically matching this exact risk pattern get blocked.
    """
    conditions: Dict[str, Any] = {}

    # 1. Profile ID scoping
    prof_id = tx.get("profile_id") or tx.get("profile")
    if prof_id and str(prof_id).upper() not in ("UNKNOWN", "ALL", ""):
        conditions["profile_id"] = str(prof_id)

    # 2. Precise Amount threshold (within 85% of target transaction amount)
    amount = float(tx.get("amount", 0))
    if amount > 0:
        if amount < 100.0:
            conditions["amount_lt"] = round(amount * 1.15, 2)
        else:
            conditions["amount_gt"] = round(amount * 0.85, 2)

    # 3. Merchant Category
    m_cat = tx.get("merchant_category") or tx.get("category")
    if m_cat:
        conditions["merchant_category"] = str(m_cat)

    # 4. Telemetry Signals — only extract if transaction exhibits elevated risk (>0.50)
    vpn_prob = float(tx.get("vpn_probability", 0))
    if vpn_prob >= 0.50:
        conditions["vpn_prob_gt"] = round(vpn_prob * 0.85, 2)

    auto_prob = float(tx.get("automation_probability", 0))
    if auto_prob >= 0.50:
        conditions["automation_score_gt"] = round(auto_prob * 0.85, 2)

    known_dev = float(tx.get("known_device_probability", 1.0))
    if known_dev <= 0.40:
        conditions["known_device_lt"] = round(known_dev * 1.25, 2)

    tor_prob = float(tx.get("tor_probability", 0))
    if tor_prob >= 0.35:
        conditions["tor_used"] = True

    return conditions
