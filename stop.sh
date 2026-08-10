#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.vector_agent_lab_web.pid"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT_DIR"

"$PYTHON_BIN" -m vector_agent_lab.web.cli stop --pid-file "$PID_FILE"
