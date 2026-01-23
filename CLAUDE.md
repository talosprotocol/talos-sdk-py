# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is the Talos SDK for Python, providing Python bindings to the core Talos Protocol functionality. The SDK enables secure, encrypted communication between autonomous agents through implementation of the Double Ratchet Algorithm and Model Context Protocol (MCP) integrations.

## Repository Structure

Key directories and files include:

- `src/talos_sdk/` - Main Python source code organized by modules:
  - `wallet.py` - Ed25519 identity and signing
  - `session.py` - Double Ratchet core (Session, SessionManager)
  - `client.py` - TalosClient for gateway interaction
  - `mcp.py` - MCP request signing
  - `crypto.py` - Cryptographic primitives
  - `canonical.py` - RFC 8785 canonical JSON
  - `a2a/` - Phase 10 A2A Communication components
- `tests/` - Unit tests for all SDK components
- `examples/` - Practical usage examples
- `scripts/` - Development and CI scripts
- `artifacts/` - Test and build artifacts
- `docs/` - Additional documentation

## Common Development Commands

### Setup and Initialization
```bash
# Install development dependencies
make install

# Install in development mode
pip install -e .[dev]
```

### Building
```bash
# Build distributable packages
make build
# or
python -m build

# Clean build artifacts
make clean
```

### Testing
```bash
# Run unit tests
make test
# or
pytest tests

# Run with coverage reporting
make coverage

# Run conformance tests against contracts
make conformance

# Run standardized test script (used by CI)
scripts/test.sh --unit
scripts/test.sh --ci
scripts/test.sh --coverage

# Specific test modes via test.sh:
# --smoke, --unit, --integration, --coverage, --ci, --full
```

### Code Quality
```bash
# Run linting and type checking
make lint
# or separately:
ruff check .
mypy src tests

# Auto-format code
make format
# or:
ruff format .

# Type checking only
make typecheck
# or:
mypy src tests
```

## Architecture Guidelines

1. **Module Organization**:
   - Core cryptographic functionality in `src/talos_sdk/`
   - A2A communication components in `src/talos_sdk/a2a/`
   - Clear separation between transport, encryption, and application layers

2. **Security Patterns**:
   - No plaintext data sent to gateway
   - End-to-end encryption using Double Ratchet Algorithm
   - Identity management via Ed25519 wallets
   - RFC 8785 canonical JSON for consistent serialization

3. **Phase 10 Layering**:
   - Phase 10.2: Transport layer with HTTP transport, sequencing, typed models
   - Phase 10.3: Ratchet binding with Double Ratchet encryption via FrameCrypto

## Language-Specific Patterns

### Python SDK Patterns
- Uses `pytest` with `PYTHONPATH=src` for tests
- Coverage via `pytest-cov` plugin
- Tests located in `tests/` directory with parallel structure to `src/`
- Type checking with `mypy`
- Code formatting with `ruff`
- Follows standard Python packaging with `pyproject.toml`

### Key Components
1. **Wallet** (`wallet.py`) - Ed25519 identity creation and management
2. **Session Management** (`session.py`) - Double Ratchet implementation
3. **A2A Communication** (`a2a/` directory) - Secure agent-to-agent messaging
4. **MCP Integration** (`mcp.py`) - Model Context Protocol signing support
5. **Cryptographic Primitives** (`crypto.py`) - Low-level crypto operations

## Key Scripts and Tools

- `scripts/test.sh` - Standardized test entrypoint supporting multiple modes
- `Makefile` - Universal interface for common development tasks
- `pyproject.toml` - Package configuration and dependency management
- Conformance testing against `talos-contracts` test vectors

## Development Workflow

1. Make changes in appropriate module within `src/talos_sdk/`
2. Add/update corresponding tests in `tests/`
3. Run `make lint` to check code quality
4. Run `make test` or `scripts/test.sh --unit` to validate functionality
5. Run `make coverage` to ensure adequate test coverage
6. Commit changes (triggers pre-commit hooks at repository level)
7. Push to remote for CI validation