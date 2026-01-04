# talos-sdk-py Makefile
# Python SDK for Talos Protocol

.PHONY: install build test lint clean start stop

# Default target
all: install test

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -e ".[dev]" -q 2>/dev/null || pip install -e . -q

# Build (Python doesn't require build step)
build:
	@echo "Python SDK - no build step required"

# Run tests
test:
	@echo "Running tests..."
	pytest tests/ -q

# Lint check
lint:
	@echo "Running lint..."
	ruff check . --exclude=.venv
	ruff format --check . --exclude=.venv

# Clean all generated files and dependencies
clean:
	@echo "Cleaning..."
	rm -rf *.egg-info
	rm -rf build dist
	rm -rf .venv venv
	rm -rf .pytest_cache .ruff_cache
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete. Ready for fresh build."

# Conformance test
conformance:
	@echo "Running conformance tests..."
	talos-sdk conformance run --vectors ../talos-contracts/test_vectors/sdk/release_sets/v1.0.0.json --report conformance.xml

# Doctor check
doctor:
	@echo "Checking environment..."
	@python3 --version || echo "Python3 missing"
	@pip --version || echo "Pip missing"
	@[ -d ".venv" ] && echo "Virtualenv detected" || echo "No virtualenv detected"

# Scripts wrapper
start:
	@./scripts/start.sh

stop:
	@./scripts/stop.sh
