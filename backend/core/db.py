"""
Database Setup & Schema (`core/db.py`)

PostgreSQL database manager for production execution,
with SQLite support for isolated unit test fixtures.
"""

import os
import sqlite3
import logging
import re
from typing import Generator, Any, Optional, List
from urllib.parse import urlparse, unquote
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL") or "postgresql://postgres:Shrutish%402006@localhost:5432/fraud_engine_db"
DEFAULT_DB_PATH = DATABASE_URL

# SQLAlchemy engine setup for PostgreSQL ORM support
try:
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)
except Exception as e:
    logger.error(f"Failed to initialize SQLAlchemy engine with {DATABASE_URL}: {e}")
    raise e

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Any, None, None]:
    """SQLAlchemy Session dependency generator for FastAPI endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class PGCursorWrapper:
    """Cursor wrapper for PostgreSQL (psycopg2) providing dictionary row mapping and statement translation."""

    def __init__(self, pg_cursor: Any):
        self._cursor = pg_cursor
        self.lastrowid: Optional[int] = None

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        pg_query = query.replace("?", "%s")

        is_insert = pg_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in pg_query.upper()

        if is_insert and not has_returning:
            table_match = re.search(r"INSERT\s+INTO\s+([a-zA-Z0-9_]+)", pg_query, re.IGNORECASE)
            if table_match:
                tbl = table_match.group(1).lower()
                if tbl in ("audit_log", "rule_history", "soc_audit_log"):
                    pg_query += " RETURNING id"
                    has_returning = True

        if params:
            self._cursor.execute(pg_query, params)
        else:
            self._cursor.execute(pg_query)

        if is_insert and has_returning:
            try:
                res = self._cursor.fetchone()
                if res:
                    self.lastrowid = res["id"] if isinstance(res, dict) and "id" in res else res[0]
            except Exception:
                pass

        return self

    def fetchone(self) -> Optional[Any]:
        return self._cursor.fetchone()

    def fetchall(self) -> List[Any]:
        return self._cursor.fetchall()


class PGConnectionWrapper:
    """Connection wrapper that adapts psycopg2 connection to standard cursor interface."""

    def __init__(self, pg_conn: Any):
        self._conn = pg_conn

    def cursor(self) -> PGCursorWrapper:
        import psycopg2.extras
        cursor = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PGCursorWrapper(cursor)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()


def get_db_connection(target: Optional[str] = None) -> Any:
    """
    Returns a PostgreSQL database connection for PostgreSQL URLs / default app execution,
    or SQLite connection if a file path (.db / .sqlite) is passed for test isolation.
    """
    db_target = target or os.getenv("DATABASE_URL") or DATABASE_URL

    if db_target and (db_target.endswith(".db") or db_target.endswith(".sqlite") or db_target.startswith("sqlite:")):
        conn = sqlite3.connect(db_target)
        conn.row_factory = sqlite3.Row
        return conn

    import psycopg2
    parsed = urlparse(db_target)

    try:
        pg_conn = psycopg2.connect(
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            user=parsed.username or "postgres",
            password=unquote(parsed.password) if parsed.password else None,
            dbname=parsed.path.lstrip("/") or "fraud_engine_db",
        )
        return PGConnectionWrapper(pg_conn)
    except Exception as err:
        logger.error(f"Failed to connect to PostgreSQL at {db_target}: {err}")
        raise err


def init_db(target: Optional[str] = None) -> None:
    """
    Initializes PostgreSQL database schema (or SQLite schema if isolated test .db file is passed).
    """
    conn = get_db_connection(target)
    cursor = conn.cursor()

    is_pg = isinstance(conn, PGConnectionWrapper)

    if is_pg:
        # PostgreSQL Target Schema
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            rule_id VARCHAR(255) NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            command TEXT NOT NULL,
            code TEXT NOT NULL,
            status VARCHAR(50) NOT NULL,
            prev_hash VARCHAR(64) NOT NULL,
            hash VARCHAR(64) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soc_rules (
            rule_id VARCHAR(255) PRIMARY KEY,
            profile_id VARCHAR(255) NOT NULL,
            rule_name VARCHAR(255) NOT NULL,
            conditions_json JSONB NOT NULL,
            action VARCHAR(50) NOT NULL DEFAULT 'BLOCK',
            status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            hit_count INT NOT NULL DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soc_audit_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            transaction_id VARCHAR(255) NOT NULL,
            rule_id VARCHAR(255) NOT NULL DEFAULT '',
            event_type VARCHAR(100) NOT NULL,
            action VARCHAR(50) NOT NULL,
            risk_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            reason TEXT NOT NULL DEFAULT ''
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soc_audit_tx_id ON soc_audit_log(transaction_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_soc_audit_timestamp ON soc_audit_log(timestamp);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_log_rule_id ON audit_log(rule_id);")
    else:
        # SQLite Test Fixture Schema
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

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soc_rules (
            rule_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            rule_name TEXT NOT NULL,
            conditions_json TEXT NOT NULL,
            action TEXT NOT NULL DEFAULT 'BLOCK',
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            created_at TEXT NOT NULL,
            hit_count INTEGER NOT NULL DEFAULT 0
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS soc_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            rule_id TEXT NOT NULL DEFAULT '',
            event_type TEXT NOT NULL,
            action TEXT NOT NULL,
            risk_score REAL NOT NULL DEFAULT 0.0,
            reason TEXT NOT NULL DEFAULT ''
        );
        """)

    conn.commit()
    conn.close()
    logger.info("Initialized database schema successfully.")
