#!/bin/bash
set -e

cd "$(dirname "$0")"

python -m pip install -r requirements.txt

python -m uvicorn app:app --host 0.0.0.0 --port 8000