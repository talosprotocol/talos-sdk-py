"""Framing logic for Talos SDK."""

import json

from .canonical import canonical_json_bytes
from .crypto import b64u_decode as base64url_decode
from .crypto import b64u_encode as base64url_encode


class Frame:
    def __init__(
        self, frame_type: str, payload: bytes, version: int = 1, flags: int = 0
    ):
        self.type = frame_type
        self.payload = payload
        self.version = version
        self.flags = flags

    def encode(self) -> bytes:
        frame_obj = {
            "version": self.version,
            "type": self.type,
            "flags": self.flags,
            "payload": base64url_encode(self.payload),
        }
        # Encode whole object as base64url
        json_bytes = canonical_json_bytes(frame_obj)
        return base64url_encode(json_bytes).encode("utf-8")

    @classmethod
    def decode(cls, data: bytes) -> "Frame":
        try:
            # Data is base64url encoded JSON
            json_str = base64url_decode(data.decode("utf-8")).decode("utf-8")
            obj = json.loads(json_str)

            if "type" not in obj or "payload" not in obj:
                raise ValueError("Invalid frame fields")

            return cls(
                frame_type=obj["type"],
                payload=base64url_decode(obj["payload"]),
                version=obj.get("version", 1),
                flags=obj.get("flags", 0),
            )
        except Exception as e:
            from .errors import TalosFrameInvalidError

            raise TalosFrameInvalidError(f"Frame decoding failed: {e}")
