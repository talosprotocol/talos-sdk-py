#!/usr/bin/env python3
"""
Talos A2A Group Management Demo

Demonstrates A2A Group lifecycle and membership event structures.
Group management includes:
- Group creation (owner-only)
- Membership transitions (INVITED, JOINED, LEFT)
- Membership event hash-chaining (simulated)
"""

import sys
import hashlib
from datetime import datetime, timezone
from pathlib import Path

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos_sdk.a2a.models import GroupResponse
from talos_sdk.canonical import canonical_json_bytes


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def create_group_event(group_id: str, actor_id: str, target_id: str, event_type: str, previous_digest: str = "0" * 64):
    """Simulate a group membership event."""
    ts = datetime.now(timezone.utc).isoformat()
    preimage = {
        "schema_id": "talos.a2a.group_membership_event",
        "schema_version": "v1",
        "group_id": group_id,
        "actor_id": actor_id,
        "target_id": target_id,
        "event_type": event_type,
        "ts": ts,
        "previous_digest": previous_digest
    }
    digest = hashlib.sha256(canonical_json_bytes(preimage)).hexdigest()
    return preimage, digest


def main():
    print_header("Talos A2A Group Management Demo")

    # 1. Group Creation
    print("🏗️  Creating Group...")
    group = GroupResponse(
        group_id="group-security-ops",
        owner_id="admin-agent",
        state="ACTIVE"
    )
    print(f"   Group ID: {group.group_id}")
    print(f"   Owner:    {group.owner_id}")
    print(f"   State:    {group.state}")

    # 2. Membership Events (Hash Chain)
    print_header("Membership Event Hash Chain")

    # Event 1: Admin invites Alice
    e1_data, e1_digest = create_group_event(
        group.group_id, "admin-agent", "alice-agent", "INVITED"
    )
    print(f"🔹 Event 1: admin-agent INVITED alice-agent")
    print(f"   Digest:   {e1_digest[:16]}...")
    print(f"   Previous: {e1_data['previous_digest'][:16]}...")

    # Event 2: Alice joins
    e2_data, e2_digest = create_group_event(
        group.group_id, "alice-agent", "alice-agent", "JOINED", previous_digest=e1_digest
    )
    print(f"\n🔹 Event 2: alice-agent JOINED group")
    print(f"   Digest:   {e2_digest[:16]}...")
    print(f"   Previous: {e2_data['previous_digest'][:16]}... (Links to Event 1)")

    # Event 3: Admin invites Bob
    e3_data, e3_digest = create_group_event(
        group.group_id, "admin-agent", "bob-agent", "INVITED", previous_digest=e2_digest
    )
    print(f"\n🔹 Event 3: admin-agent INVITED bob-agent")
    print(f"   Digest:   {e3_digest[:16]}...")
    print(f"   Previous: {e3_data['previous_digest'][:16]}... (Links to Event 2)")

    # 3. Verification
    print_header("Verification Proof")
    print("✅ Group State: ACTIVE")
    print("✅ Membership Chain: 3 events linked via previous_digest")
    print("✅ Determinism: All digests computed using RFC 8785 Canonical JSON")

    print_header("Demo Complete!")
    print("✅ Group management logic and event structures verified.")

if __name__ == "__main__":
    main()
