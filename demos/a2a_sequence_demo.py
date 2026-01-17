#!/usr/bin/env python3
"""
Talos A2A Sequence Persistence Demo

Demonstrates monotonic sequence tracking and persistence across client instances.
Key features:
- Sequence tracking per (session_id, sender_id)
- Persistence using InMemorySequenceStorage
- Isolation between different sessions and senders
"""

import sys
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos_sdk.a2a.sequence_tracker import SequenceTracker, InMemorySequenceStorage

def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")

def main():
    print_header("Talos A2A Sequence Persistence Demo")

    # We use a shared storage instance to simulate persistence (e.g., a file or database)
    storage = InMemorySequenceStorage()
    
    session_a = "session-alpha"
    session_b = "session-beta"
    alice = "alice"
    bob = "bob"

    print(f"📂 Shared Storage Initialized")
    print(f"   Sessions: {session_a}, {session_b}")
    print(f"   Senders: {alice}, {bob}")

    # 1. First client instance for Alice in Session A
    print_header("Client Instance 1: Alice in Session A")
    tracker1 = SequenceTracker(session_a, alice, storage)
    
    seq1 = tracker1.reserve()
    seq2 = tracker1.reserve()
    print(f"   Reserved Sequence 1: {seq1}")
    print(f"   Reserved Sequence 2: {seq2}")

    # 2. Second client instance for Alice in Session A (Simulated Restart/Re-init)
    print_header("Client Instance 2: Alice in Session A (Re-init)")
    tracker2 = SequenceTracker(session_a, alice, storage)
    
    seq3 = tracker2.reserve()
    print(f"   Reserved Sequence 3: {seq3} (Should be 2)")
    assert seq3 == 2, f"Expected 2, got {seq3}"
    print(f"   ✅ Sequence persisted correctly for Alice in Session A")

    # 3. Isolation: Bob in Session A
    print_header("Isolation: Bob in Session A")
    tracker_bob = SequenceTracker(session_a, bob, storage)
    
    seq_bob = tracker_bob.reserve()
    print(f"   Bob Sequence 1: {seq_bob} (Should be 0)")
    assert seq_bob == 0, f"Expected 0, got {seq_bob}"
    print(f"   ✅ Sequence isolated for different sender in same session")

    # 4. Isolation: Alice in Session B
    print_header("Isolation: Alice in Session B")
    tracker_alice_b = SequenceTracker(session_b, alice, storage)
    
    seq_alice_b = tracker_alice_b.reserve()
    print(f"   Alice (Session B) Sequence 1: {seq_alice_b} (Should be 0)")
    assert seq_alice_b == 0, f"Expected 0, got {seq_alice_b}"
    print(f"   ✅ Sequence isolated for same sender in different session")

    # 5. Global Default Storage Test
    print_header("Global Default Storage Test")
    print("   Creating tracker without explicit storage (using process-global default)...")
    tracker_global = SequenceTracker("global-session", "global-sender")
    
    g_seq1 = tracker_global.reserve()
    print(f"   Global Seq 1: {g_seq1}")
    
    # Create another tracker for the same global session/sender
    tracker_global_2 = SequenceTracker("global-session", "global-sender")
    g_seq2 = tracker_global_2.reserve()
    print(f"   Global Seq 2: {g_seq2} (Should be 1)")
    assert g_seq2 == 1, f"Expected 1, got {g_seq2}"
    print("   ✅ Sequence persisted correctly via global process-level default storage")

    print_header("Demo Complete!")
    print("Summary of Test coverage:")
    print("- [x] Monotonic increment per sender/session")
    print("- [x] Persistence across tracker instances")
    print("- [x] Isolation between senders in the same session")
    print("- [x] Isolation between sessions for the same sender")
    print("- [x] Process-wide global default storage")

if __name__ == "__main__":
    main()
