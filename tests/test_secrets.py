import pytest
import binascii
import os
from talos_sdk.secrets.kek import Envelope, ALGORITHM_AES_256_GCM, generate_master_key
from talos_sdk.secrets.local_provider import LocalKekProvider

# Do NOT hardcode master keys in source. Load from environment or generate for ephemeral tests.
MASTER_KEY = os.environ.get("TALOS_MASTER_KEY", generate_master_key())
KEY_ID = "kek-v1"

@pytest.fixture
def provider():
    return LocalKekProvider(MASTER_KEY, KEY_ID)

def test_encrypt_decrypt_roundtrip(provider):
    plaintext = b"super secret data"
    envelope = provider.encrypt(plaintext)
    
    # Verify Envelope Structure
    assert envelope.kek_id == KEY_ID
    assert envelope.alg == ALGORITHM_AES_256_GCM
    assert len(binascii.unhexlify(envelope.iv)) == 12
    assert len(binascii.unhexlify(envelope.tag)) == 16
    assert envelope.ciphertext # Not empty
    
    # Decrypt
    decrypted = provider.decrypt(envelope)
    assert decrypted == plaintext

def test_decrypt_fail_key_mismatch(provider):
    plaintext = b"data"
    envelope = provider.encrypt(plaintext)
    
    # Tamper key ID
    envelope.kek_id = "wrong-key"
    
    with pytest.raises(ValueError, match="Key mismatch"):
        provider.decrypt(envelope)

def test_decrypt_fail_tampered_ciphertext(provider):
    plaintext = b"data"
    envelope = provider.encrypt(plaintext)
    
    # Tamper ciphertext (flip last char)
    # Ciphertext is hex string
    ct_bytes = bytearray(binascii.unhexlify(envelope.ciphertext))
    ct_bytes[-1] ^= 0xFF
    envelope.ciphertext = binascii.hexlify(ct_bytes).decode('ascii')
    
    # GCM should fail authentication (tag mismatch effectively, or integrity check)
    from cryptography.exceptions import InvalidTag
    with pytest.raises(InvalidTag):
        provider.decrypt(envelope)

def test_envelope_serialization():
    env = Envelope(
        kek_id="k1",
        iv="00"*12,
        ciphertext="aa",
        tag="bb"*16,
        alg="aes-256-gcm"
    )
    d = env.to_dict()
    assert d["kek_id"] == "k1"
    
    env2 = Envelope.from_dict(d)
    assert env2.kek_id == "k1"
    assert env2.iv == env.iv
