"""JSON Schema validation for Talos identities."""

import json
import os
from typing import Any
from jsonschema import validate, ValidationError, Draft202012Validator
from .errors import TalosInvalidInputError

class IdentityValidationError(TalosInvalidInputError):
    """Raised when an identity fails validation against normative schemas."""
    def __init__(self, message: str, **kwargs: Any):
        super().__init__(message, **kwargs)

def _get_schema_path(schema_name: str) -> str:
    """Locate the schema file for the given rbac type."""
    # 1. Check for explicit override (dev/test)
    contracts_dir = os.environ.get("TALOS_CONTRACTS_DIR")
    if contracts_dir:
        path = os.path.join(contracts_dir, "schemas", "rbac", f"{schema_name}.schema.json")
        if os.path.exists(path):
            return path

    # 2. Try bundled assets (relative to this file)
    # Note: This assumes talos-contracts is installed and assets are properly bundled.
    # In this monorepo environment, we might need a better fallback.
    try:
        import talos_contracts
        package_path = os.path.dirname(talos_contracts.__file__)
        path = os.path.join(package_path, "assets", "schemas", "rbac", f"{schema_name}.schema.json")
        if os.path.exists(path):
            return path
    except ImportError:
        pass

    # 3. Monorepo fallback (absolute path to contracts repo)
    monorepo_path = "/Users/nileshchakraborty/workspace/study/blockchain-mcp-security/deploy/repos/talos-contracts"
    path = os.path.join(monorepo_path, "schemas", "rbac", f"{schema_name}.schema.json")
    if os.path.exists(path):
        return path

    raise IdentityValidationError(f"Schema for {schema_name} not found")

def validate_identity(identity: dict[str, Any], schema_type: str) -> None:
    """
    Validate an identity object (Principal, Org, Team) against normative Draft 2020-12 schemas.
    
    Args:
        identity: The identity object to validate.
        schema_type: One of 'principal', 'org', 'team'.
        
    Raises:
        IdentityValidationError: If validation fails or schema is missing.
    """
    schema_path = _get_schema_path(schema_type)
    
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
        
        # We use Draft202012Validator explicitly for hardening
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(identity))
        
        if errors:
            # Format first error for the message
            err = errors[0]
            msg = f"Validation failed for {schema_type}: {err.message} at {'.'.join(map(str, err.path))}"
            raise IdentityValidationError(msg)
            
    except (ValidationError, Exception) as e:
        if isinstance(e, IdentityValidationError):
            raise
        raise IdentityValidationError(f"Schema validation error: {str(e)}")

def validate_principal(principal: dict[str, Any]) -> None:
    validate_identity(principal, "principal")

def validate_org(org: dict[str, Any]) -> None:
    validate_identity(org, "org")

def validate_team(team: dict[str, Any]) -> None:
    validate_identity(team, "team")
