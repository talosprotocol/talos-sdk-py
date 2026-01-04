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
	# Style + Types (Fail on error)
	ruff check .
	mypy src tests

format:
	# Auto-fix style
	ruff format .
	ruff check --fix .

test:
	# Unit tests (Must include happy paths)
	pytest tests

conformance:
	# Run conformance vectors
	# Usage: make conformance RELEASE_SET=v1.1.0/common.json
	@if [ -z "$(RELEASE_SET)" ]; then \
		echo "Usage: make conformance RELEASE_SET=<path>"; \
		exit 0; \
	fi
	talos-sdk --vectors ../talos-contracts/test_vectors/sdk/release_sets/$(RELEASE_SET) --report conformance.xml

build:
	python -m build

clean:
	rm -rf dist build *.egg-info .pytest_cache .mypy_cache .ruff_cache


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
