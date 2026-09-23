#!/usr/bin/env bash
# Starts the local dev stack (db, api, web) described in
# docs/operations/local-development.md. Ctrl+C stops api and web;
# the db container keeps running (stop it with `docker compose down`).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_DIR="$ROOT_DIR/apps/api"
WEB_DIR="$ROOT_DIR/apps/web"
LOG_DIR="$ROOT_DIR/.dev-logs"

check_prereqs() {
  if ! docker info >/dev/null 2>&1; then
    echo "error: Docker isn't running. Start Docker Desktop and try again." >&2
    exit 1
  fi
  if [ ! -x "$API_DIR/.venv/bin/uvicorn" ]; then
    echo "error: apps/api/.venv not found. Run the one-time API setup in" >&2
    echo "       docs/operations/local-development.md first." >&2
    exit 1
  fi
  if [ ! -d "$WEB_DIR/node_modules" ]; then
    echo "error: apps/web/node_modules not found. Run 'npm install' in" >&2
    echo "       apps/web first (see docs/operations/local-development.md)." >&2
    exit 1
  fi
}

start_db() {
  echo "==> starting local Postgres"
  (cd "$ROOT_DIR" && docker compose up -d db)

  echo "==> waiting for Postgres to be healthy"
  for _ in $(seq 1 30); do
    health="$(cd "$ROOT_DIR" && docker compose ps db --format json 2>/dev/null | grep -o '"Health":"[a-z]*"' | cut -d'"' -f4 || true)"
    [ "$health" = "healthy" ] && return
    sleep 1
  done
  echo "error: db did not become healthy in time" >&2
  exit 1
}

start_api() {
  echo "==> starting api (http://localhost:8000, log: $LOG_DIR/api.log)"
  (cd "$API_DIR" && exec .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000) \
    > "$LOG_DIR/api.log" 2>&1 &
  api_pid=$!
}

start_web() {
  echo "==> starting web (http://localhost:5173, log: $LOG_DIR/web.log)"
  (cd "$WEB_DIR" && exec npm run dev) > "$LOG_DIR/web.log" 2>&1 &
  web_pid=$!
}

cleanup() {
  # Guard against running twice: the INT/TERM trap and the EXIT trap that
  # fires right after it would otherwise both print and kill.
  [ -n "${cleaned_up:-}" ] && return
  cleaned_up=1
  echo
  echo "==> stopping api and web (db keeps running; 'docker compose down' to stop it)"
  kill "$api_pid" "$web_pid" "$tail_pid" 2>/dev/null || true
  wait "$api_pid" "$web_pid" "$tail_pid" 2>/dev/null || true
}

wait_until_stopped() {
  # A polling loop, not a blocking `wait`/`tail -f`: macOS ships bash 3.2,
  # whose `wait` builtin does not get interrupted by a trapped signal until
  # the waited-for process exits. Traps ARE dispatched between simple
  # commands in every bash version, so a short sleep loop reacts to Ctrl+C
  # (or the whole process group's SIGINT) within ~1s in the worst case, and
  # immediately in the common case where the terminal signals `sleep` too.
  while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
    sleep 1
  done
}

main() {
  check_prereqs
  mkdir -p "$LOG_DIR"
  start_db
  start_api
  start_web
  trap cleanup EXIT INT TERM
  tail -f "$LOG_DIR/api.log" "$LOG_DIR/web.log" &
  tail_pid=$!
  echo "==> stack is up. Press Ctrl+C to stop api and web."
  wait_until_stopped
}

main
