"""
Vanna AI client with Claude Sonnet 4.5 integration.

This module provides a custom Vanna implementation using:
- Claude Sonnet 4.5 as the LLM for SQL generation
- PostgreSQL/Supabase as the database backend
"""

import os
import logging
from typing import Optional

from vanna.base import VannaBase
from anthropic import Anthropic

logger = logging.getLogger(__name__)


class VannaClient(VannaBase):
    """
    Custom Vanna implementation using Claude Sonnet 4.5 for LLM.

    This extends VannaBase to use Anthropic's Claude instead of OpenAI,
    providing better SQL generation quality for complex queries.
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize the Vanna client with Claude."""
        super().__init__(config=config)

        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not set - using environment default")

        self.model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-5-20250514")
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None

        # Database connection settings
        self.db_host = os.environ.get(
            "DATABASE_HOST",
            "supabase-metaflow-postgresql.hyperplane-supabase-metaflow.svc.cluster.local",
        )
        self.db_port = os.environ.get("DATABASE_PORT", "5432")
        self.db_name = os.environ.get("DATABASE_NAME", "postgres")
        self.db_user = os.environ.get("DATABASE_USER", "postgres")
        self.db_password = os.environ.get("DATABASE_PASSWORD", "")
        self.db_schema = os.environ.get("DATABASE_SCHEMA", "reagan_crm")

        # Training data storage (in-memory for now, could be persisted)
        self._ddl_training = []
        self._doc_training = []
        self._sql_training = []

        logger.info(f"Vanna client initialized with model: {self.model}")

    def system_message(self, message: str) -> dict:
        """Create a system message for Claude."""
        return {"role": "system", "content": message}

    def user_message(self, message: str) -> dict:
        """Create a user message for Claude."""
        return {"role": "user", "content": message}

    def assistant_message(self, message: str) -> dict:
        """Create an assistant message for Claude."""
        return {"role": "assistant", "content": message}

    def submit_prompt(self, prompt: str, **kwargs) -> str:
        """
        Submit a prompt to Claude and get the response.

        This is the core method that Vanna uses to interact with the LLM.
        """
        if not self.client:
            raise ValueError(
                "Anthropic client not initialized - check ANTHROPIC_API_KEY"
            )

        try:
            # Build the system prompt for SQL generation
            system_prompt = """You are an expert SQL query generator. Your task is to convert natural language questions into accurate PostgreSQL queries.

Guidelines:
1. Generate ONLY the SQL query - no explanations unless asked
2. Use proper PostgreSQL syntax
3. Include appropriate JOINs when querying related tables
4. Use meaningful column aliases for readability
5. Handle NULL values appropriately
6. Use LIMIT to prevent large result sets unless specifically asked for all data
7. Format dates appropriately for PostgreSQL
8. When uncertain about column names, use the most likely match based on the schema provided

Database Schema Context:
""" + self._get_schema_context()

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            raise

    def _get_schema_context(self) -> str:
        """Build schema context from training data."""
        context = ""

        if self._ddl_training:
            context += "\n--- DDL (Table Definitions) ---\n"
            for ddl in self._ddl_training:
                context += f"{ddl}\n\n"

        if self._doc_training:
            context += "\n--- Documentation ---\n"
            for doc in self._doc_training:
                context += f"{doc}\n\n"

        if self._sql_training:
            context += "\n--- Example Queries ---\n"
            for q, sql in self._sql_training:
                context += f"Question: {q}\nSQL: {sql}\n\n"

        return context if context else "No schema context available yet."

    def train(
        self,
        question: Optional[str] = None,
        sql: Optional[str] = None,
        ddl: Optional[str] = None,
        documentation: Optional[str] = None,
    ) -> str:
        """
        Train the model with example data.

        Args:
            question: Example natural language question
            sql: The corresponding SQL query
            ddl: DDL statement (CREATE TABLE, etc.)
            documentation: Documentation about the database/business logic
        """
        if ddl:
            self._ddl_training.append(ddl)
            logger.info(f"Added DDL training data: {ddl[:100]}...")
            return f"Added DDL: {ddl[:50]}..."

        if documentation:
            self._doc_training.append(documentation)
            logger.info(f"Added documentation: {documentation[:100]}...")
            return f"Added documentation: {documentation[:50]}..."

        if question and sql:
            self._sql_training.append((question, sql))
            logger.info(f"Added Q&A pair: {question}")
            return f"Added example: {question}"

        return "No training data provided"

    def get_training_data(self) -> dict:
        """Get all stored training data."""
        return {
            "ddl": self._ddl_training,
            "documentation": self._doc_training,
            "sql_examples": [{"question": q, "sql": s} for q, s in self._sql_training],
        }

    def generate_sql(self, question: str, **kwargs) -> str:
        """
        Generate SQL from a natural language question.

        This is the main entry point for SQL generation.
        """
        # Build a comprehensive prompt
        prompt = f"""Given the following question, generate a PostgreSQL query to answer it.

Question: {question}

Important:
- Use the schema '{self.db_schema}' for all table references (e.g., {self.db_schema}.accounts)
- Return ONLY the SQL query, no explanation
- Use appropriate JOINs if the question requires data from multiple tables
- Include a LIMIT clause if appropriate to avoid large result sets
- Use meaningful column aliases

Generate the SQL query:"""

        return self.submit_prompt(prompt, **kwargs)

    def connect_to_postgres(self):
        """
        Connect to the PostgreSQL/Supabase database.

        Returns a connection string that can be used with psycopg2 or SQLAlchemy.
        """
        connection_string = (
            f"postgresql://{self.db_user}:{self.db_password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )
        return connection_string

    def run_sql(self, sql: str) -> list:
        """
        Execute SQL and return results.

        This method is used by Vanna to execute generated queries.
        """
        import psycopg2
        from psycopg2.extras import RealDictCursor

        try:
            conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
            )

            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                results = cur.fetchall()
                return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            raise
        finally:
            if conn:
                conn.close()


# Global client instance
_vanna_client: Optional[VannaClient] = None


def get_vanna_client() -> VannaClient:
    """Get or create the Vanna client singleton."""
    global _vanna_client
    if _vanna_client is None:
        _vanna_client = VannaClient()

        # Auto-train with database schema on startup
        _auto_train_schema(_vanna_client)

    return _vanna_client


def _auto_train_schema(vanna: VannaClient):
    """Automatically train Vanna with the database schema on startup."""
    try:
        import psycopg2

        conn = psycopg2.connect(
            host=vanna.db_host,
            port=vanna.db_port,
            dbname=vanna.db_name,
            user=vanna.db_user,
            password=vanna.db_password,
        )

        with conn.cursor() as cur:
            # Get table definitions for the target schema
            cur.execute(
                """
                SELECT table_name, column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_schema = %s
                ORDER BY table_name, ordinal_position
            """,
                (vanna.db_schema,),
            )

            columns = cur.fetchall()

            if columns:
                # Group by table
                tables = {}
                for table, col, dtype, nullable in columns:
                    if table not in tables:
                        tables[table] = []
                    tables[table].append(
                        f"  {col} {dtype}" + (" NOT NULL" if nullable == "NO" else "")
                    )

                # Create DDL for each table
                for table, cols in tables.items():
                    ddl = (
                        f"CREATE TABLE {vanna.db_schema}.{table} (\n"
                        + ",\n".join(cols)
                        + "\n);"
                    )
                    vanna.train(ddl=ddl)

                logger.info(
                    f"Auto-trained Vanna with {len(tables)} tables from schema {vanna.db_schema}"
                )
            else:
                logger.warning(f"No tables found in schema {vanna.db_schema}")

    except Exception as e:
        logger.error(f"Error auto-training schema: {e}")
        # Don't fail startup - schema can be trained later
    finally:
        if conn:
            conn.close()
