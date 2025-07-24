#!/bin/bash
set -e  # Exit immediately if any command fails

# Change to the directory where this script is located
 PROJECT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
 cd "$PROJECT_DIR"

# Install required Python dependencies
pip install -r requirements.txt

# Start the FastAPI server; use Shakudo's expected port (default 8787 or as configured)
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8787}


