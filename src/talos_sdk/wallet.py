"""Talos SDK Wallet.

Identity management as defined in SDK_CONTRACT.md.
"""

import hashlib
import os
import time

from typing import Any, Dict

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from talos_contracts import base64url_encode

from .canonical import canonical_json_bytes

from .errors import TalosInvalidInputError

# Base58btc alphabet for DID encoding
_BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _base58_encode(data: bytes) -> str:
    """Encode bytes to base58btc."""
    num = int.from_bytes(data, "big")
    result = []
    while num > 0:
        num, remainder = divmod(num, 58)
        result.append(_BASE58_ALPHABET[remainder])
    # Handle leading zeros
    for byte in data:
        if byte == 0:
            result.append(_BASE58_ALPHABET[0])
        else:
            break
    return "".join(reversed(result))


class Wallet:
    """Talos identity wallet for key management and signing.

    Implements the Identity module from SDK_CONTRACT.md.
    """

    def __init__(
        self,
        private_key: Ed25519PrivateKey,
        name: str | None = None,
    ):
        """Initialize a Wallet from a private key.

        Args:
            private_key: Ed25519 private key
            name: Optional human-readable name
        """
        self._private_key = private_key
        self._public_key = private_key.public_key()
        self._name = name

    @classmethod
    def generate(cls, name: str | None = None) -> "Wallet":
        """Generate a new wallet with a random keypair.

        Args:
            name: Optional human-readable name for the wallet

        Returns:
            A new Wallet instance with a randomly generated keypair

        Note:
            This method is non-deterministic (uses secure random).
        """
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key, name)

    @classmethod
    def from_seed(cls, seed: bytes, name: str | None = None) -> "Wallet":
        """Create a wallet from a 32-byte seed.

        Args:
            seed: 32-byte seed (raw bytes)
            name: Optional human-readable name

        Returns:
            A Wallet instance derived deterministically from the seed

        Raises:
            TalosInvalidInputError: If seed length is not 32 bytes
        """
        if len(seed) != 32:
            raise TalosInvalidInputError(
                f"Seed must be exactly 32 bytes, got {len(seed)}",
                details={"seed_length": len(seed)},
            )
        private_key = Ed25519PrivateKey.from_private_bytes(seed)
        return cls(private_key, name)

    def to_did(self) -> str:
        """Convert the wallet's public key to a DID string.

        Returns:
            DID string in format did:key:z6Mk...

        Note:
            Deterministic - same public key produces identical DID.
        """
        # Multicodec prefix for Ed25519 public key: 0xed01
        prefix = bytes([0xED, 0x01])
        public_bytes = self._public_key.public_bytes_raw()
        multicodec_key = prefix + public_bytes
        return f"did:key:z{_base58_encode(multicodec_key)}"

    @property
    def address(self) -> str:
        """Get the hex-encoded public key hash (address).

        Returns:
            64-character hex string
        """
        public_bytes = self._public_key.public_bytes_raw()
        return hashlib.sha256(public_bytes).hexdigest()

    @property
    def public_key(self) -> bytes:
        """Get the 32-byte public key."""
        return self._public_key.public_bytes_raw()

    @property
    def name(self) -> str | None:
        """Get the wallet name."""
        return self._name

    @property
    def key_id(self) -> str:
        """Get the key ID (truncated DID for HTTP headers)."""
        return self.to_did()

    def sign(self, message: bytes) -> bytes:
        """Sign a message using Ed25519.

        Args:
            message: Arbitrary message bytes

        Returns:
            64-byte Ed25519 signature

        Note:
            Deterministic - Ed25519 signing is deterministic.
        """
        return self._private_key.sign(message)

    @staticmethod
    def verify(message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify a signature against a message and public key.

        Args:
            message: Original message bytes
            signature: 64-byte signature
            public_key: 32-byte public key

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            pk = Ed25519PublicKey.from_public_bytes(public_key)
            pk.verify(signature, message)
            return True
        except Exception:  # noqa: E722; pylint: disable=broad-except
            return False

    def sign_http_request(
        self,
        method: str,
        path: str,
        query: str = "",
        body: Dict[str, Any] | None = None,
        opcode: str = "http.request"
    ) -> Dict[str, str]:
        """Sign an HTTP request for Phase 3 Attestation.

        Args:
            method: HTTP Method (e.g. POST)
            path: Raw path (e.g. /v1/chat)
            query: Raw query string (e.g. k=v&a=b)
            body: Request body dict (or None)
            opcode: Operation code (default: http.request)

        Returns:
            Dict of headers to add to the request:
            - X-Talos-Key-ID
            - X-Talos-Timestamp
            - X-Talos-Nonce
            - X-Talos-Signature
            - X-Talos-Sig-Alg
            - X-Talos-Sig-Version
        """
        # 1. Prepare inputs
        timestamp = int(time.time())
        nonce = base64url_encode(os.urandom(12))

        if body is None:
            body_bytes = b""
        else:
            body_bytes = canonical_json_bytes(body)

        method_ascii = method.upper().encode('ascii')
        
        # Path+Query: raw string exactly as sent
        # Expect caller to provide raw path and raw query string
        full_path = path + (f"?{query}" if query else "")
        path_query_ascii = full_path.encode('ascii')

        nonce_ascii = nonce.encode('ascii')
        ts_ascii = str(timestamp).encode('ascii')
        opcode_ascii = opcode.encode('ascii')

        # 2. Construct Signing Input (Strict Byte-Level)
        signing_input = (
            body_bytes + b"\n" +
            method_ascii + b"\n" +
            path_query_ascii + b"\n" +
            nonce_ascii + b"\n" +
            ts_ascii + b"\n" +
            opcode_ascii
        )
        
        # 3. Sign
        sig_bytes = self.sign(signing_input)
        sig_b64 = base64url_encode(sig_bytes)

        return {
            "X-Talos-Key-ID": self.key_id,
            "X-Talos-Timestamp": str(timestamp),
            "X-Talos-Nonce": nonce,
            "X-Talos-Signature": sig_b64,
            "X-Talos-Sig-Alg": "ed25519",
            "X-Talos-Sig-Version": "v1"
        }
