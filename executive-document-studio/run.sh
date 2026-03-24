#!/bin/bash
set -e
cd "$(dirname "$0")"

PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"
FORCE_FRONTEND_BUILD="${FORCE_FRONTEND_BUILD:-0}"

echo "=== Executive Document Studio ==="

echo "[1] Installing Python dependencies..."
if [ ! -d "backend/.venv" ]; then
  python3 -m venv backend/.venv
fi
source backend/.venv/bin/activate
pip install -q -r backend/requirements.txt

if [ "$FORCE_FRONTEND_BUILD" = "1" ] || [ ! -d "frontend/out" ]; then
  echo "[2] Building frontend..."
  cd frontend
  if [ ! -d "node_modules" ]; then
    npm install --silent
  fi
  NEXT_PUBLIC_API_BASE_URL=/api npm run build
  cd ..
else
  echo "[2] Pre-built frontend found — skipping build"
fi

echo "[3] Starting single-service server on port ${PORT}..."
cd backend
exec uvicorn main:app --host "$HOST" --port "$PORT"
