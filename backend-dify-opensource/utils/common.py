import os
import json

from langchain_openai import ChatOpenAI
from langchain_community.chat_models.ollama import ChatOllama
from connections.base import DatabaseConnection
from connections.SupabasePostgresql import PostgreSQLConnection 
from connections.SupabaseGraphql import GraphqlConnection       
from connections.BigQueryGGsql import BigQuerySQLConnection     
from tomark import Tomark
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
        model_name='gpt-4o',
        model_kwargs={
            'response_format': {
                'type': 'json_object',
            }
        } if force_json else {},
        max_tokens=512,
        temperature=0
    )
    return llm


def get_ollama(force_json=False):
    return ChatOllama(
        base_url='http://ollama-sqlcoder.hyperplane-ollama.svc.cluster.local:11434',
        model="qwen2:latest",
        temperature=0.03,
        repeat_penalty=1.0,
        stop=["<|im_end|>"],
        format='json' if force_json else None,
    )


def get_codeqwen(force_json=True):
    llm = ChatOllama(
            base_url="http://ollama-sqlcoder.hyperplane-ollama.svc.cluster.local:11434",
            model="codeqwen:7b-chat-v1.5-q6_K",
            temperature=0.01,
            repeat_penalty=1.0,
            stop=["<|im_end|>"],
            format='json' if force_json else None
        )
    return llm



async def exec_sql(language: str, sqlCode: str):
    res = await get_db(language).exec_query_with_ret(sqlCode)
    if res['status'] == 'ok':
        table = json.loads(res['context'])
        if len(table) > 0:
            table = Tomark.table(table)
        else:
            table = "This query returns empty table"
    else:
        table = ''
    return table