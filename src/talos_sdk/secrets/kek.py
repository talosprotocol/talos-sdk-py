import abc
import base64
import json
from dataclasses import dataclass
from typing import Optional

ALGORITHM_AES_256_GCM = "aes-256-gcm"

@dataclass
class Envelope:
    """Encrypted data envelope (Draft 2020-12)."""
    kek_id: str
    iv: str        # 24 hex char (12 bytes)
    ciphertext: str # Hex
    tag: str       # 32 hex char (16 bytes)
    alg: str = ALGORITHM_AES_256_GCM

    def to_dict(self) -> dict:
        return {
            "kek_id": self.kek_id,
            "iv": self.iv,
            "ciphertext": self.ciphertext,
            "tag": self.tag,
            "alg": self.alg
        }

    @staticmethod
    def from_dict(data: dict) -> 'Envelope':
        return Envelope(
            kek_id=data["kek_id"],
            iv=data["iv"],
            ciphertext=data["ciphertext"],
            tag=data["tag"],
            alg=data.get("alg", ALGORITHM_AES_256_GCM)
        )

class KekProvider(abc.ABC):
    """Abstract interface for Key Encryption Key providers."""

    @abc.abstractmethod
    def encrypt(self, plaintext: bytes) -> Envelope:
        """Encrypt plaintext bytes and return Envelope."""
        pass

    @abc.abstractmethod
    def decrypt(self, envelope: Envelope) -> bytes:
        """Decrypt envelope and return plaintext bytes."""
        pass

def generate_master_key() -> str:
    """Generate a stable 256-bit (32 byte) master key in hex format."""
    import secrets
    return secrets.token_hex(32)
