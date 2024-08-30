from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
logging.basicConfig(level=logging.INFO)
import json

from utils.common import get_db, uniform_grab_value, exec_sql, get_codeqwen

from prompts.OPENHERMES_TEMPLATES import PROMPT_TABLE_FINDING, CUSTOM_PROMPT


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.turns = {}
    yield

app = FastAPI(docs_url=os.environ.get("DOCS_URL", "/os-nlp-sql-dify/docs"), 
                openapi_url=os.environ.get('OPENAPI_URL','/os-nlp-sql-dify/openapi.json'),
                redoc_url=None,
                title="NLP-SQL backend",
                description="A dify compatable nlp-sql backend",
                summary="Shakudo nlp-sql backend",
                version="0.0.1",
                lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    expose_headers=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


async def recommend_tables(userprompt, schema):

    language = 'postgresql'
    llm = get_codeqwen()
    parsed = await get_db(language).get_tables(schema)

    prompt_table = PROMPT_TABLE_FINDING.format_prompt(
        table_example=str(parsed), prompt=userprompt
    )
    tables = uniform_grab_value(await llm.ainvoke(prompt_table))
    tables = json.loads(tables)['data']

    tables = [t for t in tables if t in parsed]
    return tables



async def gen_sql(prompt: str, schema: str, tables: list[str]):
    language = 'postgresql'
    llm = get_codeqwen()

    table_spec, _ = await get_db(language).get_table_specs(tables, schema)

    info = "\n".join(                                                                         
            [f"Table name: {n}\nColumns:\n{d}\n" for n, d in table_spec.items()]                  
        )
    num_try = 3
    errMessage = ''

    while num_try > 0:
        prompt_built = CUSTOM_PROMPT.format(
            prompt=prompt,
            additional_err=errMessage,
            table_info=info,
            schema=schema,
            language=language,
        )
        query = uniform_grab_value(await llm.ainvoke(prompt_built))
        sqlCode = json.loads(query)['data']

        validated = await get_db(language).validate_query(sqlCode)
        validated = validated['message']

        if validated == '':
            break
        num_try -= 1
        
        errMessage = validated
        sqlCode = ''
    if sqlCode == '':
        return "Couldn't get sql query for this prompt"
    table = await exec_sql(language, sqlCode)

    message = {'sql': f"```sql\n{sqlCode}```", 'table': table}        

    return message


@app.get('/ff_sql')
async def fullflow(prompt: str, schema: str):
    tables = await recommend_tables(prompt, schema)
    resp = await gen_sql(prompt=prompt, schema=schema, tables=tables)
    return resp


@app.get('/')
async def get_health():
    return "It's good"


