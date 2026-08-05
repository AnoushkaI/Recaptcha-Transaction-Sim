# Database Migration Guide: SQLite to Production SQL (PostgreSQL / MySQL)

This guide provides instructions and technical steps for migrating the Recaptcha Transaction Simulation Fraud Engine from the default file-based **SQLite** database (`fraud_rules.db`) to a production-grade relational database such as **PostgreSQL** or **MySQL**.

---

## 📑 Table of Contents
1. [Why Migrate from SQLite?](#1-why-migrate-from-sqlite)
2. [Recommended Database Engines](#2-recommended-database-engines)
3. [Data Type Mapping Reference](#3-data-type-mapping-reference)
4. [Target Schema DDL Scripts](#4-target-schema-ddl-scripts)
   - [PostgreSQL Schema](#postgresql-schema)
   - [MySQL Schema](#mysql-schema)
5. [Data Migration Options](#5-data-migration-options)
   - [Option A: Custom Python Data Migration Script](#option-a-custom-python-data-migration-script-recommended)
   - [Option B: Using pgloader (CLI Tool)](#option-b-using-pgloader-cli-tool)
6. [Backend Code Integration Steps](#6-backend-code-integration-steps)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Update Configuration (`backend/config.py`)](#step-2-update-configuration-backendconfigpy)
   - [Step 3: Refactor Database Module (`backend/core/db.py`)](#step-3-refactor-database-module-backendcoredbpy)
7. [Verification & Testing](#7-verification--testing)

---

## 1. Why Migrate from SQLite?

While **SQLite** is zero-config and fast for local development and unit tests, migrating to an enterprise SQL database offers:

- **High Concurrency & MVCC:** Multi-process and multi-worker FastAPI instances without file-level write locking errors (`database is locked`).
- **Connection Pooling:** Built-in connection pooling for high-throughput fraud transaction simulation.
- **Native JSON Support:** Optimized `JSONB` indexes for SOC condition payloads and transaction rules.
- **Centralized Security & Auditing:** Independent access controls, encrypted network transit (TLS/SSL), and cloud hosting (AWS RDS, GCP Cloud SQL, Azure Database).

---

## 2. Recommended Database Engines

| Database Engine | Recommendation | Primary Use Case |
| :--- | :--- | :--- |
| **PostgreSQL 14+** | 🌟 **Strongly Recommended** | Best compliance, native `JSONB` indexing, robust hash-chained audit logging, high concurrency. |
| **MySQL 8.0+ / MariaDB** | Alternative | Good web-scale performance, standard relational features. |
| **SQLAlchemy ORM** | **Abstraction Layer** | Recommended for FastAPI code abstraction (allows swapping between SQLite, Postgres, and MySQL seamlessly). |

---

## 3. Data Type Mapping Reference

| Data Type | SQLite (`fraud_rules.db`) | PostgreSQL Target | MySQL Target |
| :--- | :--- | :--- | :--- |
| **Primary Key (UUID/Text)** | `TEXT PRIMARY KEY` | `VARCHAR(255) PRIMARY KEY` | `VARCHAR(255) PRIMARY KEY` |
| **Auto-Increment ID** | `INTEGER AUTOINCREMENT` | `SERIAL` or `BIGSERIAL` | `BIGINT AUTO_INCREMENT` |
| **JSON Payload** | `TEXT` | `JSONB` or `TEXT` | `JSON` or `LONGTEXT` |
| **Floating Risk Score** | `REAL` | `DOUBLE PRECISION` | `DOUBLE` |
| **Timestamps** | `TEXT` (ISO 8601) | `TIMESTAMPTZ` or `VARCHAR(64)`| `DATETIME` or `VARCHAR(64)` |

---

## 4. Target Schema DDL Scripts

### PostgreSQL Schema

```sql
-- Create database
CREATE DATABASE fraud_engine_db;
\c fraud_engine_db;

-- 1. Rules Table
CREATE TABLE IF NOT EXISTS rules (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_by_command TEXT NOT NULL
);

-- 2. Audit Log Table (Tamper-Evident SHA-256 Chained Log)
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

-- 3. Rule History Table
CREATE TABLE IF NOT EXISTS rule_history (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(255) NOT NULL,
    version INT NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    command TEXT NOT NULL
);

-- 4. Custom Profiles Table
CREATE TABLE IF NOT EXISTS custom_profiles (
    name VARCHAR(255) PRIMARY KEY,
    profile_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. SOC Rules Table
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

-- 6. SOC Audit Log Table
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

-- Performance Indexes
CREATE INDEX idx_soc_audit_tx_id ON soc_audit_log(transaction_id);
CREATE INDEX idx_soc_audit_timestamp ON soc_audit_log(timestamp);
CREATE INDEX idx_audit_log_rule_id ON audit_log(rule_id);
```

### MySQL Schema

```sql
CREATE DATABASE IF NOT EXISTS fraud_engine_db;
USE fraud_engine_db;

CREATE TABLE IF NOT EXISTS rules (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code TEXT NOT NULL,
    description TEXT NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_by_command TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_id VARCHAR(255) NOT NULL,
    timestamp VARCHAR(64) NOT NULL,
    command TEXT NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    prev_hash VARCHAR(64) NOT NULL,
    hash VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rule_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    rule_id VARCHAR(255) NOT NULL,
    version INT NOT NULL,
    code TEXT NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at VARCHAR(64) NOT NULL,
    command TEXT NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS custom_profiles (
    name VARCHAR(255) PRIMARY KEY,
    profile_json JSON NOT NULL,
    updated_at VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS soc_rules (
    rule_id VARCHAR(255) PRIMARY KEY,
    profile_id VARCHAR(255) NOT NULL,
    rule_name VARCHAR(255) NOT NULL,
    conditions_json JSON NOT NULL,
    action VARCHAR(50) NOT NULL DEFAULT 'BLOCK',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
    created_at VARCHAR(64) NOT NULL,
    hit_count INT NOT NULL DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS soc_audit_log (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    timestamp VARCHAR(64) NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    rule_id VARCHAR(255) NOT NULL DEFAULT '',
    event_type VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    risk_score DOUBLE NOT NULL DEFAULT 0.0,
    reason TEXT NOT NULL DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## 5. Data Migration Options

### Option A: Custom Python Data Migration Script (Recommended)

Save the following script as `scripts/migrate_sqlite_to_pg.py` and run it to transfer existing data from `fraud_rules.db` into PostgreSQL.

```python
"""
Script: scripts/migrate_sqlite_to_pg.py
Description: Migrates existing data from SQLite (fraud_rules.db) to PostgreSQL.
"""

import sqlite3
import psycopg2
from psycopg2.extras import execute_values
import os

SQLITE_DB = os.getenv("DATABASE_PATH", "fraud_rules.db")
POSTGRES_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fraud_engine_db")

def migrate():
    print(f"Connecting to SQLite ({SQLITE_DB})...")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print(f"Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(POSTGRES_URL)
    pg_cur = pg_conn.cursor()

    tables = ["rules", "audit_log", "rule_history", "custom_profiles", "soc_rules", "soc_audit_log"]

    for table in tables:
        print(f"Migrating table '{table}'...")
        rows = sqlite_cur.execute(f"SELECT * FROM {table}").fetchall()
        if not rows:
            print(f"  No rows found in {table}. Skipping.")
            continue

        columns = rows[0].keys()
        cols_str = ", ".join(columns)
        placeholders = ", ".join(["%s"] * len(columns))

        insert_query = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;"
        data_tuples = [tuple(row[col] for col in columns) for row in rows]

        execute_values(pg_cur, insert_query, data_tuples)
        pg_conn.commit()
        print(f"  Successfully migrated {len(data_tuples)} rows to PostgreSQL table '{table}'.")

    sqlite_conn.close()
    pg_conn.close()
    print("✨ Migration complete successfully!")

if __name__ == "__main__":
    migrate()
```

---

### Option B: Using `pgloader` (CLI Tool)

If `pgloader` is installed on your environment, you can run a single command:

```bash
pgloader fraud_rules.db postgresql://postgres:password@localhost:5432/fraud_engine_db
```

---

## 6. Backend Code Integration Steps

### Step 1: Install Dependencies
Install Python drivers for PostgreSQL / SQLAlchemy:
```bash
pip install psycopg2-binary sqlalchemy
```
Add `psycopg2-binary` and `sqlalchemy` to `requirements.txt`.

---

### Step 2: Update Configuration (`backend/config.py`)

Modify `Settings` in `backend/config.py` to accept database connection strings:

```python
class Settings(BaseSettings):
    # Support both SQLite paths and PostgreSQL/MySQL Database URLs
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///fraud_rules.db")
```

Add your database string to `.env`:
```env
# For PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/fraud_engine_db

# For MySQL
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/fraud_engine_db
```

---

### Step 3: Refactor Database Module (`backend/core/db.py`)

Using **SQLAlchemy** allows the application to dynamically connect to **either** SQLite or PostgreSQL depending on `DATABASE_URL`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///fraud_rules.db")

# Handles connection pooling for Postgres/MySQL or single-thread for SQLite
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL, pool_size=10, max_overflow=20)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

## 7. Verification & Testing

1. Run unit and integration tests to verify database functions:
   ```bash
   pytest tests/
   ```
2. Check that API routes respond correctly:
   ```bash
   curl http://localhost:8000/api/rules
   curl http://localhost:8000/api/audit-log
   ```
3. Test hash-chain verification:
   The audit log SHA-256 hash chaining remains intact when migrated because hashes are deterministic strings calculated on row insertion.
