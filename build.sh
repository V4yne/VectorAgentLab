#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${PYTHON:-python}"

cd "$ROOT_DIR"

if ! "$PYTHON_BIN" -c "import build" >/dev/null 2>&1; then
  echo "Missing build dependency."
  echo "Run one of these first:"
  echo "  $PYTHON_BIN -m pip install build"
  echo "  $PYTHON_BIN -m pip install -e \".[dev,web]\""
  exit 1
fi

"$PYTHON_BIN" -m build

LATEST_WHEEL="$(ls -t dist/vector_agent_lab-*.whl | head -n 1)"

echo
echo "Build finished."
echo "Wheel: $LATEST_WHEEL"
echo
echo "To test the built package in this environment:"
echo "  $PYTHON_BIN -m pip install \"$LATEST_WHEEL[web]\""
echo "  vector-agent-lab-web-start"
echo "  vector-agent-lab-web-stop"

