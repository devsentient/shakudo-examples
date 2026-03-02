import json
import os

from langchain_community.chat_models.ollama import ChatOllama
from langchain_openai import ChatOpenAI
from tomark import Tomark

from connections.base import DatabaseConnection
from connections.BigQueryGGsql import BigQuerySQLConnection
from connections.SupabaseGraphql import GraphqlConnection
from connections.SupabasePostgresql import PostgreSQLConnection

# from connections.DatabricksSparksql import DatabricksSQLConnection

# Openai Env:
api_key = os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_OPENAI_API_KEY", "")
local_llm = os.environ.get("HYPERPLANE_JOB_PARAMETER_LLM_ENDPOINTS", "{}")
local_llm_endpoints = json.loads(local_llm)


def uniform_grab_value(x):
    if hasattr(x, "content"):
        value = x.content
    else:
        value = x
    return value


def get_db(database_name: str) -> DatabaseConnection:
    db = {
        "postgresql": PostgreSQLConnection(),
        "graphql": GraphqlConnection(),
        "bq": BigQuerySQLConnection(),
        # 'sparksql': DatabricksSQLConnection(),
    }
    return db[database_name]


def get_llm(force_json=False):
    llm = ChatOpenAI(
        openai_api_key=api_key,
        model_name="gpt-4o",
        model_kwargs=(
            {
                "response_format": {
                    "type": "json_object",
                }
            }
            if force_json
            else {}
        ),
        max_tokens=512,
        temperature=0,
    )
    return llm


def get_ollama(force_json=False):
    return ChatOllama(
        base_url="http://ollama-sqlcoder.hyperplane-ollama.svc.cluster.local:11434",
        model="qwen2:latest",
        temperature=0.03,
        repeat_penalty=1.0,
        stop=["<|im_end|>"],
        format="json" if force_json else None,
    )


def get_codeqwen(force_json=True):
    llm = ChatOllama(
        base_url="http://ollama-sqlcoder.hyperplane-ollama.svc.cluster.local:11434",
        model="codeqwen:7b-chat-v1.5-q6_K",
        temperature=0.01,
        repeat_penalty=1.0,
        stop=["<|im_end|>"],
        format="json" if force_json else None,
    )
    return llm


async def exec_sql(language: str, sqlCode: str):
    res = await get_db(language).exec_query_with_ret(sqlCode)
    if res["status"] == "ok":
        table = json.loads(res["context"])
        if len(table) > 0:
            table = Tomark.table(table)
        else:
            table = "This query returns empty table"
    else:
        table = ""
    return table


def load_glossary() -> dict | None:
    """
    Load business glossary from JSON/YAML file.
    Glossary maps business terms to database entities.

    Expected format:
    {
        "terms": {
            "donation": {"tables": ["donations", "gifts"], "columns": ["amount", "donor_id"]},
            "donor": {"tables": ["donors", "contacts"], "columns": ["name", "email"]}
        },
        "table_descriptions": {
            "donations": "Records of all donations received",
            "donors": "Contact information for donors"
        }
    }
    """
    glossary_path = os.environ.get("GLOSSARY_PATH", "glossary.json")

    if not os.path.exists(glossary_path):
        alt_paths = [
            "/app/glossary.json",
            "/tmp/git/monorepo/glossary.json",
            os.path.join(os.path.dirname(__file__), "..", "glossary.json"),
        ]
        for alt in alt_paths:
            if os.path.exists(alt):
                glossary_path = alt
                break
        else:
            return None

    try:
        with open(glossary_path, "r") as f:
            if glossary_path.endswith(".yaml") or glossary_path.endswith(".yml"):
                import yaml

                return yaml.safe_load(f)
            else:
                return json.load(f)
    except Exception as e:
        print(f"Warning: Could not load glossary from {glossary_path}: {e}")
        return None


def format_database_structure(db_structure: dict) -> str:
    """
    Format database structure for LLM consumption.

    Input: {schema_name: {table_name: [columns]}}
    Output: Human-readable string format
    """
    lines = []
    for schema_name, tables in db_structure.items():
        lines.append(f"\n=== Schema: {schema_name} ===")
        for table_name, columns in tables.items():
            cols_preview = columns[:10]
            if len(columns) > 10:
                cols_str = ", ".join(cols_preview) + f"... (+{len(columns) - 10} more)"
            else:
                cols_str = ", ".join(cols_preview)
            lines.append(f"  {table_name}: [{cols_str}]")
    return "\n".join(lines)
