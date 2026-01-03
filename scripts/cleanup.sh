#!/usr/bin/env bash
set -euo pipefail

# talos-sdk-py cleanup script
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "Cleaning talos-sdk-py..."
cd "$REPO_DIR"

rm -rf *.egg-info build dist
rm -rf .venv venv
rm -rf .pytest_cache .ruff_cache
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

echo "✓ talos-sdk-py cleaned"
