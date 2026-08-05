"""
Script: scripts/migrate_sqlite_to_pg.py
Description: Migrates existing data from SQLite (fraud_rules.db) to PostgreSQL.
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os
import sys
from urllib.parse import urlparse, unquote
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv(Path(__file__).parent.parent / ".env")

SQLITE_DB = os.getenv("DATABASE_PATH", "fraud_rules.db")
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fraud_engine_db")



def connect_postgres(url: str):
    """Parse DATABASE_URL and connect via keyword args to handle special chars in password."""
    parsed = urlparse(url)
    return psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        user=parsed.username,
        password=unquote(parsed.password) if parsed.password else None,
        dbname=parsed.path.lstrip("/"),
    )


def migrate():
    print(f"Connecting to SQLite database: {SQLITE_DB}...")
    if not os.path.exists(SQLITE_DB):
        print(f"Warning: SQLite database file '{SQLITE_DB}' does not exist yet. Nothing to migrate.")
        return

    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print(f"Connecting to PostgreSQL database: {POSTGRES_URL}...")
    try:
        pg_conn = connect_postgres(POSTGRES_URL)
        pg_cur = pg_conn.cursor()
    except Exception as err:
        print(f"ERROR: Could not connect to PostgreSQL: {err}")
        print("Please check your PostgreSQL credentials or ensure the PostgreSQL server is running.")
        sqlite_conn.close()
        sys.exit(1)

    tables = ["rules", "audit_log", "rule_history", "custom_profiles", "soc_rules", "soc_audit_log"]

    for table in tables:
        print(f"Migrating table '{table}'...")
        try:
            rows = sqlite_cur.execute(f"SELECT * FROM {table}").fetchall()
        except sqlite3.OperationalError:
            print(f"  INFO: Table '{table}' not present in SQLite database. Skipping.")
            continue

        if not rows:
            print(f"  INFO: No rows found in '{table}'. Skipping.")
            continue

        columns = list(rows[0].keys())
        cols_str = ", ".join(columns)
        data_tuples = [tuple(row[col] for col in columns) for row in rows]

        insert_query = f"INSERT INTO {table} ({cols_str}) VALUES %s ON CONFLICT DO NOTHING;"
        execute_values(pg_cur, insert_query, data_tuples)
        pg_conn.commit()
        print(f"  OK: Migrated {len(data_tuples)} rows to PostgreSQL table '{table}'.")

    sqlite_conn.close()
    pg_conn.close()
    print("\nSQLite to PostgreSQL migration completed successfully!")


if __name__ == "__main__":
    migrate()
