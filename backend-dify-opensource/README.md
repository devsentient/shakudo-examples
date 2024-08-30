# Documentation

### Build endpoint as Agent

There are 3 main endpoints:

1. `Recommend_Schema`: `recommend_schema` receives and produce the most relevant schema. It only considers
   the current list a schema as input for LLM
2. `Recommend_Table`: `/recommend_table` receives schema and prompt and produce the list of relevant tables.
   it uses a list of table names and their columns as input for LLM to determine
3. `Sql_Markdown`: `/sql` receives schema, list of relevant tables and user's prompt to determine the sql query,
   run validation check, retry 3 times max if the query is syntatically incorrect and then run
   the query and return to the caller.

### Build Agent in Dify

Go to `Tools -> Create Custom Tools`. Paste OpenAPI Schema which can get from `FastAPI` application
as definition for the 3 above endpoints. For `url`, fill in the in-cluster URL. Then test the connection in Dify

### Build Chatbot in Dify

Go to `Studio -> Agent`. Create an Agent Chatbot from Scratch. In the Instruction, fill in the prompt which
mentions which agent tool will be used in a specific case.
In `Tools`, Add tools which are defined in the above step.
Note: set the temperature of LLM to 0.03 for consistency.
