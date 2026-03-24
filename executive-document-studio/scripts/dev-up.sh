#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PORT="${PORT:-3000}"
HOST="${HOST:-0.0.0.0}"
FORCE_FRONTEND_BUILD="${FORCE_FRONTEND_BUILD:-0}"

mkdir -p "$RUN_DIR"
"$ROOT_DIR/scripts/dev-down.sh" >/dev/null 2>&1 || true

nohup bash -lc "cd '$ROOT_DIR' && HOST='$HOST' PORT='$PORT' FORCE_FRONTEND_BUILD='$FORCE_FRONTEND_BUILD' exec ./run.sh" \
  >"$RUN_DIR/single-service.log" 2>&1 < /dev/null &
echo $! > "$RUN_DIR/single-service.pid"

for _ in $(seq 1 90); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1 && curl -fsS "http://127.0.0.1:${PORT}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null
curl -fsS "http://127.0.0.1:${PORT}" >/dev/null

echo "[studio] app ready -> http://127.0.0.1:${PORT}"
echo "[studio] logs -> $RUN_DIR/single-service.log"
