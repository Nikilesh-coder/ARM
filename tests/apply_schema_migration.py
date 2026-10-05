import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL not set in .env")

migration_path = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations", "20260929010000_arm_mvp_schema.sql")

print(f"Reading migration from: {migration_path}")
with open(migration_path, "r", encoding="utf-8") as f:
    sql = f.read()

print("Connecting to database...")
conn = psycopg2.connect(DB_URL)
conn.autocommit = True
cur = conn.cursor()

print("Applying migration...")
cur.execute(sql)

print("Migration applied successfully!")
cur.close()
conn.close()
