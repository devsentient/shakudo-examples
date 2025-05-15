"""Entry point for the FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
import json

from pydantic import BaseModel

from prompts.DIFY_TEMPLATES import TEMPLATE, TEMPLATE_TABLE_FINDING
from utils.common import exec_sql, get_codeqwen, get_db, uniform_grab_value

LANGUAGE = "postgresql"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan management for the FastAPI application."""
    app.state.turns = {}
    yield


app = FastAPI(
    docs_url=os.environ.get("DOCS_URL", "/os-nlp-sql-dify/docs"),
    openapi_url=os.environ.get("OPENAPI_URL", "/os-nlp-sql-dify/openapi.json"),
    redoc_url=None,
    title="NLP-SQL backend",
    description="A dify compatable nlp-sql backend",
    summary="Shakudo nlp-sql backend",
    version="0.0.1",
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


async def recommend_tables(userprompt, schema):
    """
    Recommend tables based on user's prompt and schema.
    It generates the prompt dynamically and return it.
    """
    parsed = await get_db(LANGUAGE).get_tables(schema)
    
    excluded_tables = os.getenv('EXCLUDE_TABLE_NAMES', '').split(',')
    for tname in excluded_tables:
        parsed.pop(tname, None)
    print(f"Tables considered: {parsed.keys()}")

    prompt_table = TEMPLATE_TABLE_FINDING.format(
        table_example=str(parsed), prompt=userprompt, excluded_tables=excluded_tables
    )
    return prompt_table


async def gen_sql(prompt: str, schema: str, tables: list[str]):
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


async def validate_and_exec_sql(sqlCode: str) -> str:
    """
    Validates and executes SQL query.
    """
    validated = await get_db(LANGUAGE).validate_query(sqlCode)
    validatedMsg = validated["message"]

    if validatedMsg != "":
        logging.warning("INVALID SQL CODE: " + sqlCode)
        return "Couldn't get sql query for this prompt"

    table = await exec_sql(LANGUAGE, sqlCode)
    message = {"sql": f"```sql\n{sqlCode}```", "table": table}
    return message


@app.get("/recommendTables")
async def recommend_tables_endpoint(prompt: str, schema: str):
    """
    Endpoint to recommend tables based on user's prompt and schema.
    """
    return await recommend_tables(prompt, schema)


class SQLRequest(BaseModel):
    prompt: str
    schema: str
    tables: dict


@app.post("/generateSQL")
async def generate_sql_endpoint(data: SQLRequest):
    """
    Endpoint to generate SQL query based on user's prompt and schema.
    """
    try:
        tablesString = data.tables["data"]
        tablesArray = tablesString.split(",")
        return await gen_sql(data.prompt, data.schema, tablesArray)
    except:
        print(f"Could not get 'data' field in tables field in payload.")
        return "Couldn't get sql query for this prompt."


@app.post("/validateAndExecuteSQL")
async def validate_and_exec_sql_endpoint(sqlCode: dict):
    """
    Endpoint to validate and execute SQL query.
    """
    sqlCode = sqlCode["data"]
    return await validate_and_exec_sql(sqlCode)


@app.get("/")
async def get_health():
    return "It's good"
