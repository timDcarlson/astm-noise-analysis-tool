#!/usr/bin/env bash
set -euo pipefail

# Quick setup script for ASTM Noise Analysis Tool (macOS/Linux)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Setting up ASTM Noise Analysis Tool..."
./setup_env.sh

echo
echo "Setup complete!"
echo "Start the tool with: ./run_astm_noise.sh"
