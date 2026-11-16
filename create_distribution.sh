#!/usr/bin/env bash
set -euo pipefail

# ASTM Noise Analysis Tool - Distribution Creator (macOS/Linux)
# Creates a clean zip distribution similar to create_distribution.ps1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VERSION="3.2.1"
SKIP_TESTS=0

usage() {
  cat <<EOF
Usage: ./create_distribution.sh [--version X.Y.Z] [--skip-tests]

Creates: ASTM-Noise-Analysis-Tool-vX.Y.Z.zip
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -v|--version)
      VERSION="${2:-}"; shift 2 ;;
    --skip-tests)
      SKIP_TESTS=1; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown arg: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$VERSION" ]]; then
  echo "Error: --version requires a value" >&2
  exit 2
fi

PACKAGE_NAME="ASTM-Noise-Analysis-Tool-v${VERSION}"
ZIP_NAME="${PACKAGE_NAME}.zip"

# Prefer ditto on macOS for nicer zip metadata
zip_dir() {
  local src_dir="$1"
  local out_zip="$2"

  if command -v ditto >/dev/null 2>&1; then
    rm -f "$out_zip"
    ditto -c -k --sequesterRsrc --keepParent "$src_dir" "$out_zip"
  else
    rm -f "$out_zip"
    (cd "$(dirname "$src_dir")" && zip -r -q "$out_zip" "$(basename "$src_dir")")
  fi
}

FILES_TO_INCLUDE=(
  "ASTMnoise.py"
  "data_processor.py"
  "gui_components.py"
  "gui_plots.py"
  "convexHull.py"
  "config.py"
  "utils.py"
  "__init__.py"
  "requirements.txt"
  "setup_env.bat"
  "setup_env.ps1"
  "run_astm_noise.bat"
  "run_astm_noise.ps1"
  "INSTALL.bat"
  "README.md"
  "HELP.md"
  "DISTRIBUTION.md"
  "CHANGELOG.md"
  "PACKAGE_CHECKLIST.md"
  "create_distribution.bat"
  "create_distribution.ps1"
  "create_distribution.sh"
  "setup_env.sh"
  "run_astm_noise.sh"
  "INSTALL.sh"
)

echo "ASTM Noise Analysis Tool - Distribution Creator"
echo "==============================================="
echo "Creating distribution package v${VERSION}..."
echo

TMP_ROOT="$(mktemp -d)"
PKG_DIR="${TMP_ROOT}/${PACKAGE_NAME}"
mkdir -p "$PKG_DIR"

COPIED=0
MISSING=()

echo "Copying files..."
for f in "${FILES_TO_INCLUDE[@]}"; do
  if [[ -e "$f" ]]; then
    cp -R "$f" "$PKG_DIR/"
    COPIED=$((COPIED+1))
  else
    MISSING+=("$f")
  fi
done

echo "Copied ${COPIED}/${#FILES_TO_INCLUDE[@]} files"
if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "Missing files (skipped):"
  for m in "${MISSING[@]}"; do
    echo "  - $m"
  done
fi

# Clean development artifacts
find "$PKG_DIR" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$PKG_DIR" -name "*.pyc" -type f -delete 2>/dev/null || true
find "$PKG_DIR" -name "*.log" -type f -delete 2>/dev/null || true
find "$PKG_DIR" -name ".DS_Store" -type f -delete 2>/dev/null || true

# Basic import test (optional)
if [[ "$SKIP_TESTS" -eq 0 ]]; then
  PYTHON_BIN=""
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  fi

  if [[ -n "$PYTHON_BIN" ]]; then
    echo
    echo "Running basic validation test (imports)..."
    "$PYTHON_BIN" - <<PY
import sys
sys.path.insert(0, r"$PKG_DIR")
import ASTMnoise
import convexHull
print("Success: Import test passed")
PY
  else
    echo "Skipping tests: python/python3 not found"
  fi
fi

echo
echo "Creating ZIP archive: ${ZIP_NAME}"
zip_dir "$PKG_DIR" "$SCRIPT_DIR/$ZIP_NAME"

# Cleanup
rm -rf "$TMP_ROOT"

BYTES=$(python3 - <<PY 2>/dev/null || true
import os
p=r"$SCRIPT_DIR/$ZIP_NAME"
print(os.path.getsize(p) if os.path.exists(p) else "")
PY
)

if [[ -n "$BYTES" ]]; then
  MB=$(python3 - <<PY
b=$BYTES
print(round(b/1024/1024, 2))
PY
)
  echo "Created: $ZIP_NAME (${MB} MB)"
else
  echo "Created: $ZIP_NAME"
fi

echo
echo "Package creation complete!"
