from langchain.prompts import PromptTemplate

TEMPLATE_TABLE_FINDING = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
I will give you tables and their column names, return table names which are the most 
related to the prompt provided by the user.
If nothing is directly related, randomly pick some.

Your return should be exactly in format below, nothing else:
{{"data":  [{{"table": "Name of table1", "description": "Short description of table1"}},
            {{"table": "Name of table2", "description": "Short description of table2"}}]
}}

<|eot_id|>
<|start_header_id|>user<|end_header_id|>
Given the list of table names and their column names: 
{table_example}

Give me relevant tables to {prompt}
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

PROMPT_TABLE_FINDING = PromptTemplate(
    input_variables=["prompt", "table_example"], template=TEMPLATE_TABLE_FINDING
)

TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You are an expert in postgreSQL, create a syntactically correct postgreSQL query to run
based on user questions.

Adding "{schema}." to any table in the query.
The format of the response in the following format: 
{{"data": 'SQL query to run'}}

Example is {{"data" : "SELECT * from loblaw.table1"}}

<|eot_id|>
<|start_header_id|>user<|end_header_id|>
Given information about the table:
{table_info}

{prompt}
<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

ANS_TEMPLATE = """<|begin_of_text|><|start_header_id|>system<|end_header_id|>
Given the following query and result, give an answer in one or two line of natural language sentences. If there is not enough information, say "There is not enough information".
Only answer the question, do not provide code samples.
<|eot_id|>
<|start_header_id|>user<|end_header_id|>
This is sql query: {query}
And this is the corresponding sql's output {result}

Give answer to the question: {prompt}<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

CUSTOM_PROMPT = PromptTemplate(
    input_variables=["prompt", "table_info", "additional_err", "schema"],
    template=TEMPLATE,
)

ANS_PROMPT = PromptTemplate(
    input_variables=["prompt", "query", "result"], template=ANS_TEMPLATE
)


COLUMN_FILTER_TEMPLATE = """
<|begin_of_text|><|start_header_id|>system<|end_header_id|>
You will help the user to pick relevant columns from a postgressql table based on user's prompt.
<|eot_id|>
<|start_header_id|>user<|end_header_id|>
This is the list of column names {columns}
Give me the list of columns which are relevant to {prompt}
Your response should be exactly in the JSON format below, nothing else. 

{{"data": [ "column_name_1", "column_name_2, ...]}}

<|eot_id|>
<|start_header_id|>assistant<|end_header_id|>
"""

COLUMN_FILTER_PROMPT = PromptTemplate(template=COLUMN_FILTER_TEMPLATE, 
                                      input_variables=['columns', 'prompt'])