from langchain.prompts import PromptTemplate

TEMPLATE_TABLE_FINDING = """
<|im_start|>system
I will give you tables and their column names, return table names which are the most 
related to the prompt provided by the user.
If nothing is directly related, randomly pick some.

<|im_end|>
<|im_start|>user
Given the list of table names and their column names in the format {{table1: [column1, column2, ...], table2: [column1, column2, ...]}}:

{table_example}

Give me the relevant tables to this prompt: "{prompt}"

Your return should be exactly in format below, nothing else:
{{"data": [table1, table2, ...]}}
<|im_end|>
<|im_start|> assistant
"""
PROMPT_TABLE_FINDING = PromptTemplate(
    input_variables=["prompt", "table_example"], template=TEMPLATE_TABLE_FINDING
)

TEMPLATE = """
<|im_start|> system
You are an expert in {language}, create a syntactically correct {language} query to run
based on user questions.
<|im_end|>
<|im_start|> user
Given information about the table:
{table_info}

Give me sql query that can answer: "{prompt}"

Adding "{schema}." to any table in the query.
The format of the response in the following format: 
{{"data": 'SQL query to run'}}
Please note that the query to extract date part is 'EXTRACT(part FROM date_expression)'
Example is {{"data" : "SELECT * from project_id.loblaw.table1"}}
<|im_end|>
<|im_start|> assistant
"""

CUSTOM_PROMPT = PromptTemplate(
    input_variables=["prompt", "additional_err", "table_info", "schema", "language"],
    template=TEMPLATE,
)


ANS_TEMPLATE = """
<|im_start|> system
Given the following query and result, give an answer in one or two line of natural language sentences. If there is not enough information, say "There is not enough information".
Only answer the question, do not provide code samples.
Query:
{query}
Result:
{result}
<|im_end|>
<|im_start|> user
{prompt}<|im_end|>
<|im_start|> assistant
"""

ANS_PROMPT = PromptTemplate(
    input_variables=["prompt", "query", "result"], template=ANS_TEMPLATE
)


COLUMN_FILTER_TEMPLATE = """
<|im_start|> system
You will help the user to pick relevant columns from a SQL table based on user's prompt.
<|im_end|>
<|im_start|> user
This is the list of column names {columns}
Give me the list of column names which are relevant to this prompt: "{prompt}"
Your response should be exactly in the JSON format below, nothing else. 

{{"data": [ "column_name_1", "column_name_2, ...]}}

<|im_end|>
<|im_start|> assistant
"""


COLUMN_FILTER_TEMPLATE = """
<|im_start|> system
You will help the user to pick relevant columns from a postgressql table based on user's prompt.
<|im_end|>
<|im_start|> user
This is the list of column names {columns}
Give me the list of columns which are relevant to {prompt}
Your response should be exactly in JSON format below, status can only be 'ok' or 'error'. 
{{
    "status": "ok",
    "data": ["column_name_1", "column_name_2, ...]
}}
<|im_end|>
<|im_start|> assistant
"""

COLUMN_FILTER_PROMPT = PromptTemplate(
    template=COLUMN_FILTER_TEMPLATE, input_variables=["columns", "prompt"]
)
