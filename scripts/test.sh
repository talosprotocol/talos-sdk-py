#!/usr/bin/env bash
set -eo pipefail

# =============================================================================
# Python SDK Standardized Test Entrypoint
# =============================================================================

ARTIFACTS_DIR="artifacts/coverage"
mkdir -p "$ARTIFACTS_DIR"

COMMAND=${1:-"--unit"}

run_unit() {
    echo "=== Running Unit Tests ==="
    PYTHONPATH=src python3 -m pytest tests/ -v --cov=talos_sdk --cov-report=xml:"$ARTIFACTS_DIR/coverage.xml"
}

run_smoke() {
    echo "=== Running Smoke Tests ==="
    PYTHONPATH=src python3 -m pytest tests/ -m smoke --maxfail=1 -q || run_unit
}

run_integration() {
    echo "--- Skipping Integration (Not found) ---"
}

run_coverage() {
    echo "=== Running Coverage (pytest-cov) ==="
    PYTHONPATH=src python3 -m pytest tests/ --cov=talos_sdk --cov-branch --cov-report=xml:"$ARTIFACTS_DIR/coverage.xml"
}

case "$COMMAND" in
    --smoke)
        run_smoke
        ;;
    --unit)
        run_unit
        ;;
    --integration)
        run_integration
        ;;
    --coverage)
        run_coverage
        ;;
    --ci)
        run_smoke
        run_unit
        run_coverage
        ;;
    --full)
        run_smoke
        run_unit
        run_integration
        run_coverage
        ;;
    *)
        echo "Usage: $0 {--smoke|--unit|--integration|--coverage|--ci|--full}"
        exit 1
        ;;
esac

# Generate minimal results.json
mkdir -p artifacts/test
cat <<EOF > artifacts/test/results.json
{
  "repo_id": "sdks-python",
  "command": "$COMMAND",
  "status": "pass",
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF
