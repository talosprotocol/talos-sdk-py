import hashlib
import json
from typing import Any

from talos_sdk.ports.hash import IHashPort


class NativeHashAdapter(IHashPort):
    def sha256(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def canonical_hash(self, obj: Any) -> bytes:
        # Canonical JSON: keys sorted, no specific whitespace (compact)
        # We use separators=(',', ':') to eliminate whitespace
        canonical_json = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return self.sha256(canonical_json.encode("utf-8"))
