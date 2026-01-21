#!/usr/bin/env bash
set -euo pipefail

# Setup script for ASTM Noise Analysis Tool (macOS/Linux)
# Enforces wheel-only installs (no source builds).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up ASTM Noise Analysis environment..."

PYTHON_BIN="${PYTHON:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN=python
  else
    echo "Error: python3/python not found." >&2
    exit 1
  fi
fi

echo "Using Python: $($PYTHON_BIN --version 2>&1)"

VENV_DIR=".venv"
if [[ -d "$VENV_DIR" ]]; then
  echo "Removing existing virtual environment: $VENV_DIR"
  rm -rf "$VENV_DIR"
fi

echo "Creating virtual environment..."
"$PYTHON_BIN" -m venv "$VENV_DIR"

VENV_PY="$VENV_DIR/bin/python"
PIP="$VENV_PY -m pip"

echo "Upgrading pip..."
$PIP install --upgrade pip

echo "Installing required packages (wheels only)..."
if [[ -f "requirements.txt" ]]; then
  # Wheel-only enforcement: fail if any dependency requires building from source.
  $PIP install --only-binary=:all: -r requirements.txt
else
  echo "Warning: requirements.txt not found. Installing basic packages (wheels only)..."
  $PIP install --only-binary=:all: numpy matplotlib scipy
fi

echo
echo "Environment setup complete!"
echo "Virtual environment created at: $SCRIPT_DIR/$VENV_DIR"
echo "Run: ./run_astm_noise.sh"
