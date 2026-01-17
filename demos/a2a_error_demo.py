#!/usr/bin/env python3
"""
Talos A2A Error Mapping Demo

Demonstrates how the SDK translates Gateway error responses into specific
Python exceptions with detailed context (current_state, sender_seq, etc).
"""

import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for demo
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from talos_sdk.a2a.errors import (
    raise_mapped_error,
    A2AFrameReplayError,
    A2ASessionStateInvalidError,
    A2AFrameSequenceTooFarError,
    A2ASessionNotFoundError,
)
from talos_sdk.a2a.models import ErrorResponse


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def test_error_mapping(title: str, error_code: str, message: str, details: dict):
    print(f"🔹 Testing: {title}")
    error_resp = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details
    )
    
    try:
        raise_mapped_error(error_resp, status_code=400)
    except Exception as e:
        print(f"   Exception raised: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        for attr in ['current_state', 'sender_seq', 'expected_seq']:
            if hasattr(e, attr):
                print(f"   {attr}: {getattr(e, attr)}")
    print("-" * 40)


def main():
    print_header("Talos A2A Error Mapping Demo")

    # 1. Session Not Found
    test_error_mapping(
        "Session Not Found (404-like)",
        "A2A_SESSION_NOT_FOUND",
        "Session not found in DB",
        {"session_id": "sess-missing-123"}
    )

    # 2. Session State Invalid (with state details)
    test_error_mapping(
        "Session State Invalid",
        "A2A_SESSION_STATE_INVALID",
        "Cannot send frame in PENDING state",
        {"current_state": "PENDING"}
    )

    # 3. Frame Replay Error (with server-side sender_seq)
    test_error_mapping(
        "Frame Replay (Sequence Conflict)",
        "A2A_FRAME_REPLAY_DETECTED",
        "Frame with this sequence already processed",
        {"sender_seq": 42}
    )

    # 4. Sequence Too Far (with expected_seq)
    test_error_mapping(
        "Sequence Gap (Too Far)",
        "A2A_FRAME_SEQUENCE_TOO_FAR",
        "Sequence gap detected",
        {"expected_seq": 10, "received_seq": 15}
    )

    # 5. Frame Size Exceeded
    test_error_mapping(
        "Frame Size Exceeded",
        "A2A_FRAME_SIZE_EXCEEDED",
        "Frame is too large",
        {"size": 1048576, "limit": 1000000}
    )

    # 6. Generic Error Fallback
    test_error_mapping(
        "Unknown Error Code",
        "INTERNAL_SERVER_ERROR",
        "Database connection lost",
        {}
    )

    print_header("Demo Complete!")
    print("✅ All gateway errors successfully mapped to typed Python exceptions.")

if __name__ == "__main__":
    main()
