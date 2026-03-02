#!/usr/bin/env python3
"""
Execute Reagan CRM schema creation and seed data.
Run this script once to set up the database.

Usage:
    python schema/execute_schema.py

Environment variables required:
    DATABASE_HOST: PostgreSQL host
    DATABASE_PORT: PostgreSQL port (default: 5432)
    DATABASE_NAME: Database name (default: postgres)
    DATABASE_USER: Database user
    DATABASE_PASSWORD: Database password
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from pathlib import Path


def get_db_config():
    """Get database connection config from environment."""
    return {
        "host": os.environ.get(
            "DATABASE_HOST",
            "supabase-metaflow-postgresql.hyperplane-supabase-metaflow.svc.cluster.local",
        ),
        "port": os.environ.get("DATABASE_PORT", "5432"),
        "dbname": os.environ.get("DATABASE_NAME", "postgres"),
        "user": os.environ.get("DATABASE_USER", "postgres"),
        "password": os.environ.get("DATABASE_PASSWORD", ""),
    }


def execute_sql_file(cursor, filepath: Path):
    """Execute a SQL file."""
    print(f"  Executing: {filepath.name}")
    with open(filepath, "r") as f:
        sql = f.read()

    # Split by semicolon to handle multiple statements
    # But be careful with functions that contain semicolons
    statements = []
    current = []

    for line in sql.split("\n"):
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            stmt = "\n".join(current).strip()
            if stmt and stmt != ";":
                statements.append(stmt)
            current = []

    # Execute each statement
    for stmt in statements:
        if stmt.strip():
            try:
                cursor.execute(stmt)
            except Exception as e:
                print(f"    Error executing statement: {e}")
                print(f"    Statement: {stmt[:100]}...")
                raise


def main():
    print("=" * 60)
    print("Reagan CRM Database Setup")
    print("=" * 60)

    config = get_db_config()
    print(f"\nConnecting to: {config['host']}:{config['port']}/{config['dbname']}")

    if not config["password"]:
        print("ERROR: DATABASE_PASSWORD environment variable not set")
        print("\nPlease set the required environment variables:")
        print("  export DATABASE_HOST=<host>")
        print("  export DATABASE_USER=<user>")
        print("  export DATABASE_PASSWORD=<password>")
        sys.exit(1)

    schema_dir = Path(__file__).parent

    try:
        conn = psycopg2.connect(**config)
        conn.autocommit = True
        cursor = conn.cursor()

        print("\n[1/2] Creating schema and tables...")
        execute_sql_file(cursor, schema_dir / "001_create_schema.sql")
        print("  ✓ Schema created")

        print("\n[2/2] Inserting seed data...")
        execute_sql_file(cursor, schema_dir / "002_seed_data.sql")
        print("  ✓ Seed data inserted")

        # Verify counts
        print("\n[Verification] Checking record counts...")
        cursor.execute("SELECT COUNT(*) FROM reagan_crm.account")
        account_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reagan_crm.contact")
        contact_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reagan_crm.opportunity")
        opp_count = cursor.fetchone()[0]

        print(f"  Accounts: {account_count}")
        print(f"  Contacts: {contact_count}")
        print(f"  Opportunities: {opp_count}")

        cursor.close()
        conn.close()

        print("\n" + "=" * 60)
        print("DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print("\nYou can now run the Vanna training script:")
        print("  python schema/003_vanna_training.py")

    except psycopg2.Error as e:
        print(f"\nERROR: Database connection failed: {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nERROR: SQL file not found: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
