from psycopg2 import OperationalError, ProgrammingError, DataError, DatabaseError
import os
import json
import psycopg as pg
from psycopg.rows import dict_row
from connections.base import DatabaseConnection
from connections.sql_query_templates import get_sql_templates

default_postgres = "nlp-sql-postgresql.hyperplane-nlp-sql-v0"
dbname = os.environ.get("POSTGRES_DB_NAME", "postgres")
host = os.environ.get("POSTGRES_HOST", default_postgres)
user = os.environ.get("POSTGRES_USER", "supabase_admin")
port = os.environ.get("POSTGRES_PORT", "5432")
password = os.environ.get("HYPERPLANE_CUSTOM_SECRET_KEY_POSTGRES_PSWD", "postgres")
source_type = os.environ.get("SOURCE_TYPE","supabase")
conninfo = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
if "CLIENT_ENCODING" in os.environ:
    conninfo += f"?client_encoding={os.environ.get('CLIENT_ENCODING','utf8')}"
MAX_DB_RET = 60


def tables_parse(tables):
    """Parsing the sql response into a dictionary in format
    {
        table_1: [table_1_col_1_name, table_1_col_2_name, table_1_col_3_name, table_1_col_4_name,],
        table_2: [table_2_col_1_name, table_2_col_2_name, table_1_col_3_name, table_1_col_4_name,]
        ...
    }

    Args:
        tables (_type_): Response from postgres in format:
        [{'column_name': 'id', 'table_name': 'test'},
        {'column_name': 'name', 'table_name': 'test'}]

    """
    res = {}
    for t in tables:
        if t["table_name"] not in res:
            res[t["table_name"]] = []
        if len(res[t["table_name"]]) < 30:
            res[t["table_name"]].append(t["column_name"])
    return res

### Start psql definations
async def is_valid_psql_query(query):
    conn = None
    try:
        async with await pg.AsyncConnection.connect(conninfo, row_factory=dict_row) as conn:
            try:
                async with conn.cursor() as cur:
                    await cur.execute(
                        "EXPLAIN " + query
                    )  # Use EXPLAIN to check the query plan without execution
                return {"status": "ok", "message":""}
            except pg.Error as e:
                print(f"SQL Error: {e}")
                return {"status": "failed", "message": e}
    except Exception as e:
        return {"status": "failed", "message": e}
    finally:
        if conn:
            await conn.close()

async def get_psql_schemas(GET_SCHEMA_SQL:str):
    conn = await pg.AsyncConnection.connect(conninfo, row_factory=dict_row)
    async with conn:
        async with conn.cursor() as cur:
            await cur.execute(
               GET_SCHEMA_SQL
            )
            fetched = await cur.fetchmany(500)
            keys = list(fetched[0].keys()) if len(fetched) > 0 else []
            keeping = keys[:]
            limited = [{k: f[k] for k in keeping} for f in fetched]
            limited = [x["schema_name"] for x in limited]
    return limited

async def exec_psql_no_ret(sqlCode: str):
    err = True
    conn = None
    try:
        conn = await pg.AsyncConnection.connect(conninfo, row_factory=dict_row)
        async with conn:
            # Execute a SQL command without explicitly creating a cursor
            await conn.execute(sqlCode)
            ret = json.dumps({"ok": "executed"}, default=str)
            err = False
    except ProgrammingError as pe:
        ret = json.dumps({"error": f"Programming error: {pe}"})
    except DataError as de:
        ret = json.dumps({"error": f"Data error: {de}"})
    except OperationalError as oe:
        ret = json.dumps({"error": f"Operational error (connection issue): {oe}"})
    except DatabaseError as db_err:
        ret = json.dumps({"error": f"Database error: {db_err}"})
    except SyntaxError as se:
        ret = json.dumps({"error": f"Syntax error: {se}"})
    except Exception as e:
        ret = json.dumps({"error": f"General error: {type(e)} {e}"})
    finally:
        if conn:
            await conn.close()
    return {
        "status": "error" if err else "ok",
        "message": "Data founded and returned"
        if not err
        else "Failed, retry if possible.",
        "context": ret,
    }

async def get_table_specs(tables,GET_TABLE_SPECS_SQL,schema=None):
    conn = await pg.AsyncConnection.connect(conninfo, row_factory=dict_row)
    async with conn:
        async with conn.cursor() as cur:
            table_spec = {}
            for t in tables:
                query = GET_TABLE_SPECS_SQL
                if schema:
                    query = query.format(schema)

                await cur.execute(
                    query,
                    (t,),
                )
                table_spec[t] = [
                    (d["column_name"], d["data_type"])
                    for d in (await cur.fetchall())
                ][:]
    return table_spec, None

async def exec_psql(
    sqlCode: str
):
    err = True
    conn = None
    try:
        conn = await pg.AsyncConnection.connect(conninfo, row_factory=dict_row)
        async with conn:
            try:
                async with conn.cursor() as cur:
                    try:
                        await cur.execute(sqlCode)
                        fetched = await cur.fetchmany(MAX_DB_RET)
                        keys = list(fetched[0].keys()) if len(fetched) > 0 else []
                        keeping = keys[:MAX_DB_RET]

                        limited = [{k: f[k] for k in keeping} for f in fetched]

                        ret = json.dumps(limited, default=str)
                        err = False
                    except ProgrammingError as pe:
                        ret = json.dumps({"error": f"Programming error: {pe}"})
                    except DataError as de:
                        ret = json.dumps({"error": f"Data error: {de}"})
                    except DatabaseError as db_err:
                        ret = json.dumps({"error": f"Database error: {db_err}"})
            except OperationalError as oe:
                ret = json.dumps(
                    {"error": f"Operational error (connection issue): {oe}"}
                )
    except SyntaxError as se:
        ret = json.dumps({"error": f"Syntax error: {se}"})
    except Exception as e:
        ret = json.dumps({"error": f"General error: {type(e)} {e}"})
    finally:
        if conn:
            await conn.close()
    return {
        "status": "error" if err else "ok",
        "message": "Data founded and returned"
        if not err
        else "Failed, retry if possible.",
        "context": ret,
    }

async def get_tables_psql(schema,TABLE_PULLING_SQL):
    conn = False
    try:
        conn = await pg.AsyncConnection.connect(conninfo, row_factory=dict_row)
        async with conn:
            async with conn.cursor() as cur:
                await cur.execute(TABLE_PULLING_SQL.format(schema))
                tables = await cur.fetchall()
                parsed = tables_parse(tables)
    except Exception as e:
        raise e
    finally:
        if conn:
            await conn.close()
    return parsed


class PostgreSQLConnection(DatabaseConnection):
    def __init__(self, conninfo:str = conninfo, source_type:str = source_type):
        self.conninfo = conninfo
        self.source_type = source_type
        self.TABLE_PULLING_SQL, self.GET_SCHEMA_SQL, self.GET_TABLE_SPECS_SQL = get_sql_templates(self.source_type)

    async def get_schema(self):
        return await get_psql_schemas(GET_SCHEMA_SQL = self.GET_SCHEMA_SQL)
    
    async def validate_query(self, query):
        return await is_valid_psql_query(query)
    
    async def exec_query_with_ret(self, query):
        return await exec_psql(query)

    async def exec_query_without_ret(self, query):
        return await exec_psql_no_ret(query)
    
    async def get_tables(self, schema):
        return await get_tables_psql(schema,TABLE_PULLING_SQL=self.TABLE_PULLING_SQL)

    async def get_table_specs(self, tables, schema=None):
        if self.source_type=="redshift_psql":
            return await get_table_specs(tables,GET_TABLE_SPECS_SQL=self.GET_TABLE_SPECS_SQL,schema=schema)
        else: ##TODO: Use schema in supabase postgres for pulling get_table_specs
            return await get_table_specs(tables,GET_TABLE_SPECS_SQL=self.GET_TABLE_SPECS_SQL)

