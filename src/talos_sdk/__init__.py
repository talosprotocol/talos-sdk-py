"""Talos SDK - Secure Multi-Language SDK for AI Agents.

This package provides the Python implementation of the Talos Protocol v1,
enabling secure identity, capability authorization, and MCP request signing.

Example:
    >>> from talos_sdk import Wallet, TalosClient
    >>> wallet = Wallet.generate("my-agent")
    >>> client = TalosClient("wss://gateway.example.com", wallet)
    >>> await client.connect()
    >>> response = await client.sign_and_send_mcp(
    ...     {"method": "read", "params": {"path": "/data"}},
    ...     "filesystem",
    ...     "read",
    ... )
"""

from typing import Any

from .a2a_v1 import (
    A2AJsonRpcClient,
    A2AJsonRpcError,
    TALOS_ATTESTATION_EXTENSION,
    TALOS_COMPAT_JSONRPC_EXTENSION,
    TALOS_SECURE_CHANNELS_EXTENSION,
)
from .canonical import canonical_json, canonical_json_bytes
from .errors import (
    TalosCryptoError,
    TalosDeniedError,
    TalosError,
    TalosFrameInvalidError,
    TalosInvalidCapabilityError,
    TalosInvalidInputError,
    TalosProtocolMismatchError,
    TalosTransportError,
    TalosTransportTimeoutError,
)


def _missing_optional_class(name: str, dependency: str, exc: ModuleNotFoundError) -> type:
    class _MissingOptionalDependency:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ModuleNotFoundError(
                f"{name} requires the optional dependency '{dependency}' to be installed"
            ) from exc

    _MissingOptionalDependency.__name__ = name
    return _MissingOptionalDependency


def _missing_optional_function(name: str, dependency: str, exc: ModuleNotFoundError) -> Any:
    def _missing_optional_dependency(*args: Any, **kwargs: Any) -> None:
        raise ModuleNotFoundError(
            f"{name} requires the optional dependency '{dependency}' to be installed"
        ) from exc

    _missing_optional_dependency.__name__ = name
    return _missing_optional_dependency


try:
    from .wallet import Wallet
except ModuleNotFoundError as exc:
    Wallet = _missing_optional_class("Wallet", "cryptography", exc)

try:
    from .mcp import SignedFrame, sign_mcp_request, verify_mcp_response
except ModuleNotFoundError as exc:
    SignedFrame = _missing_optional_class("SignedFrame", "cryptography", exc)
    sign_mcp_request = _missing_optional_function("sign_mcp_request", "cryptography", exc)
    verify_mcp_response = _missing_optional_function("verify_mcp_response", "cryptography", exc)


try:
    from .client import PROTOCOL_VERSION, TalosClient
except ModuleNotFoundError as exc:
    PROTOCOL_VERSION = "1.0"
    TalosClient = _missing_optional_class("TalosClient", "websockets", exc)

try:
    from .mcp_client import McpClient
except ModuleNotFoundError as exc:
    McpClient = _missing_optional_class("McpClient", "requests", exc)

try:
    from .validation import (
        IdentityValidationError,
        validate_identity,
        validate_org,
        validate_principal,
        validate_team,
    )
except ModuleNotFoundError as exc:
    IdentityValidationError = _missing_optional_class(
        "IdentityValidationError", "jsonschema", exc
    )
    validate_principal = _missing_optional_function("validate_principal", "jsonschema", exc)
    validate_org = _missing_optional_function("validate_org", "jsonschema", exc)
    validate_team = _missing_optional_function("validate_team", "jsonschema", exc)
    validate_identity = _missing_optional_function("validate_identity", "jsonschema", exc)

__version__ = "1.0.0"

# SDK Version Exports (required by VERSIONING.md)
SDK_VERSION = __version__
SUPPORTED_PROTOCOL_RANGE = ("1.0", "1.x")
CONTRACT_MANIFEST_HASH = "3gi_Ti6G17oMQabjDlVUXcfBqOjN4HswNdD4Lu0uyyI"

__all__ = [
    # Core classes
    "Wallet",
    "TalosClient",
    "A2AJsonRpcClient",
    "McpClient",
    "SignedFrame",
    # Functions
    "sign_mcp_request",
    "verify_mcp_response",
    "canonical_json",
    "canonical_json_bytes",
    # Constants
    "PROTOCOL_VERSION",
    "A2AJsonRpcError",
    "TALOS_ATTESTATION_EXTENSION",
    "TALOS_SECURE_CHANNELS_EXTENSION",
    "TALOS_COMPAT_JSONRPC_EXTENSION",
    # Errors
    "TalosError",
    "TalosDeniedError",
    "TalosInvalidCapabilityError",
    "TalosProtocolMismatchError",
    "TalosFrameInvalidError",
    "TalosCryptoError",
    "TalosInvalidInputError",
    "TalosTransportError",
    "TalosTransportTimeoutError",
    "IdentityValidationError",
    "validate_principal",
    "validate_org",
    "validate_team",
    "validate_identity",
]
