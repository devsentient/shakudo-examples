# NLP-to-SQL Backend with Auto-Schema Detection

A FastAPI backend that converts natural language questions to SQL queries, with automatic schema detection capabilities.

## Features

### Core Features (Original)
- **Recommend Tables**: Given a schema and prompt, recommends relevant tables
- **Generate SQL**: Generates SQL queries from natural language
- **Validate & Execute**: Validates SQL syntax and executes queries

### New Features (Auto-Schema Detection)
- **Auto-Schema Detection**: Automatically identifies the relevant schema and tables based on the user's question
- **Schema-less Queries**: Users can ask questions without knowing database structure
- **Business Glossary Support**: Map business terms to technical database entities
- **Schema Caching**: Improves performance by caching database structure

## API Endpoints

### Original Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/recommendTables` | GET | Recommend tables for a given prompt and schema |
| `/generateSQL` | POST | Generate SQL query from prompt, schema, and tables |
| `/validateAndExecuteSQL` | POST | Validate and execute SQL query |

### New Auto-Detection Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/getAvailableSchemas` | GET | List all available schemas and their tables |
| `/getDatabaseStructure` | GET | Get full database structure with columns |
| `/autoDetectSchema` | POST | Auto-detect schema and tables for a question |
| `/askQuestion` | POST | Unified endpoint for schema-less queries |
| `/glossary` | GET | Get the configured business glossary |
| `/clearSchemaCache` | POST | Clear the schema cache |

## Usage

### Traditional Flow (with schema)
```python
# 1. Recommend tables
GET /recommendTables?prompt=...&schema=climate

# 2. Generate SQL (send response to LLM first)
POST /generateSQL
{"prompt": "...", "schema": "climate", "tables": {"data": "table1,table2"}}

# 3. Execute SQL
POST /validateAndExecuteSQL
{"data": "SELECT * FROM ..."}
```

### New Flow (without schema)
```python
# 1. Ask question (returns prompt for LLM to detect schema)
POST /askQuestion
{"prompt": "Give me everything John Smith donated in the last 10 years"}

# 2. Send prompt_for_llm to your LLM
# 3. Parse JSON response to get schema and tables
# 4. Continue with generateSQL and validateAndExecuteSQL
```

### Auto-Detection with Dify Workflow

The `/autoDetectSchema` and `/askQuestion` endpoints return prompts designed for LLM processing. In Dify:

1. Call `/askQuestion` with user's natural language query
2. Send the returned `prompt_for_llm` to an LLM node
3. Parse the LLM's JSON response to extract schema and tables
4. Use those values with `/generateSQL` and `/validateAndExecuteSQL`

## Business Glossary

Create a `glossary.json` file to map business terms to database entities:

```json
{
    "terms": {
        "donation": {
            "tables": ["donations", "gifts"],
            "columns": ["amount", "gift_amount"],
            "description": "Financial contributions"
        }
    },
    "table_descriptions": {
        "donations": "Records of all donations received"
    }
}
```

See `glossary.json.example` for a complete example.

Set the glossary path via environment variable:
```bash
export GLOSSARY_PATH=/path/to/glossary.json
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | nlp-sql-postgresql.hyperplane-nlp-sql-v0 |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | Database user | supabase_admin |
| `POSTGRES_DB_NAME` | Database name | postgres |
| `HYPERPLANE_CUSTOM_SECRET_KEY_POSTGRES_PSWD` | Database password | postgres |
| `SOURCE_TYPE` | Database type (supabase/redshift_psql) | supabase |
| `EXCLUDE_TABLE_NAMES` | Comma-separated tables to exclude | (empty) |
| `GLOSSARY_PATH` | Path to business glossary JSON | glossary.json |
| `DOCS_URL` | Swagger docs URL | /os-nlp-sql-dify/docs |

## Running Locally

```bash
cd backend-dify-opensource
pip install -r requirements.txt
uvicorn app_dify:app --host 0.0.0.0 --port 8000
```

## Testing

```bash
python tests/test_app.py
```

## Building with Dify

### Setup Custom Tools
1. Go to `Tools -> Create Custom Tools`
2. Paste OpenAPI Schema from `http://localhost:8000/os-nlp-sql-dify/openapi.json`
3. Fill in the in-cluster URL
4. Test the connection

### Create Agent
1. Go to `Studio -> Agent`
2. Create an Agent Chatbot
3. Add the custom tools
4. Configure LLM with temperature ~0.03 for consistency

### Workflow for Auto-Schema Detection
1. Start Node: User Input
2. HTTP Node: Call `/askQuestion` with user prompt
3. LLM Node: Process the returned prompt for schema detection
4. Code Node: Parse JSON response to extract schema/tables
5. HTTP Node: Call `/generateSQL` with extracted values
6. LLM Node: Generate SQL from the prompt
7. HTTP Node: Call `/validateAndExecuteSQL`
8. End Node: Return results
