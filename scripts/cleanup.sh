#!/bin/bash
set -euo pipefail

echo "Cleaning up..."
rm -rf *.egg-info build dist .venv venv .pytest_cache .ruff_cache conformance.xml
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
