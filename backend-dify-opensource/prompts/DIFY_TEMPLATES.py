"""This module is to define prompt templates for dify application."""

TEMPLATE_TABLE_FINDING = """
Given the list of table names and their column names in the format {{table1: [column1, column2, ...], table2: [column1, column2, ...]}}:

{table_example}

Give me the relevant tables to this prompt: "{prompt}"

Your return should be exactly in format below, nothing else:
{{"data": [table1, table2, ...]}}
"""

TEMPLATE = """
Given information about the table:
{table_info}

Give me sql query that can answer: "{prompt}"

Adding "{schema}." to any table in the query.
The format of the response in the following format: 
{{"data": 'SQL query to run'}}
Please note that the query to extract date part is 'EXTRACT(part FROM date_expression)'
Example is {{"data" : "SELECT * from project_id.loblaw.table1"}}
"""
