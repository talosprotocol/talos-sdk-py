#!/bin/bash
set -e

COMMAND=${1:-unit}

case "$COMMAND" in
  unit)
    echo "=== Running Unit Tests ==="
    # Run unit tests only
    pytest tests/ -q
    ;;
  interop)
    echo "=== Running Vector Compliance (Conformance) ==="
    make conformance
    ;;
  lint)
    echo "=== Running Lint ==="
    # ruff check src tests 2>/dev/null || ruff check talos_sdk tests 2>/dev/null || true
    make lint
    ;;
  typecheck)
    echo "=== Running Typecheck ==="
    make typecheck
    ;;
  *)
    echo "Error: Unknown command '$COMMAND'"
    exit 1
    ;;
esac
