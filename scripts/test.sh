#!/usr/bin/env bash
set -eo pipefail

# =============================================================================
# Python SDK Standardized Test Entrypoint
# =============================================================================

ARTIFACTS_DIR="artifacts/coverage"
mkdir -p "$ARTIFACTS_DIR"

COMMAND=${1:-"--unit"}

pick_python() {
    local candidates=()
    if [[ -n "${TALOS_PYTHON:-}" ]]; then
        candidates+=("${TALOS_PYTHON}")
    fi
    candidates+=(python3 python3.14 python3.13 python3.12 python3.11 python3.10)

    local candidate
    for candidate in "${candidates[@]}"; do
        command -v "$candidate" >/dev/null 2>&1 || continue
        if "$candidate" - <<'PY' >/dev/null 2>&1
import sys
raise SystemExit(0 if sys.version_info >= (3, 10) else 1)
PY
        then
            echo "$candidate"
            return 0
        fi
    done

    echo "Talos Python SDK tests require Python >= 3.10. Set TALOS_PYTHON to a compatible interpreter." >&2
    exit 1
}

HOST_PYTHON="$(pick_python)"
VENV_DIR=".venv-test"
PYTHONPATH_BASE="src${PYTHONPATH:+:$PYTHONPATH}"

ensure_virtualenv() {
    if [[ ! -x "$VENV_DIR/bin/python" ]]; then
        echo "Creating local test virtualenv with $("$HOST_PYTHON" --version 2>&1)..."
        "$HOST_PYTHON" -m venv "$VENV_DIR"
    fi
}

ensure_virtualenv
PYTHON_BIN="$VENV_DIR/bin/python"

ensure_test_dependencies() {
    if PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" - <<'PY' >/dev/null 2>&1
import importlib.util

required = [
    "pytest",
    "pytest_cov",
    "cryptography",
    "fastapi",
    "httpx",
    "jsonschema",
    "pydantic",
    "requests",
    "websockets",
]
missing = [name for name in required if importlib.util.find_spec(name) is None]
raise SystemExit(0 if not missing else 1)
PY
    then
        return 0
    fi

    echo "Installing Python SDK test dependencies with $("$PYTHON_BIN" --version 2>&1)..."
    local install_args=()
    if [[ -f "../../contracts/python/pyproject.toml" ]]; then
        install_args+=(-e ../../contracts/python)
    fi
    install_args+=(-e ".[dev]")
    PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON_BIN" -m pip install "${install_args[@]}"
}

ensure_test_dependencies

run_unit() {
    echo "=== Running Unit Tests ==="
    PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" -m pytest tests/ -v --cov=talos_sdk --cov-report=xml:"$ARTIFACTS_DIR/coverage.xml"
}

run_smoke() {
    echo "=== Running Smoke Tests ==="
    PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" -m pytest tests/ -m smoke --maxfail=1 -q || run_unit
}

run_integration() {
    echo "--- Skipping Integration (Not found) ---"
}

run_coverage() {
    echo "=== Running Coverage (pytest-cov) ==="
    PYTHONPATH="$PYTHONPATH_BASE" "$PYTHON_BIN" -m pytest tests/ --cov=talos_sdk --cov-branch --cov-report=xml:"$ARTIFACTS_DIR/coverage.xml"
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
