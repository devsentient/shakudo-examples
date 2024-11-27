cd backend-dify-opensource/

# apt-get update -y && apt-get upgrade -y
# apt-get install -y dnsutils postgresql
pip install -r requirements.txt

# Uncomment below for local development only
export POSTGRES_HOST=supabase-metaflow-postgresql.hyperplane-supabase-metaflow
export POSTGRES_PORT=5432
export UVICORN_HOST=0.0.0.0
export UVICORN_PORT=8000
export EXCLUDE_SCHEMAS="pg_catalog"
export EXCLUDE_TABLE_NAMES="example_table_name"
export EXCLUDE_TABLE_PATTERNS=_airbyte_raw
export HYPERPLANE_CUSTOM_SECRET_KEY_POSTGRES_PSWD=ONUpIAekWk
uvicorn app_dify:app --workers 1 --port 8000 --reload
