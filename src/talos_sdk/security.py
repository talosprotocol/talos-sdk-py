"""
Capability management for Talos SDK.
"""

from typing import Any, Optional
from .wallet import Wallet
from .canonical import canonical_json_bytes
import base64


def base64url_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def base64url_decode(s: str) -> bytes:
    s += "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s)


class Capability:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.v = data.get("v", "1")
        self.iss = data.get("iss")
        self.sub = data.get("sub")
        self.scope = data.get("scope")
        self.iat = data.get("iat")
        self.exp = data.get("exp")
        self.sig = data.get("sig")

    @classmethod
    def create(
        cls,
        issuer_wallet: Wallet,
        subject_did: str,
        scope: Any,
        exp: int,
        iat: Optional[int] = None,
    ) -> "Capability":
        if iat is None:
            import time

            iat = int(time.time())

        cap_data = {
            "v": "1",
            "iss": issuer_wallet.to_did(),
            "sub": subject_did,
            "scope": scope,
            "iat": iat,
            "exp": exp,
        }

        canon = canonical_json_bytes(cap_data)
        sig = issuer_wallet.sign(canon)
        cap_data["sig"] = base64url_encode(sig)

        return cls(cap_data)

    def verify(self, issuer_public_key: bytes) -> bool:
        if not self.sig:
            return False

        # Verify expiry
        import time

        if self.exp is None or self.exp < int(time.time()):
            return False

        # Get content without signature
        content = {k: v for k, v in self.data.items() if k != "sig"}
        canon = canonical_json_bytes(content)
        sig_bytes = base64url_decode(self.sig)

        return Wallet.verify(canon, sig_bytes, issuer_public_key)

    def authorize(self, tool: str, action: str) -> bool:
        """Simple scope check: scope is list of {tool, actions}"""
        if not isinstance(self.scope, list):
            return False

        for s in self.scope:
            if s.get("tool") == tool:
                if action in s.get("actions", []):
                    return True
        return False
