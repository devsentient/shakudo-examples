"""Entry point for the FastAPI application."""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from prompts.DIFY_TEMPLATES import (
    TEMPLATE,
    TEMPLATE_TABLE_FINDING,
    TEMPLATE_SCHEMA_DETECTION,
    TEMPLATE_GLOSSARY_SECTION,
)
from utils.common import exec_sql, get_db, load_glossary, format_database_structure

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LANGUAGE = "postgresql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan management for the FastAPI application."""
    app.state.turns = {}
    app.state.schema_cache = None
    app.state.schema_cache_ttl = 300  # 5 minutes cache
    app.state.last_cache_time = 0
    yield


app = FastAPI(
    docs_url=os.environ.get("DOCS_URL", "/os-nlp-sql-dify/docs"),
    openapi_url=os.environ.get("OPENAPI_URL", "/os-nlp-sql-dify/openapi.json"),
    redoc_url=None,
    title="NLP-SQL backend",
    description="A dify compatable nlp-sql backend with auto-schema detection",
    summary="Shakudo nlp-sql backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    expose_headers=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request Models
# ============================================================================


class SQLRequest(BaseModel):
    prompt: str
    schema_name: str = Field(
        ..., alias="schema"
    )  # Accept "schema" in JSON for backwards compat
    tables: dict

    model_config = {"populate_by_name": True}  # Allow both schema_name and schema


class AutoDetectRequest(BaseModel):
    prompt: str
    use_glossary: bool = True


class AskQuestionRequest(BaseModel):
    prompt: str
    use_glossary: bool = True


# ============================================================================
# Core Functions
# ============================================================================


async def get_all_schemas_and_tables(use_cache: bool = True) -> dict:
    """
    Fetch all schemas and their tables from the database.
    Returns: {schema_name: {table_name: [columns]}}
    """
    import time

    current_time = time.time()
    cache_valid = (
        use_cache
        and app.state.schema_cache is not None
        and (current_time - app.state.last_cache_time) < app.state.schema_cache_ttl
    )

    if cache_valid:
        return app.state.schema_cache

    db = get_db(LANGUAGE)
    result = await db.get_all_tables_all_schemas(exclude_system_schemas=True)

    app.state.schema_cache = result
    app.state.last_cache_time = current_time

    return result


async def auto_detect_schema_and_tables(prompt: str, use_glossary: bool = True) -> str:
    """
    Use LLM to automatically detect the best schema and tables for a given prompt.
    Returns: {"schema": str, "tables": list, "confidence": str, "reasoning": str}
    """
    db_structure = await get_all_schemas_and_tables()

    if not db_structure:
        raise HTTPException(
            status_code=500,
            detail="No schemas found in database. Please check database connection.",
        )

    formatted_structure = format_database_structure(db_structure)

    glossary_section = ""
    if use_glossary:
        glossary = load_glossary()
        if glossary:
            glossary_section = TEMPLATE_GLOSSARY_SECTION.format(
                glossary=json.dumps(glossary, indent=2)
            )

    detection_prompt = TEMPLATE_SCHEMA_DETECTION.format(
        database_structure=formatted_structure,
        glossary_section=glossary_section,
        prompt=prompt,
    )

    return detection_prompt


async def recommend_tables(userprompt: str, schema: str) -> str:
    """
    Recommend tables based on user's prompt and schema.
    Returns the prompt for LLM to identify relevant tables.
    """
    parsed = await get_db(LANGUAGE).get_tables(schema)

    excluded_tables = os.getenv("EXCLUDE_TABLE_NAMES", "").split(",")
    excluded_tables = [t.strip() for t in excluded_tables if t.strip()]
    for tname in excluded_tables:
        parsed.pop(tname, None)
    logger.info(f"Tables considered for schema '{schema}': {list(parsed.keys())}")

    prompt_table = TEMPLATE_TABLE_FINDING.format(
        table_example=str(parsed), prompt=userprompt, excluded_tables=excluded_tables
    )
    return prompt_table


async def recommend_tables_auto(userprompt: str):
    """
    Recommend tables when schema is not provided.
    First detects the schema, then recommends tables within it.
    """
    detection_prompt = await auto_detect_schema_and_tables(
        userprompt, use_glossary=True
    )
    return detection_prompt


async def gen_sql(prompt: str, schema: str, tables: list[str]) -> str:
    """
    Generates template for LLM to generate SQL query.
    """
    table_spec, _ = await get_db(LANGUAGE).get_table_specs(tables, schema)
    info = "\n".join(
        [f"Table name: {n}\nColumns:\n{d}\n" for n, d in table_spec.items()]
    )
    prompt_built = TEMPLATE.format(
        prompt=prompt,
        table_info=info,
        schema=schema,
        LANGUAGE=LANGUAGE,
    )
    return prompt_built


async def validate_and_exec_sql(sqlCode: str) -> dict:
    """
    Validates and executes SQL query.
    """
    validated = await get_db(LANGUAGE).validate_query(sqlCode)
    validatedMsg = validated["message"]

    if validatedMsg != "":
        logger.warning(f"INVALID SQL CODE: {sqlCode}")
        return {
            "error": "Couldn't get sql query for this prompt",
            "details": str(validatedMsg),
        }

    table = await exec_sql(LANGUAGE, sqlCode)
    message = {"sql": f"```sql\n{sqlCode}```", "table": table}
    return message


# ============================================================================
# API Endpoints
# ============================================================================


@app.get("/")
async def get_health():
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/getAvailableSchemas")
async def get_available_schemas():
    """
    Returns all available schemas and their tables.
    Useful for debugging and understanding database structure.
    """
    try:
        db_structure = await get_all_schemas_and_tables(use_cache=False)
        schema_summary = {
            schema: {"table_count": len(tables), "tables": list(tables.keys())}
            for schema, tables in db_structure.items()
        }
        return {"schemas": schema_summary, "total_schemas": len(db_structure)}
    except Exception as e:
        logger.error(f"Error fetching schemas: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching schemas: {str(e)}")


@app.get("/getDatabaseStructure")
async def get_database_structure():
    """
    Returns full database structure with all schemas, tables, and columns.
    """
    try:
        db_structure = await get_all_schemas_and_tables(use_cache=True)
        return {"structure": db_structure}
    except Exception as e:
        logger.error(f"Error fetching database structure: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching database structure: {str(e)}"
        )


@app.post("/autoDetectSchema")
async def auto_detect_schema_endpoint(data: AutoDetectRequest):
    """
    Given a natural language question, returns an LLM prompt to detect
    the appropriate schema and tables.

    The caller should send this prompt to an LLM and parse the JSON response
    to get: {"schema": str, "tables": list, "confidence": str, "reasoning": str}
    """
    try:
        detection_prompt = await auto_detect_schema_and_tables(
            data.prompt, use_glossary=data.use_glossary
        )
        return detection_prompt
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in auto-detect schema: {e}")
        raise HTTPException(status_code=500, detail=f"Error detecting schema: {str(e)}")


@app.get("/recommendTables")
async def recommend_tables_endpoint(prompt: str, schema: Optional[str] = None):
    """
    Endpoint to recommend tables based on user's prompt.

    If schema is provided, returns tables from that schema.
    If schema is not provided, returns a prompt for auto-detection.
    """
    if schema:
        return await recommend_tables(prompt, schema)
    else:
        return await recommend_tables_auto(prompt)


@app.post("/generateSQL")
async def generate_sql_endpoint(data: SQLRequest):
    """
    Endpoint to generate SQL query based on user's prompt and schema.
    """
    try:
        tablesString = data.tables.get("data", "")
        if not tablesString:
            return {"error": "No tables provided in 'data' field"}
        tablesArray = [t.strip() for t in tablesString.split(",") if t.strip()]
        return await gen_sql(data.prompt, data.schema_name, tablesArray)
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        return {"error": "Couldn't get sql query for this prompt.", "details": str(e)}


@app.post("/validateAndExecuteSQL")
async def validate_and_exec_sql_endpoint(sqlCode: dict):
    """
    Endpoint to validate and execute SQL query.
    """
    sql = sqlCode.get("data", "")
    if not sql:
        return {"error": "No SQL code provided in 'data' field"}
    return await validate_and_exec_sql(sql)


@app.post("/askQuestion")
async def ask_question_endpoint(data: AskQuestionRequest):
    """
    Unified endpoint for asking questions without specifying schema.

    This endpoint orchestrates the full flow:
    1. Auto-detects the appropriate schema and tables
    2. Returns the detection prompt for the caller to send to LLM

    The caller should:
    1. Send the returned prompt to an LLM to get schema/tables
    2. Call /generateSQL with the detected schema and tables
    3. Call /validateAndExecuteSQL with the generated SQL

    For a fully automated flow, use the Dify workflow which handles all steps.
    """
    try:
        detection_prompt = await auto_detect_schema_and_tables(
            data.prompt, use_glossary=data.use_glossary
        )

        return {
            "step": "schema_detection",
            "prompt_for_llm": detection_prompt,
            "next_steps": [
                "1. Send 'prompt_for_llm' to your LLM",
                "2. Parse the JSON response to get schema and tables",
                "3. Call POST /generateSQL with {prompt, schema, tables}",
                "4. Send the SQL generation prompt to your LLM",
                "5. Call POST /validateAndExecuteSQL with the generated SQL",
            ],
            "original_question": data.prompt,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in askQuestion: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error processing question: {str(e)}"
        )


@app.post("/clearSchemaCache")
async def clear_schema_cache():
    """
    Clears the schema cache. Useful when database structure changes.
    """
    app.state.schema_cache = None
    app.state.last_cache_time = 0
    return {"status": "cache_cleared"}


@app.get("/glossary")
async def get_glossary():
    """
    Returns the business glossary if configured.
    The glossary maps business terms to database entities.
    """
    glossary = load_glossary()
    if glossary:
        return {"glossary": glossary}
    return {
        "glossary": None,
        "message": "No glossary configured. Set GLOSSARY_PATH env var or create glossary.json",
    }
