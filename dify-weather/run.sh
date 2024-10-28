#!/bin/bash
set -e

cd "$(dirname "$0")"

python -m pip install -r requirements.txt

fastapi run app.py --port 8000
