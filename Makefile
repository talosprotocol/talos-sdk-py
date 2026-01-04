# Universal Makefile Interface
all: install lint test build conformance

install:
	pip install -e .[dev]

typecheck:
	# Enforce type checking (Gradual initially, Strict for core later)
	mypy src tests

lint:
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
	find . -name "__pycache__" -type d -exec rm -rf {} +
