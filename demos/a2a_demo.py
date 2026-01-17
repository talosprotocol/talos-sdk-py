#!/usr/bin/env python3
"""
Talos A2A Communication Demo

Demonstrates end-to-end encrypted agent-to-agent messaging using:
- Double Ratchet Session for forward-secure encryption
- RatchetFrameCrypto adapter for frame generation
- frame_digest computation per Phase 10 LOCKED SPEC

Run: python demos/a2a_demo.py
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos_sdk.a2a.ratchet_crypto import RatchetFrameCrypto, _b64u_decode_strict, NONCE_LEN
from talos_sdk.canonical import canonical_json_bytes
from talos_sdk.crypto import KeyPair, generate_signing_keypair
from talos_sdk.session import Session, SessionManager


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def print_frame(label: str, data: dict) -> None:
    print(f"\n📦 {label}:")
    for key, val in data.items():
        if isinstance(val, str) and len(val) > 50:
            print(f"   {key}: {val[:50]}...")
        else:
            print(f"   {key}: {val}")


def compute_frame_digest(
    session_id: str,
    sender_id: str,
    sender_seq: int,
    header_b64u: str,
    ciphertext_hash: str,
) -> str:
    """Compute frame_digest per Phase 10 LOCKED SPEC."""
    preimage = {
        "schema_id": "talos.a2a.encrypted_frame",
        "schema_version": "v1",
        "session_id": session_id,
        "sender_id": sender_id,
        "sender_seq": sender_seq,
        "header_b64u": header_b64u,
        "ciphertext_hash": ciphertext_hash,
    }
    return hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()


def main():
    print_header("Talos A2A Communication Demo")
    
    # =========================================================================
    # Step 1: Setup identities (using Ed25519 for signing)
    # =========================================================================
    print("🔑 Creating agent identities...")
    
    # Ed25519 keys for identity/signing
    alice_keypair = generate_signing_keypair()
    bob_keypair = generate_signing_keypair()
    
    alice_manager = SessionManager(alice_keypair)
    bob_manager = SessionManager(bob_keypair)
    
    print(f"   Alice ID: alice-agent-001")
    print(f"   Bob ID:   bob-agent-002")
    
    # =========================================================================
    # Step 2: Exchange prekey bundles (simulated discovery)
    # =========================================================================
    print_header("Key Exchange (X3DH)")
    
    bob_bundle = bob_manager.get_prekey_bundle()
    print(f"📨 Bob publishes prekey bundle")
    print(f"   Identity key:  {bob_bundle.identity_key.hex()[:32]}...")
    print(f"   Signed prekey: {bob_bundle.signed_prekey.hex()[:32]}...")
    
    # =========================================================================
    # Step 3: Alice initiates session
    # =========================================================================
    print_header("Session Establishment")
    
    alice_session = alice_manager.create_session_as_initiator("bob-agent-002", bob_bundle)
    print(f"✅ Alice created session as initiator")
    
    # Bob creates session as responder (using Alice's ephemeral DH key)
    bob_session = bob_manager.create_session_as_responder(
        "alice-agent-001",
        alice_session.state.dh_keypair.public_key,
    )
    print(f"✅ Bob created session as responder")
    
    # =========================================================================
    # Step 4: Create RatchetFrameCrypto adapters
    # =========================================================================
    print_header("RatchetFrameCrypto Setup")
    
    alice_crypto = RatchetFrameCrypto(alice_session)
    bob_crypto = RatchetFrameCrypto(bob_session)
    
    print(f"🔐 Alice crypto adapter ready")
    print(f"🔐 Bob crypto adapter ready")
    
    # Session metadata
    session_id = "sess-demo-001"
    
    # =========================================================================
    # Step 5: Alice sends encrypted message
    # =========================================================================
    print_header("Alice → Bob: Encrypted Message")
    
    plaintext = b"Hello Bob! This is a secure A2A message with forward secrecy."
    print(f"📝 Plaintext: {plaintext.decode()}")
    
    # Encrypt
    header_b64u, ciphertext_b64u, ciphertext_hash = alice_crypto.encrypt(plaintext)
    
    # Compute frame_digest (normally done by session_client)
    sender_seq = 0
    frame_digest = compute_frame_digest(
        session_id=session_id,
        sender_id="alice-agent-001",
        sender_seq=sender_seq,
        header_b64u=header_b64u,
        ciphertext_hash=ciphertext_hash,
    )
    
    # Construct frame
    frame = {
        "schema_id": "talos.a2a.encrypted_frame",
        "schema_version": "v1",
        "session_id": session_id,
        "sender_id": "alice-agent-001",
        "sender_seq": sender_seq,
        "header_b64u": header_b64u,
        "ciphertext_b64u": ciphertext_b64u,
        "ciphertext_hash": ciphertext_hash,
        "frame_digest": frame_digest,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    
    print_frame("Encrypted Frame", {
        "session_id": frame["session_id"],
        "sender_id": frame["sender_id"],
        "sender_seq": frame["sender_seq"],
        "header_b64u": frame["header_b64u"],
        "ciphertext_hash": frame["ciphertext_hash"],
        "frame_digest": frame["frame_digest"],
    })
    
    # =========================================================================
    # Step 6: Bob decrypts message
    # =========================================================================
    print_header("Bob Receives & Decrypts")
    
    # Verify ciphertext_hash before decrypting
    combined = _b64u_decode_strict(frame["ciphertext_b64u"])
    ciphertext_only = combined[NONCE_LEN:]
    computed_hash = hashlib.sha256(ciphertext_only).hexdigest()
    
    if computed_hash == frame["ciphertext_hash"]:
        print(f"✅ Ciphertext hash verified")
    else:
        print(f"❌ Ciphertext hash mismatch!")
        return
    
    # Decrypt
    decrypted = bob_crypto.decrypt(
        frame["header_b64u"],
        frame["ciphertext_b64u"],
        frame["ciphertext_hash"],
    )
    
    print(f"🔓 Decrypted: {decrypted.decode()}")
    
    # Verify plaintext matches
    if decrypted == plaintext:
        print(f"✅ Plaintext matches original!")
    
    # =========================================================================
    # Step 7: Bob sends reply
    # =========================================================================
    print_header("Bob → Alice: Reply Message")
    
    reply = b"Hi Alice! Got your message. Double Ratchet working perfectly!"
    print(f"📝 Reply: {reply.decode()}")
    
    header_b64u, ciphertext_b64u, ciphertext_hash = bob_crypto.encrypt(reply)
    
    sender_seq = 0
    frame_digest = compute_frame_digest(
        session_id=session_id,
        sender_id="bob-agent-002",
        sender_seq=sender_seq,
        header_b64u=header_b64u,
        ciphertext_hash=ciphertext_hash,
    )
    
    reply_frame = {
        "schema_id": "talos.a2a.encrypted_frame",
        "sender_id": "bob-agent-002",
        "sender_seq": sender_seq,
        "frame_digest": frame_digest,
    }
    
    print_frame("Reply Frame", reply_frame)
    
    # Alice decrypts
    decrypted_reply = alice_crypto.decrypt(header_b64u, ciphertext_b64u, ciphertext_hash)
    print(f"\n🔓 Alice decrypted: {decrypted_reply.decode()}")
    
    # =========================================================================
    # Step 8: Security properties demonstration
    # =========================================================================
    print_header("Security Properties")
    
    print("🛡️  Forward Secrecy:")
    print("   - Each message uses a unique message key")
    print("   - Keys are deleted after use")
    print("   - Compromising current key doesn't reveal past messages")
    
    print("\n🔄 Break-in Recovery:")
    print("   - DH ratchet generates fresh keys")
    print("   - Recovery happens automatically")
    print("   - Future messages remain secure")
    
    print("\n🔐 Frame Integrity:")
    print("   - ciphertext_hash: SHA-256 of ciphertext (not nonce)")
    print("   - frame_digest: SHA-256 of canonical preimage")
    print("   - AEAD: ChaCha20-Poly1305 with header as AAD")
    
    # =========================================================================
    # Summary
    # =========================================================================
    print_header("Demo Complete!")
    
    print(f"📊 Session Statistics:")
    print(f"   Alice messages sent:     {alice_session.messages_sent}")
    print(f"   Alice messages received: {alice_session.messages_received}")
    print(f"   Bob messages sent:       {bob_session.messages_sent}")
    print(f"   Bob messages received:   {bob_session.messages_received}")
    
    print(f"\n✅ All Phase 10 features demonstrated:")
    print(f"   - X3DH key exchange")
    print(f"   - Double Ratchet encryption")
    print(f"   - RatchetFrameCrypto adapter")
    print(f"   - frame_digest computation")
    print(f"   - ciphertext_hash verification")
    print(f"   - Base64url encoding (no padding)")


if __name__ == "__main__":
    main()
