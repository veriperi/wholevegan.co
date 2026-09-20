"""
Loads the generated CSVs into a Postgres database (Supabase/Neon free tier,
or any Postgres you have) instead of a local SQLite file — this is what
lets your dashboard and dbt project point at a real, shareable connection
string rather than a file that only exists on your laptop.

Setup:
    pip install sqlalchemy psycopg2-binary pandas python-dotenv

    Create a .env file next to this script with:
        DATABASE_URL=postgresql://user:password@host:port/dbname

Run:
    python load_db.py
"""

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]

engine = create_engine(DATABASE_URL)

with engine.begin() as conn:
    with open("../sql/schema.sql") as f:
        conn.execute(text(f.read()))

TABLES = [
    ("customers", "customers.csv"),
    ("products", "products.csv"),
    ("orders", "orders.csv"),
    ("order_items", "order_items.csv"),
    ("returns", "returns.csv"),
]

with engine.begin() as conn:
    for table, file in TABLES:
        df = pd.read_csv(f"../data/{file}")
        # Truncate then reload so this script is safely re-runnable
        conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        df.to_sql(table, conn, if_exists="append", index=False)
        print(f"Loaded {len(df)} rows into {table}")

print("Done. Database is ready for dbt.")
