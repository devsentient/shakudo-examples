#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT_DIR/.run"
PROJECT_FRONTEND_DIR="$ROOT_DIR/frontend"

kill_project_next_server() {
  while read -r pid; do
    [ -n "$pid" ] || continue
    cwd="$(readlink -f "/proc/$pid/cwd" 2>/dev/null || true)"
    exe="$(readlink -f "/proc/$pid/exe" 2>/dev/null || true)"
    if [[ "$cwd" == "$PROJECT_FRONTEND_DIR"* ]] || [[ "$cwd" == "$PROJECT_FRONTEND_DIR/.next/standalone"* ]] || [[ "$exe" == *node* ]]; then
      cmdline="$(tr '\0' ' ' </proc/$pid/cmdline 2>/dev/null || true)"
      if [[ "$cmdline" == *"next-server"* ]] || [[ "$cmdline" == *"frontend/.next/standalone"* ]]; then
        kill "$pid" >/dev/null 2>&1 || true
        echo "[studio] stopped stale frontend process (pid $pid)"
      fi
    fi
  done < <(ps -eo pid=,comm= | awk '$2=="next-server"{print $1}')
}

if [ -f "$RUN_DIR/single-service.pid" ]; then
  pid="$(cat "$RUN_DIR/single-service.pid")"
  if kill -0 "$pid" >/dev/null 2>&1; then
    kill "$pid" >/dev/null 2>&1 || true
    echo "[studio] stopped single-service app (pid $pid)"
  fi
  rm -f "$RUN_DIR/single-service.pid"
fi

pkill -f "$ROOT_DIR/backend/.venv/bin/uvicorn main:app" >/dev/null 2>&1 || true
pkill -f "$ROOT_DIR/./run.sh" >/dev/null 2>&1 || true
kill_project_next_server
