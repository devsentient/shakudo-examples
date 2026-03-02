"""
This module is to define USER prompt templates for dify application.
The system prompts are set in the workflow.
"""

TEMPLATE_TABLE_FINDING = """
Given the list of table names and their column names in the format {{table1: [column1, column2, ...], table2: [column1, column2, ...]}}:

{table_example}

Give me the relevant tables to this prompt: "{prompt}"

Your return should be exactly in format below, nothing else:
{{"data": "table_1, table_2, table_3"}}

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

TEMPLATE_SCHEMA_DETECTION = """
You are a database schema analyst. Given a user's natural language question and a database structure, identify the most relevant schema and tables to answer the question.

DATABASE STRUCTURE (format: schema_name -> table_name: [columns]):
{database_structure}

{glossary_section}

USER QUESTION: "{prompt}"

INSTRUCTIONS:
1. Analyze the user's question to understand what data they need
2. Look for tables that contain relevant columns (e.g., names, dates, amounts, IDs)
3. Consider table names and column names that semantically match the question
4. If a glossary is provided, use it to map business terms to technical table/column names
5. Select the single most appropriate schema and the relevant tables within it

Your response must be valid JSON in exactly this format:
{{"schema": "schema_name", "tables": ["table1", "table2"], "confidence": "high|medium|low", "reasoning": "brief explanation"}}

IMPORTANT:
- "schema" must be one of the schema names from the database structure above
- "tables" must be table names that exist within the selected schema
- "confidence" indicates how confident you are in the match
- If no good match exists, use confidence "low" and explain in reasoning
"""

TEMPLATE_GLOSSARY_SECTION = """
BUSINESS GLOSSARY (maps business terms to database entities):
{glossary}

Use this glossary to interpret business terms in the user's question.
"""
