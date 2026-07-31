"""
Database Setup & Schema (`core/db.py`)

SQLite database connection manager and schema initialization.
File-based SQLite setup suitable for single-writer fraud rules engine.
"""

import sqlite3
import os
import logging
from typing import Generator

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "fraud_rules.db"


def get_db_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection configured with Row factory."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """
    Initializes SQLite tables:
    - rules: Active & inactive rule storage
    - audit_log: Cryptographically chained insert-only audit log
    - rule_history: Versioned rule history for revert support
    - custom_profiles: Simulator custom profiles
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Rules table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rules (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        code TEXT NOT NULL,
        description TEXT NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_by_command TEXT NOT NULL
    );
    """)

    # 2. Tamper-evident insert-only Audit Log table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        command TEXT NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL,
        prev_hash TEXT NOT NULL,
        hash TEXT NOT NULL
    );
    """)

    # 3. Rule History table for revert capability
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rule_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rule_id TEXT NOT NULL,
        version INTEGER NOT NULL,
        code TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        command TEXT NOT NULL
    );
    """)

    # 4. Custom Profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS custom_profiles (
        name TEXT PRIMARY KEY,
        profile_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    conn.commit()
    conn.close()
    logger.info(f"Initialized database schema successfully at {db_path}")
