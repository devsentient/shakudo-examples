class DatabaseConnection(object):
    ##
    # 'get_schemas': get_psql_schemas,
    # 'validator': is_valid_psql_query,
    # 'exec_ret': exec_psql,
    # 'exec_silence': exec_psql_no_ret,
    # 'get_table_specs': get_table_specs,
    # 'get_tables': get_tables_psql,
    conninfo: str = ""

    def __init__(self) -> None:
        return

    def get_schema(self):
        raise NotImplementedError

    def validate_query(self, query):
        raise NotImplementedError

    def exec_query_with_ret(self, query):
        raise NotImplementedError

    def exec_query_without_ret(self, query):
        raise NotImplementedError

    def get_tables(self, schema):
        raise NotImplementedError

    def get_all_tables(self):
        raise NotImplementedError

    def get_table_specs(self, tables, schema=None):
        raise NotImplementedError

    def get_all_tables_all_schemas(self, exclude_system_schemas: bool = True):
        """
        Get all tables from all schemas in the database.
        Returns a dict: {schema_name: {table_name: [columns]}}

        Args:
            exclude_system_schemas: If True, excludes system schemas like
                                   pg_catalog, information_schema, etc.
        """
        raise NotImplementedError
