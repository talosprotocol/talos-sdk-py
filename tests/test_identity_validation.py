import json
import os
import pytest
from talos_sdk.validation import validate_identity, IdentityValidationError

# Path to vectors
VECTORS_PATH = "/Users/nileshchakraborty/workspace/study/blockchain-mcp-security/deploy/repos/talos-contracts/test_vectors/sdk/identity_validation.json"

def load_matrix():
    with open(VECTORS_PATH, "r") as f:
        return json.load(f)

MATRIX = load_matrix()

def get_test_cases():
    cases = []
    for schema_type, categories in MATRIX.items():
        for category, vectors in categories.items():
            is_valid = (category == "valid")
            for v in vectors:
                cases.append((schema_type, v["data"], is_valid, v["name"]))
    return cases

@pytest.mark.parametrize("schema_type, data, expected_valid, case_name", get_test_cases())
def test_identity_conformance(schema_type, data, expected_valid, case_name):
    """Verify that SDK validation matches normative contract vectors."""
    # Set contracts dir for schema loading
    os.environ["TALOS_CONTRACTS_DIR"] = "/Users/nileshchakraborty/workspace/study/blockchain-mcp-security/deploy/repos/talos-contracts"
    
    if expected_valid:
        # Should not raise
        validate_identity(data, schema_type)
    else:
        # Should raise IdentityValidationError
        with pytest.raises(IdentityValidationError):
            validate_identity(data, schema_type)

def test_missing_schema():
    with pytest.raises(IdentityValidationError, match="Schema for missing not found"):
        validate_identity({}, "missing")

def test_invalid_id_casing():
    # Explicit check for lowercase uuidv7 as per spec
    bad_principal = {
        "schema_id": "talos.principal",
        "schema_version": "v2",
        "id": "01945533-3158-7C85-992D-9865F1715698", # UPPERCASE FAIL
        "principal_id": "p-1",
        "type": "user",
        "auth_mode": "bearer",
        "status": "active",
        "team_id": "01945533-3158-7c85-992d-9865f1715699"
    }
    with pytest.raises(IdentityValidationError, match="Validation failed"):
        validate_identity(bad_principal, "principal")

def test_extra_property_rejection():
    # proving additionalProperties: false
    leaky_org = {
        "schema_id": "talos.org",
        "schema_version": "v2",
        "id": "01945533-3158-7c85-992d-9865f1715698",
        "name": "Acme",
        "domain": "acme.com",
        "extra": "leak"
    }
    with pytest.raises(IdentityValidationError, match="Validation failed"):
        validate_identity(leaky_org, "org")
