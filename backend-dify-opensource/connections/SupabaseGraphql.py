import json
import os

"""query GetTables{
    shakudo_central_tasksCollection(first:1){
        edges{
            # __typename
            node{
            id
            details
            }
        }
    }
    }
    

Returns:
    _type_: _description_
"""
import requests

from connections.base import DatabaseConnection

SUPABASE_KEY = os.environ.get('YOUR_SUPABASE_KEY', None)
SUPABASE_GRAPHQL_ENDPOINT = os.environ.get('SUPABASE_GRAPHQL_ENDPOINT', 'http://supabase-metaflow-kong.hyperplane-supabase-metaflow.svc.cluster.local:80/graphql/v1')
SUPABASE_KEY = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE4MzQ3MDA0MDAsImlhdCI6MTY3NjkzNDAwMCwiaXNzIjoic3VwYWJhc2UiLCJyb2xlIjoiYW5vbiJ9.L5wyKsVw1lSYIlwMJYDC-7bfDmsBOf0Xwq1hU4QMbnA'

def graphql_request(query, variables=None):
    # async with aiohttp.ClientSession() as session:
    # return 
    response = requests.post(
        
        SUPABASE_GRAPHQL_ENDPOINT,
        json={'query': query, 'variables': variables},
        headers={'Content-Type': 'application/json',
                 'apiKey': SUPABASE_KEY}
    ) 
    print(response.content)
    return response.json()

# Validates a GraphQL query (placeholder function)
async def is_valid_graphql_query(query):
    test_query = f"""
    {query}
    """
    response = graphql_request(test_query)
    return 'errors' not in response

# Fetches all GraphQL schemas
async def get_graphql_schemas():
    query = """
    query GetSchemas {
        __schema {
            types {
                name
            }
        }
    }
    """
    response = graphql_request(query)
    if 'data' in response and '__schema' in response['data']:
        schemas = [type['name'] for type in response['data']['__schema']['types']]
        return schemas
    return []

# Executes a GraphQL query and returns data
async def exec_graphql_with_return(query, variables=None):
    err = ''
    try:
        response = graphql_request(query, variables)
        data = [response['data']]
    except Exception as e:
        err = str(e)
    if not data:
        data = []
    res = {
        "status": "error" if err else "ok",
        "message": "Data founded and returned"
        if not err and data
        else "Failed, retry if possible.",
        "context": json.dumps(data)
    }
    return res

# Executes a GraphQL mutation without expecting a return
async def exec_graphql_silently(mutation, variables=None):
    response = graphql_request(mutation, variables)
    return 'errors' not in response

# Retrieves table specifications using GraphQL
async def get_graphql_table_specs(tables):
    responses = {}
    query = """
    query IntrospectionQuery {
    __schema {
        types {
        name
        inputFields{
            name
            type{
            name
            }
        }
        }
    }
    }
    """
    response = graphql_request(query)
    res = {}
    for table in tables:
        table_name = table + 'InsertInput'
        filters_name = table + 'Filter'
        for item in response['data']['__schema']['types']:
            if item['name'] == table_name:
                print(item['inputFields'])
                res[table]['column'] = [(x['name'], x['type']['name']) for x in item['inputFields']]
            if item['name'] == filters_name:
                print(item)
                res[table]['filters'] = [(x['name'], x['type']['name']) for x in item['inputFields']]
    return res

async def get_graphql_table_specs_v2(tables):
    query = """
    
    query IntrospectionQuery {
      __schema {
        types {
          ...FullType
        }
      }
    }

    fragment FullType on __Type {
      kind
      name
      fields(includeDeprecated: true) {
        name
        args {
          ...InputValue
        }
        type {
          ...TypeRef
        }
      }
      inputFields {
        ...InputValue
      }
        enumValues(includeDeprecated: false) {
        name
      }

    }

    fragment InputValue on __InputValue {
      name
      type { ...TypeRef }
    }

    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
    """
    response = graphql_request(query)
    res = {}
    res_supply = {}
    data = response['data']['__schema']['types']
    for table in tables:
        for item in data:
            if item['name'] == 'Query':
                item = recursive_clean_up(item)
                table_rep = [x for x in item['fields'] if table in x['name']] # For the table query
        supply_type = supply_types(table_rep, data)
        res[table] = table_rep
        res_supply[table] = supply_type
    res = recursive_clean_up(res)
    res_supply = recursive_clean_up(res_supply)
    print(res, res_supply)
        # for item in data:
        #     if table in item['name'] and item['name'] in str_rep:
        #         supplies = recursive_clean_up(item)
        #         supplies_rep = json.dumps(recursive_clean_up(item))
        # pprint(
        #     {
        #         "table": table_rep,
        #         "types": supplies
        #     }
        # )
    return res, res_supply

def supply_types(x, data):
    res = {}
    for arg in x[0]['args']:
        res = recursive_search( arg['type'], data, res)
    return res

    
def recursive_search(keyitem, data, res, recursive=-1, keep_last=False):
    x_item = keyitem
    while 'ofType' in keyitem:
        keyitem = keyitem['ofType']
    if keyitem.get('name', None) in res or x_item.get('name', None) in res :
        return res
    if keyitem.get('kind', None) == 'SCALAR':
        res[keyitem.get('name')] = 'SCALAR'
        return res
    if keyitem.get('kind', None) in ['INTERFACE']:
        return res
    if recursive == 0:
        return res
    if keyitem.get('kind', None) in ['INPUT_OBJECT', 'ENUM', 'OBJECT']:
        for item in data:
            if 'kind' in item and 'name' in item and\
                item['kind'] == keyitem['kind'] and\
                    item['name'] == keyitem['name']:
                # This is another type. Now recursive on fields and inputFields
                item = recursive_clean_up(item)
                res[keyitem['name']] = item
                for sub_type in item.get('inputFields', []) + item.get('fields', []):
                    res.update(recursive_search(sub_type['type'], data, res, recursive-1))
        return res
    elif keyitem.get('name', None):
        res.update(recursive_search(keyitem, data, res, recursive-1))
    # else:
    #     res.update(recursive_search(keyitem['ofType'], data, res, recursive-1))
    return res

def recursive_clean_up(x):
    if isinstance(x, list):
        new_l = []
        for xa in x:
            new_l.append(recursive_clean_up(xa))
        x[:] = new_l
    if isinstance(x, dict):
        del_k = []
        for k, v in x.items():
            if not v:
                del_k.append(k)
            else:
                x[k] = recursive_clean_up(x[k])
        for k in del_k:
            del x[k]
    return x

# Fetches tables from a specific schema using GraphQL
async def get_graphql_tables(schema):
    query = """

    query IntrospectionQuery {
      __schema {
        queryType { name }
        types {
          ...FullType
        }
      }
    }

    fragment FullType on __Type {
      kind
      name
      description
      
      fields(includeDeprecated: false) {
        name
        type {
          ...TypeRef
        }
      }
    }

    fragment TypeRef on __Type {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
                ofType {
                  kind
                  name
                  ofType {
                    kind
                    name
                    ofType {
                      kind
                      name
                      ofType {
                        kind
                        name
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  
    """
    response = graphql_request(query)
    res = {}
    res_supply = {}
    data = response['data']['__schema']['types']
    if response.get('data', None):
        for item in response['data']['__schema']['types']:
            if item['name'] == 'Query':
                item = recursive_clean_up(item)
                tables = [x for x in item['fields']] # For the table query
        for tbl in tables:
            table_rep = tbl
            r = {}
            supply_type = recursive_search(tbl['type'], data, r,4)
            rm = []
            for t in supply_type:
                if t.endswith('Edge') or t.endswith('Collection') \
                    or t.endswith('Connection') or supply_type[t] == 'SCALAR':
                    rm.append(t)
            rm.append('PageInfo')
            for k in rm: 
                if k in supply_type :
                    del supply_type[k]
            res[tbl['name']]= {
                'table': table_rep,
                'columns': supply_type
            }
            print(res[tbl['name']])
    res = recursive_clean_up(res)
    # res_supply = recursive_clean_up(res_supply)
    # print(res_supply)
    return res, res_supply

class GraphqlConnection(DatabaseConnection):
    def get_schema(self):
        return get_graphql_schemas()
    
    async def validate_query(self, query):
        return await is_valid_graphql_query(query)
    
    async def exec_query_with_ret(self, query):
        return await exec_graphql_with_return(query)

    async def exec_query_without_ret(self, query):
        return await exec_graphql_silently(query)
    
    async def get_tables(self, schema):
        return await get_graphql_tables(schema)
    
    async def get_table_specs(self, tables):
        return await get_graphql_table_specs_v2(tables)
