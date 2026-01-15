import abc
import binascii
import json
import re
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator

ALGORITHM_AES_256_GCM = "aes-256-gcm"
SCHEMA_ID_ENVELOPE = "talos.secrets.envelope"
SCHEMA_VERSION_V1 = "v1"

class Envelope(BaseModel):
    """
    Encrypted data envelope (Draft 2020-12 / Normative).
    
    Ensures structural integrity and metadata compliance for secrets-at-rest.
    """
    kek_id: str = Field(..., min_length=1, max_length=255)
    iv: str = Field(..., pattern=r"^[0-9a-f]{24}$")        # 24 hex char (12 bytes)
    ciphertext: str = Field(..., pattern=r"^[0-9a-f]+$") # Hex
    tag: str = Field(..., pattern=r"^[0-9a-f]{32}$")       # 32 hex char (16 bytes)
    alg: str = Field(default=ALGORITHM_AES_256_GCM)
    schema_id: str = Field(default=SCHEMA_ID_ENVELOPE)
    schema_version: str = Field(default=SCHEMA_VERSION_V1)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z")

    @field_validator("alg")
    @classmethod
    def validate_alg(cls, v):
        if v != ALGORITHM_AES_256_GCM:
            raise ValueError(f"Unsupported algorithm: {v}")
        return v

    @field_validator("schema_id")
    @classmethod
    def validate_schema_id(cls, v):
        if v != SCHEMA_ID_ENVELOPE:
            raise ValueError(f"Invalid schema_id: {v}")
        return v

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, v):
        if v != SCHEMA_VERSION_V1:
            raise ValueError(f"Invalid schema_version: {v}")
        return v

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Envelope':
        return Envelope.model_validate(data)

    def to_json(self) -> str:
        return self.model_dump_json()

    @staticmethod
    def from_json(json_str: str) -> 'Envelope':
        return Envelope.model_validate_json(json_str)

class KekProvider(abc.ABC):
    """Abstract interface for Key Encryption Key providers."""

    @abc.abstractmethod
    def encrypt(self, plaintext: bytes) -> Envelope:
        """Encrypt plaintext bytes and return Envelope."""

    @abc.abstractmethod
    def decrypt(self, envelope: Envelope) -> bytes:
        """Decrypt envelope and return plaintext bytes."""

def generate_master_key() -> str:
    """Generate a stable 256-bit (32 byte) master key in hex format."""
    import secrets
    return secrets.token_hex(32)
