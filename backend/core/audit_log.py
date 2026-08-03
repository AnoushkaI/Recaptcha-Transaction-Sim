"""
Audit Logger (`core/audit_log.py`)

Provides tamper-evident SHA-256 hash-chained logging of all rule deployments
and reverts. Enforces insert-only audit persistence in SQLite.
"""

import hashlib
import sqlite3
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from backend.core.schemas import Rule, AuditLogEntry
from backend.core.db import get_db_connection, init_db, DEFAULT_DB_PATH




logger = logging.getLogger(__name__)

GENESIS_HASH = "0" * 64


def compute_entry_hash(prev_hash: str, rule_id: str, timestamp: str, command: str, code: str, status: str) -> str:
    """Calculates SHA-256 hash digest for hash-chaining."""
    payload = f"{prev_hash}:{rule_id}:{timestamp}:{command}:{code}:{status}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLogger:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path: str = db_path
        init_db(self.db_path)

    def _get_latest_hash(self, cursor: sqlite3.Cursor) -> str:
        """Fetch hash of most recent audit log entry or genesis hash if empty."""
        cursor.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return row["hash"]
        return GENESIS_HASH

    def log_deploy_rule(self, rule: Rule, command: str) -> AuditLogEntry:
        """
        Logs rule deployment to audit_log with hash chaining and updates SQLite rules table.
        """
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            prev_hash = self._get_latest_hash(cursor)
            entry_hash = compute_entry_hash(
                prev_hash=prev_hash,
                rule_id=rule.id,
                timestamp=timestamp,
                command=command,
                code=rule.code,
                status=rule.status
            )

            # 1. Insert into audit_log
            cursor.execute("""
            INSERT INTO audit_log (rule_id, timestamp, command, code, status, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rule.id, timestamp, command, rule.code, rule.status, prev_hash, entry_hash))
            entry_id = cursor.lastrowid

            # 2. Upsert into rules table
            cursor.execute("""
            INSERT INTO rules (id, name, code, description, created_at, status, created_by_command)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                code=excluded.code,
                description=excluded.description,
                status=excluded.status,
                created_by_command=excluded.created_by_command
            """, (rule.id, rule.name, rule.code, rule.description, rule.created_at, rule.status, rule.created_by_command))

            # 3. Append to rule_history
            cursor.execute("SELECT COUNT(*) as count FROM rule_history WHERE rule_id = ?", (rule.id,))
            version = cursor.fetchone()["count"] + 1

            cursor.execute("""
            INSERT INTO rule_history (rule_id, version, code, status, created_at, command)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (rule.id, version, rule.code, rule.status, timestamp, command))

            conn.commit()

            return AuditLogEntry(
                id=entry_id,
                rule_id=rule.id,
                timestamp=timestamp,
                command=command,
                code=rule.code,
                status=rule.status,
                prev_hash=prev_hash,
                hash=entry_hash
            )

        finally:
            conn.close()

    def log_revert_rule(self, rule_id: str, command: str) -> Optional[AuditLogEntry]:
        """
        Logs a rule revert action, updates rule status in SQLite to 'reverted'.
        """
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            cursor.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
            rule_row = cursor.fetchone()
            if not rule_row:
                return None

            prev_hash = self._get_latest_hash(cursor)
            reverted_status = "reverted"
            code = rule_row["code"]

            entry_hash = compute_entry_hash(
                prev_hash=prev_hash,
                rule_id=rule_id,
                timestamp=timestamp,
                command=command,
                code=code,
                status=reverted_status
            )

            # 1. Insert into audit_log
            cursor.execute("""
            INSERT INTO audit_log (rule_id, timestamp, command, code, status, prev_hash, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (rule_id, timestamp, command, code, reverted_status, prev_hash, entry_hash))
            entry_id = cursor.lastrowid

            # 2. Update status in rules table
            cursor.execute("UPDATE rules SET status = 'reverted' WHERE id = ?", (rule_id,))

            conn.commit()

            return AuditLogEntry(
                id=entry_id,
                rule_id=rule_id,
                timestamp=timestamp,
                command=command,
                code=code,
                status=reverted_status,
                prev_hash=prev_hash,
                hash=entry_hash
            )

        finally:
            conn.close()

    def get_audit_logs(self, rule_id: Optional[str] = None) -> List[AuditLogEntry]:
        """Fetch audit log history."""
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        try:
            if rule_id:
                cursor.execute("SELECT * FROM audit_log WHERE rule_id = ? ORDER BY id ASC", (rule_id,))
            else:
                cursor.execute("SELECT * FROM audit_log ORDER BY id ASC")

            rows = cursor.fetchall()
            return [
                AuditLogEntry(
                    id=row["id"],
                    rule_id=row["rule_id"],
                    timestamp=row["timestamp"],
                    command=row["command"],
                    code=row["code"],
                    status=row["status"],
                    prev_hash=row["prev_hash"],
                    hash=row["hash"]
                ) for row in rows
            ]
        finally:
            conn.close()

    def get_active_rules(self) -> List[Rule]:
        """Fetch all currently active rules from SQLite."""
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM rules WHERE status = 'active'")
            rows = cursor.fetchall()
            return [
                Rule(
                    id=row["id"],
                    name=row["name"],
                    code=row["code"],
                    description=row["description"],
                    created_at=row["created_at"],
                    status=row["status"],
                    created_by_command=row["created_by_command"]
                ) for row in rows
            ]
        finally:
            conn.close()

    def verify_hash_chain_integrity(self) -> Tuple[bool, Optional[int]]:
        """
        Cryptographic integrity check of the audit log hash chain.
        Returns (True, None) if valid, or (False, tampered_row_id) if chain is broken.
        """
        init_db(self.db_path)
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()


        try:
            cursor.execute("SELECT * FROM audit_log ORDER BY id ASC")
            rows = cursor.fetchall()

            expected_prev_hash = GENESIS_HASH

            for row in rows:
                row_id = row["id"]
                actual_prev = row["prev_hash"]
                actual_hash = row["hash"]

                # 1. Check prev_hash link
                if actual_prev != expected_prev_hash:
                    logger.error(f"Hash chain broken at row {row_id}: prev_hash mismatch!")
                    return False, row_id

                # 2. Recompute hash
                recomputed = compute_entry_hash(
                    prev_hash=actual_prev,
                    rule_id=row["rule_id"],
                    timestamp=row["timestamp"],
                    command=row["command"],
                    code=row["code"],
                    status=row["status"]
                )

                if recomputed != actual_hash:
                    logger.error(f"Tamper detected at row {row_id}: hash payload mismatch!")
                    return False, row_id

                expected_prev_hash = actual_hash

            return True, None

        finally:
            conn.close()
