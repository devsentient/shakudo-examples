#!/usr/bin/env bash
PROJECT_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

pip install fastapi uvicorn "fastapi[all]"
uvicorn main:app --host 0.0.0.0 --port 8787