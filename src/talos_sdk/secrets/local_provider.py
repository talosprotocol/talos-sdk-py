import os
import binascii
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .kek import KekProvider, Envelope, ALGORITHM_AES_256_GCM

class LocalKekProvider(KekProvider):
    """
    KekProvider using a local AES key (32 bytes).
    WARN: In production, use HSM/KMS.
    """
    def __init__(self, master_key_hex: str, key_id: str):
        self.key_bytes = binascii.unhexlify(master_key_hex)
        if len(self.key_bytes) != 32:
            raise ValueError("Master key must be 32 bytes (64 hex chars)")
        self.key_id = key_id
        self.aesgcm = AESGCM(self.key_bytes)

    def encrypt(self, plaintext: bytes) -> Envelope:
        iv = os.urandom(12)
        ciphertext_and_tag = self.aesgcm.encrypt(iv, plaintext, None)
        
        # Split (tag is last 16 bytes for AESGCM in cryptography lib?)
        # Wait, AESGCM.encrypt returns ciphertext + tag appended.
        ciphertext = ciphertext_and_tag[:-16]
        tag = ciphertext_and_tag[-16:]
        
        return Envelope(
            kek_id=self.key_id,
            iv=binascii.hexlify(iv).decode('ascii'),
            ciphertext=binascii.hexlify(ciphertext).decode('ascii'),
            tag=binascii.hexlify(tag).decode('ascii'),
            alg=ALGORITHM_AES_256_GCM
        )

    def decrypt(self, envelope: Envelope) -> bytes:
        if envelope.kek_id != self.key_id:
            raise ValueError(f"Key mismatch: Envelope uses {envelope.kek_id}, Provider has {self.key_id}")
        
        if envelope.alg != ALGORITHM_AES_256_GCM:
            raise ValueError(f"Unsupported algorithm: {envelope.alg}")
            
        iv = binascii.unhexlify(envelope.iv)
        tag = binascii.unhexlify(envelope.tag)
        ciphertext = binascii.unhexlify(envelope.ciphertext)
        
        # cryptography expects ciphertext + tag for decrypt
        data = ciphertext + tag
        
        return self.aesgcm.decrypt(iv, data, None)
