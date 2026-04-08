"""Create the leads table in PostgreSQL for storing customer leads."""

import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS leads (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    email      VARCHAR(255) UNIQUE NOT NULL,
    phone      VARCHAR(50),
    address    TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


def create_leads_table() -> None:
    """Connect to PostgreSQL and create the leads table if it doesn't exist."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set in environment variables.")

    conn = None
    cursor = None
    try:
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        print("🛠️  Creating 'leads' table (if not exists)...")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()

        print("✅ 'leads' table is ready.")
        print("\nSchema:")
        print("  id         SERIAL PRIMARY KEY")
        print("  name       VARCHAR(255) NOT NULL")
        print("  email      VARCHAR(255) UNIQUE NOT NULL")
        print("  phone      VARCHAR(50)")
        print("  address    TEXT")
        print("  created_at TIMESTAMPTZ DEFAULT NOW()")

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("\n🔒 Database connection closed.")


if __name__ == "__main__":
    create_leads_table()
