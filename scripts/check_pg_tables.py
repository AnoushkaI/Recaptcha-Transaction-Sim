import psycopg2
from urllib.parse import urlparse, unquote
from pathlib import Path
from dotenv import load_dotenv
import os
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

url = os.getenv("DATABASE_URL")
parsed = urlparse(url)
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port or 5432,
    user=parsed.username,
    password=unquote(parsed.password) if parsed.password else None,
    dbname=parsed.path.lstrip("/"),
)
cur = conn.cursor()

tables = ["audit_log", "soc_rules", "soc_audit_log"]

print("Row counts in PostgreSQL:")
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM public.{table}")
    count = cur.fetchone()[0]
    print(f"  {table}: {count} rows")

# Show SOC rules if any
print("\nSOC Rules content:")
cur.execute("SELECT rule_id, rule_name, profile_id, action, status, hit_count FROM public.soc_rules ORDER BY created_at DESC")
soc_rows = cur.fetchall()
if soc_rows:
    for r in soc_rows:
        print(f"  [{r[4]}] {r[0]} | {r[1]} | profile={r[2]} | action={r[3]} | hits={r[5]}")
else:
    print("  No SOC rules in PostgreSQL yet.")
    print("  NOTE: SOC rules may still be saving to SQLite (fraud_rules.db).")
    print("  --> Please restart the backend for the DATABASE_URL changes to fully take effect.")

conn.close()
