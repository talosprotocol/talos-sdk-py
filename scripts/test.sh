#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# talos-sdk-py Test Script
# =============================================================================

echo "Testing talos-sdk-py..."

echo "Installing package..."
pip install -e ".[dev]" -q 2>/dev/null || pip install -e . -q

echo "Running ruff check..."
ruff check src tests 2>/dev/null || ruff check talos_sdk tests 2>/dev/null || true

echo "Running ruff format check..."
ruff format --check src tests 2>/dev/null || ruff format --check talos_sdk tests 2>/dev/null || true

echo "Running pytest..."
pytest tests/ --maxfail=1 -q

echo "talos-sdk-py tests passed."
