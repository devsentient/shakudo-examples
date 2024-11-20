import json
import os

from google.cloud import bigquery

from connections.base import DatabaseConnection

MAX_DB_RET = 60

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/root/dev-shakudo/bigquery.json'

TABLE_PULLING_SQL = """
SELECT 
 table_name, column_name from `{0}.INFORMATION_SCHEMA.COLUMNS`
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


def is_valid_query(query):
    client = None
    try: 
        client = bigquery.Client()
        _ = client.query(query, job_config=bigquery.QueryJobConfig(dry_run=True))
        return True
    except Exception:
        return False
    finally:
        if client:
            client.close()

def get_schemas():
    schemas = []
    client = bigquery.Client() 
    for db in client.list_datasets():
        schemas.append(db.dataset_id)
    client.close()
    return schemas


def exec_sql(sqlCode: str):
    err = True
    client = None
    try:
        client = bigquery.Client() 
        fetched = client.query_and_wait(sqlCode)
        err = False
        limited = []

        for row in fetched:
            limited.append({k: row[k] for k in list(row.keys())[:MAX_DB_RET]})
        ret = json.dumps(limited, default=str)
    except Exception as e:
        ret = json.dumps({'error': f"Error {e}"}) 
    finally:
        if client:
            client.close()
    return {
        'status': 'error' if err else 'ok',
        'message': 'Failed, retry if possible' if err else 
            "Data found and returned",
        "context": ret
    }

def exec_sql_no_ret(sqlCode: str):
    client = None
    err = True

    try:
        client = bigquery.Client()
        _ = client.query_and_wait(sqlCode)
        ret = json.dumps({'ok':'executed'}, default=str)
        err = False

    except Exception as e:
        ret = json.dumps({'error': f'Error: {e}'})
    finally:
        if client:
            client.close()
    return {
        'status': 'error' if err else 'ok',
        'message': 'Executed',
        'context': ret
    }

def get_table_specs(tables, db_name):
    table_spec = {}

    client = bigquery.Client()
    
    for t in tables:
        results = client.query_and_wait(
            f"select column_name, data_type from {db_name}.INFORMATION_SCHEMA.COLUMNS where table_name = '{t}';")
        table_spec[t] = [(r['column_name'], r['data_type']) for r in results]
    client.close()

    return table_spec, None


def get_tables(db_name):
    client = bigquery.Client()

    tables = client.query_and_wait(TABLE_PULLING_SQL.format(db_name))
    parsed = tables_parse(tables)
    client.close()

    return parsed


class BigQuerySQLConnection(DatabaseConnection):
    conninfo = 'bigquery'

    def get_schema(self):                    
        return get_schemas()            
                                                   
    def validate_query(self, query):         
        return is_valid_query(query)    
                                                   
    def exec_query_with_ret(self, query):    
        return exec_sql(query)              
                                                   
    def exec_query_without_ret(self, query): 
        return exec_sql_no_ret(query)       
                                                   
    def get_tables(self, schema):            
        return get_tables(schema)       

    def get_table_specs(self, tables, db_name):
        return get_table_specs(tables, db_name)
