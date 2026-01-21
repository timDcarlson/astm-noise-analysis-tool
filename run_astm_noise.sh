#!/usr/bin/env bash
set -euo pipefail

# Launcher for ASTM Noise Analysis Tool (macOS/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting ASTM Noise Analysis Tool..."

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN=".venv/bin/python"
  echo "Using local virtual environment: $SCRIPT_DIR/.venv"
else
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  else
    echo "Error: python3/python not found. Run ./setup_env.sh first." >&2
    exit 1
  fi
  echo "Using system Python: $($PYTHON_BIN --version 2>&1)"
fi

"$PYTHON_BIN" ASTMnoise.py "$@"
