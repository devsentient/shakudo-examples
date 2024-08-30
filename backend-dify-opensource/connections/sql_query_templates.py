import os
import os

import os

def get_sql_templates(source_type: str="supabase"):
    """
    Common sql templates used in queries
    """
    dbname = os.environ.get("POSTGRES_DB_NAME", "postgres")
    
    if source_type == "redshift_psql":

        ## %_pkey% is internal tables created by redshift
        # SVV_ALL_COLUMNS to view a union of columns from Amazon Redshift tables 
        # https://docs.aws.amazon.com/redshift/latest/dg/r_SVV_ALL_COLUMNS.html 
        TABLE_PULLING_SQL = f"""
        SELECT 
            table_name, 
            column_name 
        FROM 
            svv_all_columns
        WHERE 
            database_name = '{dbname}'
            AND schema_name = '{{0}}'
            AND table_name NOT LIKE '%_pkey%'
        ORDER BY 
            table_name;
        """
        
        GET_SCHEMA_SQL = """
        SELECT nspname AS schema_name FROM pg_namespace;
        """
        GET_TABLE_SPECS_SQL = f"""
        SELECT 
            column_name, 
            data_type 
        FROM 
            svv_all_columns
        WHERE 
            database_name = '{dbname}'
            AND schema_name = '{{0}}'
            AND table_name = %s
        ORDER BY 
            column_name;
        """
    else:
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
            AND t.table_type = 'BASE TABLE'
        ORDER BY 
            c.table_name, 
            c.ordinal_position;
        """
        GET_SCHEMA_SQL = """
        SELECT schema_name FROM information_schema.schemata;
        """
        GET_TABLE_SPECS_SQL = """
        select column_name, data_type from INFORMATION_SCHEMA.COLUMNS where table_name = %s
        """
    return TABLE_PULLING_SQL, GET_SCHEMA_SQL, GET_TABLE_SPECS_SQL
