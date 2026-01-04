"""
Talos SDK - Secure Multi-Language SDK for AI Agents.

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

from .wallet import Wallet
from .client import TalosClient, PROTOCOL_VERSION
from .mcp import sign_mcp_request, verify_mcp_response, SignedFrame
from .canonical import canonical_json, canonical_json_bytes
from .errors import (
    TalosError,
    TalosDeniedError,
    TalosInvalidCapabilityError,
    TalosProtocolMismatchError,
    TalosFrameInvalidError,
    TalosCryptoError,
    TalosInvalidInputError,
    TalosTransportTimeoutError,
    TalosTransportError,
)

__version__ = "1.0.0"

__all__ = [
    # Core classes
    "Wallet",
    "TalosClient",
    "SignedFrame",
    # Functions
    "sign_mcp_request",
    "verify_mcp_response",
    "canonical_json",
    "canonical_json_bytes",
    # Constants
    "PROTOCOL_VERSION",
    # Errors
    "TalosError",
    "TalosDeniedError",
    "TalosInvalidCapabilityError",
    "TalosProtocolMismatchError",
    "TalosFrameInvalidError",
    "TalosCryptoError",
    "TalosInvalidInputError",
    "TalosTransportTimeoutError",
    "TalosTransportError",
]
