from langchain.prompts import PromptTemplate
from langchain.prompts.chat import (ChatPromptTemplate,
                                    HumanMessagePromptTemplate,
                                    SystemMessagePromptTemplate)
from langchain_core.messages import SystemMessage

GLOBAL_SYS = """
You are a nlp to sql ai assistant. You will try to help user to generate sql code, and analysis the result.
"""
global_sys = SystemMessage(content=GLOBAL_SYS)

USR_GLOBAL = """
We will be generating {language} sql code today. make sure the code generated is {language} syntax
"""
global_user_tmp = PromptTemplate(
    template=USR_GLOBAL, input_variables=["language"]
)
global_user = HumanMessagePromptTemplate(prompt=global_user_tmp)

TEMPLATE_TABLE_SYS = """
Here are tables and their column names, 
return which table names are the most likely to be related to the prompt, 

Table name and column names:
{table_example}
if nothing is directly related, randomly pick three of them.
your return should be exactly in JSON format below, status can only be 'ok' or 'error', if error, put detail in error field:
{{  "status": "ok",
    "data": [ {{"table_name": "table1", "table_desc": "short description about table1"}},
              {{"table_name": "table2", "table_desc": "short description about table2"}}, ...]
    "error": ""
}}
"""

sys_prompt_table = PromptTemplate(
    template=TEMPLATE_TABLE_SYS, input_variables=["table_example"]
)
sys_table_message = SystemMessagePromptTemplate(prompt=sys_prompt_table)
human_table_message = HumanMessagePromptTemplate.from_template("{input}")

PROMPT_TABLE_FINDING = ChatPromptTemplate.from_messages(
    [global_sys, global_user, sys_table_message, human_table_message]
)


TEMPLATE_COLUMN_FILTER_SYS = """
Here are column names in a postgres table {schema}.{table},  
return which column names are the most likely to be related to the prompt, 

The prompt: {prompt}

Here are column names:
{columns}
if nothing is directly related, put detail in error.
your return should be exactly in JSON format below, status can only be 'ok' or 'error', if error, put detail in error field:
{{  
    "status": "ok",
    "data": [ "column_name_1", "column_name_2, ...]
    "error": ""
}}
"""

sys_prompt_col = PromptTemplate(
    template=TEMPLATE_COLUMN_FILTER_SYS,
    input_variables=["schema", "table", 'prompt', 'columns'],
)

sys_message_prompt_col = SystemMessagePromptTemplate(prompt=sys_prompt_col)
# human_message_prompt_1 = HumanMessagePromptTemplate.from_template("User prompt: {input}")


COLUMN_FILTER_PROMPT = ChatPromptTemplate.from_messages([global_sys, global_user, sys_message_prompt_col])



TEMPLATE_SQL_GEN = """Given an input question, create a syntactically correct {language} query to run. 

Remember that in a group by clause, select statements must be present in the group by as well. 
Raw query only, no extra quote.

Pay attention to this potential error message: {additional_err}

remember the table is in {schema}.
so your sql should be using *** FROM {schema}.[tablename] whenever needed.
Also whenever you joining two tables, remember to always alias the common columns to ensure uniqueness, never generate query that will resulting duplicated column names.
Only use the following table:
{table_info}

Return json in following format:
{{  "status": "ok",
    "data": "SELECT * \nFROM public.oslerdemo_deals\n", // Insert `\n` after each operation
    "error": "", 
    "suggestPrompt": ""
}}

Example when user :
{{  "status": "ok",
    "data": "", // No data generated.
    "error": "The request compeletely not related to the tables", // Reason
    "suggestPrompt": "Show me xxx of xxx." // Suggestion that is ready for user to copy
}}
Remember suggestPrompt should never contains instructions, it should be prompt example.
The user question may not directly refering the column names, you have to use the columns info to guess which columns user is referring to.
and try to generate useful sqlcode.

Question: {input}
"""

sys_prompt_1 = PromptTemplate(
    template=TEMPLATE_SQL_GEN,
    input_variables=["additional_err", "table_info", "schema", 'language'],
)

sys_message_prompt_1 = SystemMessagePromptTemplate(prompt=sys_prompt_1)


CUSTOM_PROMPT = ChatPromptTemplate.from_messages([global_sys, global_user, sys_message_prompt_1])

TEMPLATE_GQL_GEN = """Given an input question, create a syntactically correct {language} query to run. 

Raw query only, no extra quote or semicolon.
USe edges node to visit fields
Pay attention to this potential error message: {additional_err}

Only use the following table and columns:
{table_info}

Here are types in graphql to support your graphql Query:
{supply_types}

Return json in following example format:
{{  "status": "ok",
    "data": "query{{
                    someCollection(
                    {{field_name: {{ilike: "%keyword%"}}}}) 
                ) {{
                    edges{{
                        node{{
                            columns
                        }}
                    }}
                }}
                }}", // Insert `\n` after each line
    "error": "", 
    "suggestPrompt": ""
}}

Example when user :
{{  "status": "ok",
    "data": "", // No data generated.
    "error": "The request compeletely not related to the tables", // Reason
    "suggestPrompt": "Show me xxx of xxx." // Suggestion that is ready for user to copy
}}
Remember suggestPrompt should never contains instructions, it should be prompt example.
The user question may not directly refering the column names, you have to use the columns info to guess which columns user is referring to.
and try to generate useful sqlcode.

Question: {input}
"""
sys_prompt_gql = PromptTemplate(
    template=TEMPLATE_GQL_GEN,
    input_variables=["additional_err", "table_info", "schema", 'language', 'supply_types']
)

sys_message_prompt_gql = SystemMessagePromptTemplate(prompt=sys_prompt_gql)

CUSTOM_PROMPT_GQL = ChatPromptTemplate.from_messages([global_sys, global_user, sys_message_prompt_gql])


TEMPLATE_2 = """
Given the following query and SQL Output, give a one or two sentences of natural language analysis of the output. 
If there is not enough information, say "There is not enough information".
Answer the question, do not directly repeat what inside the result.
SQL excuted:
{sqlCode}
User prompt:
{query}
SQL Output:
{result}

"""

sys_prompt_2 = PromptTemplate(
    template=TEMPLATE_2, input_variables=["sqlCode", "query", "result"]
)

# SUPERBASE_TEMPLATES =\
# """
# Given the following query and result,
# construct a superbase chart config.
# Remember the superbase is connected to the database already, focus on creating connections
# Query:
# {query}
# Result:
# {result}
# Return in valid superbase chart config json format only:
# """

# SUPERBASE_PROMPT = PromptTemplate(
#     input_variables=["query", "result"],
#     template=SUPERBASE_TEMPLATES,
# )

sys_message_prompt_2 = SystemMessagePromptTemplate(prompt=sys_prompt_2)

ANS_PROMPT = ChatPromptTemplate.from_messages([global_sys, global_user, sys_message_prompt_2])
