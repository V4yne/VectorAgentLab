#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.vector_agent_lab_web.pid"
LOG_FILE="$ROOT_DIR/vector_agent_lab_web.log"
HOST="${VECTOR_AGENT_LAB_WEB_HOST:-127.0.0.1}"
PORT="${VECTOR_AGENT_LAB_WEB_PORT:-8000}"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT_DIR"

if ! "$PYTHON_BIN" -c "import fastapi, uvicorn" >/dev/null 2>&1; then
  echo "Missing web dependencies."
  echo "Run: $PYTHON_BIN -m pip install -e \".[web]\""
  exit 1
fi

"$PYTHON_BIN" -m vector_agent_lab.web.cli start \
  --host "$HOST" \
  --port "$PORT" \
  --pid-file "$PID_FILE" \
  --log-file "$LOG_FILE"
