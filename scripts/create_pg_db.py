import psycopg2
import os

# Use explicit keyword args so special characters like @ in password work correctly
DB_HOST = "localhost"
DB_PORT = 5432
DB_USER = os.getenv("PGUSER", "postgres")
DB_PASS = os.getenv("PGPASSWORD", "Shrutish@2006")
DB_NAME = "fraud_engine_db"

try:
    # Connect to the default 'postgres' database first
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname="postgres")
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    exists = cur.fetchone()

    if not exists:
        cur.execute(f'CREATE DATABASE {DB_NAME}')
        print(f"Database '{DB_NAME}' created successfully!")
    else:
        print(f"Database '{DB_NAME}' already exists.")

    conn.close()
    print("Connection successful! PostgreSQL credentials are correct.")
except Exception as e:
    print(f"Error: {e}")
