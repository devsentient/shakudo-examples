import os
import json

from langchain_openai import ChatOpenAI
from connections.base import DatabaseConnection
from connections.SupabasePostgresql import PostgreSQLConnection 
# from connections.DatabricksSparksql import DatabricksSQLConnection

# Openai Env:
api_key = os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_OPENAI_API_KEY", "")
local_llm = os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_HYPERPLANE_JOB_PARAMETER_LLM_ENDPOINTS", "{}")         
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
        # 'sparksql': DatabricksSQLConnection(),
    }
    return db[database_name]


