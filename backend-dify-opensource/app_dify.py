"""Entry point for the FastAPI application."""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)
import json

from prompts.DIFY_TEMPLATES import TEMPLATE_TABLE_FINDING, TEMPLATE
from utils.common import exec_sql, get_codeqwen, get_db, uniform_grab_value


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
    language = "postgresql"
    # llm = get_codeqwen()
    parsed = await get_db(language).get_tables(schema)

    prompt_table = TEMPLATE_TABLE_FINDING.format(
        table_example=str(parsed), prompt=userprompt
    )
    # tables = uniform_grab_value(await llm.ainvoke(prompt_table))
    # tables = json.loads(tables)["data"]

    # tables = [t for t in tables if t in parsed]
    return prompt_table


async def gen_sql(prompt: str, schema: str, tables: list[str]):
    language = "postgresql"
    # llm = get_codeqwen()

    table_spec, _ = await get_db(language).get_table_specs(tables, schema)

    info = "\n".join(
        [f"Table name: {n}\nColumns:\n{d}\n" for n, d in table_spec.items()]
    )
    # num_try = 3
    errMessage = ""

    # while num_try > 0:
    prompt_built = TEMPLATE.format(
        prompt=prompt,
        additional_err=errMessage,
        table_info=info,
        schema=schema,
        language=language,
    )
    return prompt_built
        # query = uniform_grab_value(await llm.ainvoke(prompt_built))
        # sqlCode = json.loads(query)["data"]

    #     validated = await get_db(language).validate_query(sqlCode)
    #     validated = validated["message"]

    #     if validated == "":
    #         break
    #     num_try -= 1

    #     errMessage = validated
    #     sqlCode = ""
    # if sqlCode == "":
    #     return "Couldn't get sql query for this prompt"
    # table = await exec_sql(language, sqlCode)

    # message = {"sql": f"```sql\n{sqlCode}```", "table": table}

    # return message

async def validate_and_exec_sql(sqlCode: str) -> str:
    language = "postgresql"
    validated = await get_db(language).validate_query(sqlCode)
    print("Validated: ", validated)
    validatedMsg = validated["message"]

    if validatedMsg != "":
        logging.warning("INVALID SQL CODE: " + sqlCode)
        sqlCode = ""
    if sqlCode == "":
        return "Couldn't get sql query for this prompt"
    table = await exec_sql(language, sqlCode)

    message = {"sql": f"```sql\n{sqlCode}```", "table": table}

    return message


@app.get("/recommendTables")
async def recommend_tables_endpoint(prompt: str, schema: str):
    return await recommend_tables(prompt, schema)

from pydantic import BaseModel

class SQLRequest(BaseModel):
    prompt: str
    schema: str
    tables: str

@app.post("/generateSQL")
async def generate_sql_endpoint(data: SQLRequest):
    try:
        tablesArray = json.loads(data.tables)["data"]
        return await gen_sql(data.prompt, data.schema, tablesArray)
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed for tablesArray: {e}")
        return "Couldn't get sql query for this prompt."
    

@app.get("/validateAndExecuteSQL")
async def validate_and_exec_sql_endpoint(sqlCode: str):
    try:
        sqlCode = json.loads(sqlCode)["data"]
        return await validate_and_exec_sql(sqlCode)
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed for sqlCode: {e}")
        return "Unable to validate and execute SQL command."

@app.get("/ff_sql")
async def fullflow(prompt: str, schema: str):
    tables = await recommend_tables(prompt, schema)
    resp = await gen_sql(prompt=prompt, schema=schema, tables=tables)
    return resp


@app.get("/")
async def get_health():
    return "It's good"
