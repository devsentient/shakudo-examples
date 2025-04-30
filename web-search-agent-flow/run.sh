#!/bin/bash
cd $(dirname $0)

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package installer..." | tee -a process.log
    curl -LsSf https://astral.sh/uv/install.sh | sh | tee -a process.log
fi

uv init | tee -a process.log

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv | tee -a process.log
fi

# Activate virtual environment
source .venv/bin/activate | tee -a process.log

# Install dependencies using uv
echo "Installing dependencies..."
uv add -r requirements.txt | tee -a process.log

# Check if the local smolagents repo is available and install it
if [ -d "/root/gitrepos/demos/smolagents" ]; then
    echo "Found local smolagents repository, installing from local source..." | tee -a process.log
    uv pip install  -e /root/gitrepos/demos/smolagents[litellm,mcp] | tee -a process.log
else
    # Ensure smolagents is installed with all extras
    echo "Installing smolagents from PyPI..." | tee -a process.log
    uv pip install  "smolagents[litellm,mcp]==1.12.0" | tee -a process.log
fi

# Verify key packages are installed
echo "Verifying critical packages..." | tee -a process.log 
uv run python -c "import uvicorn; print(f'✅ uvicorn version: {uvicorn.__version__}')" || echo "❌ WARNING: uvicorn not properly installed!" | tee -a process.log
uv run python -c "import fastapi; print(f'✅ fastapi version: {fastapi.__version__}')" || echo "❌ WARNING: fastapi not properly installed!" | tee -a process.log
uv run python -c "import psycopg2; print(f'✅ psycopg2 version: {psycopg2.__version__}')" || echo "❌ WARNING: psycopg2 not properly installed!" | tee -a process.log
uv run python -c "import fastapi_mcp; print(f'✅ fastapi_mcp version: {fastapi_mcp.__version__}')" || echo "❌ WARNING: fastapi_mcp not properly installed!" | tee -a process.log

# Verify that smolagents.memory is importable
echo "Verifying smolagents imports..." | tee -a process.log
uv run python -c "from smolagents.memory import ActionStep; print('✅ Successfully imported smolagents.memory.ActionStep')" || echo "❌ WARNING: Failed to import smolagents.memory.ActionStep" | tee -a process.log

# Build MCP servers if needed
MCP_BUILD_SCRIPT="../../mcp-servers/build-servers.sh"
if [ -f "$MCP_BUILD_SCRIPT" ]; then
  echo "Found MCP build script: $MCP_BUILD_SCRIPT" | tee -a process.log
  echo "Building MCP servers..." | tee -a process.log
  
  # Check if pnpm is installed and install it if not available
  if ! command -v pnpm &> /dev/null; then
    echo "pnpm not found, installing it..." | tee -a process.log
    npm install -g pnpm | tee -a process.log
  fi
  
  # Try to build MCP servers, but continue even if it fails
  bash "$MCP_BUILD_SCRIPT" | tee -a process.log || echo "MCP server build failed, but continuing with service startup" | tee -a process.log
else
  echo "MCP build script not found at $MCP_BUILD_SCRIPT" | tee -a process.log
fi

# Run the FastAPI application with uvicorn
echo "Starting agent endpoint..." | tee -a process.log

# Use custom port if provided through environment variable, otherwise use default of 8000
PORT=${PORT:-8000}
echo "Using port: ${PORT}" | tee -a process.log

# Save the port to port.txt for reference
echo ${PORT} > port.txt

# Fix for BlockingIOError: [Errno 11] write could not complete without blocking
# Set PYTHONUNBUFFERED to force Python to use unbuffered output (line-buffered)
export PYTHONUNBUFFERED=1
echo "Set PYTHONUNBUFFERED=1 to avoid blocking I/O errors" | tee -a process.log

# Custom initialization code


# Create a custom log config file to suppress access logs for endpoints with X-No-Log header
cat > uvicorn_log_config.json << EOF
{
    "version": 1,
    "disable_existing_loggers": false,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": true
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": "%(levelprefix)s %(client_addr)s - \"%(request_line)s\" %(status_code)s",
            "use_colors": true
        }
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr"
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO"},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "WARNING", "propagate": false}
    }
}
EOF

# Set default LLM environment variables if they don't exist
if [ -z "${LLM_MODEL_ID}" ]; then
    echo "Setting default LLM model ID..." | tee -a process.log
    export LLM_MODEL_ID="openrouter/anthropic/claude-3.5-sonnet"
    echo "Using LLM model: ${LLM_MODEL_ID}" | tee -a process.log
else
    echo "Using provided LLM model: ${LLM_MODEL_ID}" | tee -a process.log
fi

if [ -z "${LLM_API_KEY}" ]; then
    echo "Setting API key..." | tee -a process.log
    export LLM_API_KEY=""
    if [ -z "${LLM_API_KEY}" ]; then
        echo "WARNING: No API key provided. You may need to set LLM_API_KEY manually." | tee -a process.log
    else
        echo "Using API key from configuration" | tee -a process.log
    fi
else
    echo "Using provided API key from environment" | tee -a process.log
fi

if [ -z "${USE_LITELLM}" ]; then
    echo "Setting LiteLLM usage flag..." | tee -a process.log
    export USE_LITELLM="true"
    echo "Using LiteLLM: ${USE_LITELLM}" | tee -a process.log
else
    echo "Using provided LiteLLM setting: ${USE_LITELLM}" | tee -a process.log
fi

if [ -z "${LITELLM_API_BASE}" ]; then
    echo "Setting default LiteLLM API base URL..." | tee -a process.log
    export LITELLM_API_BASE="http://litellm.hyperplane-litellm.svc.cluster.local:4000"
    echo "Using LiteLLM API base: ${LITELLM_API_BASE}" | tee -a process.log
else
    echo "Using provided LiteLLM API base: ${LITELLM_API_BASE}" | tee -a process.log
fi

if [ -z "${LLM_API_BASE}" ]; then
    echo "Setting default LLM API base URL..." | tee -a process.log
    export LLM_API_BASE="http://litellm.hyperplane-litellm.svc.cluster.local:4000"
    echo "Using LLM API base: ${LLM_API_BASE}" | tee -a process.log
else
    echo "Using provided LLM API base: ${LLM_API_BASE}" | tee -a process.log
fi

if [ -z "${LLM_HTTP_REFERER}" ]; then
    echo "Setting default LLM HTTP Referer..." | tee -a process.log
    export LLM_HTTP_REFERER="http://localhost:8787"
    echo "Using LLM HTTP Referer: ${LLM_HTTP_REFERER}" | tee -a process.log
else
    echo "Using provided LLM HTTP Referer: ${LLM_HTTP_REFERER}" | tee -a process.log
fi

if [ -z "${LLM_X_TITLE}" ]; then
    echo "Setting default LLM X-Title..." | tee -a process.log
    export LLM_X_TITLE="Agent Flow Service"
    echo "Using LLM X-Title: ${LLM_X_TITLE}" | tee -a process.log
else
    echo "Using provided LLM X-Title: ${LLM_X_TITLE}" | tee -a process.log
fi

# Set FastAPI MCP base URL if it doesn't exist
if [ -z "${FASTAPI_MCP_BASE_URL}" ]; then
    echo "Setting default FastAPI MCP base URL..." | tee -a process.log
    # Use external URL if provided, otherwise construct from HOST and PORT
    HOST=${HOST:-"0.0.0.0"}
    if [ "${HOST}" == "0.0.0.0" ]; then
        # For local development, use localhost instead of 0.0.0.0
        HOST="localhost"
    fi
    export FASTAPI_MCP_BASE_URL="http://${HOST}:${PORT}"
    echo "Using FastAPI MCP base URL: ${FASTAPI_MCP_BASE_URL}" | tee -a process.log
else
    echo "Using provided FastAPI MCP base URL: ${FASTAPI_MCP_BASE_URL}" | tee -a process.log
fi

# Set PostgreSQL connection environment variable if it doesn't exist
if [ -z "${PG_CONNECTION_STRING}" ]; then
    echo "No PG_CONNECTION_STRING detected, setting default PostgreSQL connection string for Agent Flow App..." | tee -a process.log
    
    # This should exactly match the connection string used in app/lib/db.ts
    export PG_CONNECTION_STRING="postgresql://supabase_admin:ONUpIAekWk@supabase-metaflow-postgresql.hyperplane-supabase-metaflow.svc.cluster.local:5432/postgres"
    
    echo "Using database connection: ${PG_CONNECTION_STRING}" | tee -a process.log
else
    echo "Using provided PG_CONNECTION_STRING environment variable" | tee -a process.log
    # Truncate for safety in logs (don't reveal password)
    PG_CONNECTION_STRING_SAFE=$(echo "$PG_CONNECTION_STRING" | sed 's/\/\/\([^:]*\):[^@]*@/\/\/\1:***@/g')
    echo "Connection string (sanitized): ${PG_CONNECTION_STRING_SAFE}" | tee -a process.log
fi

# Ensure database tables are created
echo "Testing database connection and creating tables if needed..." | tee -a process.log
curl -X POST "http://localhost:3000/api/db-init" || echo "Warning: Could not initialize database tables. They might already exist or the API is not accessible." | tee -a process.log

# Ensure the API URL is properly formatted to prevent URL parsing errors
if [ ! -z "${LITELLM_API_BASE}" ]; then
  # Remove trailing slashes
  LITELLM_API_BASE=$(echo "${LITELLM_API_BASE}" | sed 's/\/$//')
  
  # Ensure port number is properly separated from endpoint path
  # This fixes "Invalid port" errors by ensuring proper URL format
  if [[ "$LITELLM_API_BASE" =~ :[0-9]+: ]]; then
    LITELLM_API_BASE=$(echo "${LITELLM_API_BASE}" | sed 's/:\([0-9]\+\):/:\1\//')
    echo "Fixed port formatting in LITELLM_API_BASE: ${LITELLM_API_BASE}" | tee -a process.log
  fi
  
  echo "Using LITELLM_API_BASE: ${LITELLM_API_BASE}" | tee -a process.log
fi

# Set the default log level (lowercase for uvicorn)
LOG_LEVEL=${LOGLEVEL:-INFO}
LOG_LEVEL_LOWER=$(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')
echo "Using log level: ${LOG_LEVEL_LOWER}" | tee -a process.log

# Set up more verbose logging for troubleshooting MCP
echo "Starting uvicorn server with logging level ${LOG_LEVEL_LOWER}..." | tee -a process.log



# Use Python from the activated venv
PYTHONUNBUFFERED=1 \
PG_CONNECTION_STRING="${PG_CONNECTION_STRING}" \
LLM_MODEL_ID="${LLM_MODEL_ID}" \
LLM_API_BASE="${LLM_API_BASE}" \
LITELLM_API_BASE="${LITELLM_API_BASE}" \
USE_LITELLM="${USE_LITELLM}" \
LLM_HTTP_REFERER="${LLM_HTTP_REFERER}" \
LLM_X_TITLE="${LLM_X_TITLE}" \
LLM_API_KEY="${LLM_API_KEY}" \
FASTAPI_MCP_BASE_URL="${FASTAPI_MCP_BASE_URL}" \

uv run python -m uvicorn main:app --host 0.0.0.0 --port ${PORT} --log-level ${LOG_LEVEL_LOWER} --log-config uvicorn_log_config.json --no-use-colors --loop asyncio --reload 2>&1 | tee -a process.log