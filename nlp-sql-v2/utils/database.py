"""
Database utilities for PostgreSQL/Supabase interaction.
"""

import os
import logging
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    "host": os.environ.get(
        "DATABASE_HOST",
        "supabase-metaflow-postgresql.hyperplane-supabase-metaflow.svc.cluster.local",
    ),
    "port": os.environ.get("DATABASE_PORT", "5432"),
    "dbname": os.environ.get("DATABASE_NAME", "postgres"),
    "user": os.environ.get("DATABASE_USER", "postgres"),
    "password": os.environ.get("DATABASE_PASSWORD", ""),
}

DB_SCHEMA = os.environ.get("DATABASE_SCHEMA", "reagan_crm")


def get_connection():
    """Get a database connection."""
    return psycopg2.connect(**DB_CONFIG)


async def execute_sql(sql: str, params: Optional[tuple] = None) -> list:
    """
    Execute a SQL query and return results as a list of dictionaries.

    Args:
        sql: The SQL query to execute
        params: Optional parameters for parameterized queries

    Returns:
        List of dictionaries, one per row
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)

            # Check if this is a SELECT query
            if cur.description:
                results = cur.fetchall()
                return [dict(row) for row in results]
            else:
                # For INSERT/UPDATE/DELETE, commit and return affected rows
                conn.commit()
                return [{"affected_rows": cur.rowcount}]

    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def get_table_metadata(schema: Optional[str] = None) -> dict:
    """
    Get metadata about all tables in the specified schema.

    Returns:
        Dictionary of {table_name: [column_info]}
    """
    schema = schema or DB_SCHEMA
    conn = None

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    t.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    col_description(
                        (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass,
                        c.ordinal_position
                    ) as column_comment
                FROM information_schema.tables t
                JOIN information_schema.columns c 
                    ON t.table_schema = c.table_schema 
                    AND t.table_name = c.table_name
                WHERE t.table_schema = %s
                    AND t.table_type = 'BASE TABLE'
                ORDER BY t.table_name, c.ordinal_position
            """,
                (schema,),
            )

            rows = cur.fetchall()

            # Group by table
            tables = {}
            for table, col, dtype, nullable, default, comment in rows:
                if table not in tables:
                    tables[table] = []
                tables[table].append(
                    {
                        "column": col,
                        "type": dtype,
                        "nullable": nullable == "YES",
                        "default": default,
                        "comment": comment,
                    }
                )

            return tables

    except psycopg2.Error as e:
        logger.error(f"Error getting table metadata: {e}")
        raise
    finally:
        if conn:
            conn.close()


async def validate_sql(sql: str) -> dict:
    """
    Validate SQL syntax without executing it.

    Uses EXPLAIN to check if the query is valid.
    """
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Use EXPLAIN to validate without execution
            cur.execute(f"EXPLAIN {sql}")
            return {"valid": True, "message": ""}

    except psycopg2.Error as e:
        return {"valid": False, "message": str(e)}
    finally:
        if conn:
            conn.close()


def create_schema_if_not_exists(schema: str = None):
    """Create the target schema if it doesn't exist."""
    schema = schema or DB_SCHEMA
    conn = None
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            conn.commit()
            logger.info(f"Schema '{schema}' created or already exists")
    except psycopg2.Error as e:
        logger.error(f"Error creating schema: {e}")
        raise
    finally:
        if conn:
            conn.close()
