import json
import os
import traceback as tb

from connections.base import DatabaseConnection
from sqlalchemy import create_engine, text
from sqlalchemy.exc import (DatabaseError, DataError, OperationalError,
                            ProgrammingError)

hostname = os.environ.get(
    "DATABRICKS_HOSTNAME", "adb-8210930792410875.15.azuredatabricks.net"
)
dbname = os.environ.get("DATABRICKS_DB_NAME", "samples")
http_path = os.environ.get(
    "DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/6b88d354f9bb1c51"
)

token = None

conninfo = f"databricks://token:{token}@{hostname}?" \
    + f"http_path={http_path}&catalog={dbname}"


engine = create_engine(conninfo)

MAX_DB_RET = 60
TABLE_PULLING_SQL = """
SELECT 
    c.table_name, 
    c.column_name
FROM 
    information_schema.columns c
JOIN 
    information_schema.tables t ON c.table_schema = t.table_schema AND c.table_name = t.table_name
WHERE 
    c.table_schema = '{0}'
    AND t.table_type = 'MANAGED'
ORDER BY 
    c.table_name, 
    c.ordinal_position;
"""

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

def is_valid_sql_query(query):
    conn = None
    try:
        with engine.connect() as conn:
            conn.execute(text("EXPLAIN " + query))
            conn.commit()
            return True
    except Exception:
        print(f"SQL Error: {tb.format_exc()}")
    finally:
        if conn:
            conn.close()


def get_databrick_schemas():
    with engine.connect() as conn:
        fetched = (
            conn.execute(text("select schema_name from information_schema.schemata"))
            .mappings()
            .fetchmany(500)
        )
        conn.commit()
        keys = list(fetched[0].keys()) if len(fetched) > 0 else []
        keeping = keys[:]
        limited = [{k: f[k] for k in keeping} for f in fetched]
        limited = [x["schema_name"] for x in limited]
    return limited


def get_table_specs(tables):
    with engine.connect() as conn:
        table_spec = {}
        for t in tables:
            fetched = (
                conn.execute(
                    text(
                        f"select column_name, data_type from INFORMATION_SCHEMA.COLUMNS where table_name = '{t}';"
                    )
                )
                .mappings()
                .fetchall()
            )
            table_spec[t] = [(d["column_name"], d["data_type"]) for d in fetched]
            conn.commit()
    return table_spec, None


def exec_sql_no_ret(sqlCode: str):
    err = True
    conn = None

    try:
        with engine.connect() as conn:
            conn.execute(text(sqlCode))
            conn.commit()
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
            conn.close()
    return {
        "status": "error" if err else "ok",
        "message": "Data founded and returned"
        if not err
        else "Failed, retry if possible.",
        "context": ret,
    }


def exec_sql(sqlCode: str):
    err = True
    conn = None

    try:
        with engine.connect() as conn:
            try:
                fetched = conn.execute(text(sqlCode)).mappings().fetchmany(MAX_DB_RET)
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
    except SyntaxError as se:
        ret = json.dumps({"error": f"Syntax error: {se}"})
    except Exception as e:
        ret = json.dumps({"error": f"General error: {e}"})
    finally:
        if conn:
            conn.close()
    return {
        "status": "error" if err else "ok",
        "message": "Data found and returned"
        if not err
        else "Failed, retry if possible",
        "context": ret,
    }


def get_tables(schema):
    conn = None
    try:
        with engine.connect() as conn:
            tables = (
                conn.execute(text(TABLE_PULLING_SQL.format(schema)))
                .mappings()
                .fetchall()
            )
            parsed = tables_parse(tables)
    except Exception as e:
        raise e
    finally:
        if conn:
            conn.close()
    return parsed


class DatabricksSQLConnection(DatabaseConnection):
    conninfo: str = conninfo

    def get_schema(self):
        return get_databrick_schemas()

    def validate_query(self, query):
        return is_valid_sql_query(query)

    def exec_query_with_ret(self, query):
        return exec_sql(query)

    def exec_query_without_ret(self, query):
        return exec_sql_no_ret(query)

    def get_tables(self, schema):
        return get_tables(schema)

    def get_table_specs(self, tables):
        return get_table_specs(tables)
