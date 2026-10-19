"""Capability management for Talos SDK."""

import time
from datetime import datetime, timezone
from typing import Any, Optional, Union

from .canonical import canonical_json_bytes
from .crypto import b64u_decode as base64url_decode
from .crypto import b64u_encode as base64url_encode
from .wallet import Wallet


class Capability:
    def __init__(self, data: dict[str, Any]):
        self.data = data
        self.version = data.get("version", data.get("v", "1.0"))
        self.issuer = data.get("issuer", data.get("iss"))
        self.subject = data.get("subject", data.get("sub"))
        self.scope = data.get("scope")
        self.issued_at = data.get("issued_at", data.get("iat"))
        self.expires_at = data.get("expires_at", data.get("exp"))
        self.signature = data.get("signature", data.get("sig"))

    # --- Backward Compatibility Aliases (Deprecated) ---
    @property
    def v(self): return self.version
    @property
    def iss(self): return self.issuer
    @property
    def sub(self): return self.subject
    @property
    def iat(self): return self.issued_at
    @property
    def exp(self): return self.expires_at
    
    @property
    def sig(self): return self.signature
    @sig.setter
    def sig(self, value): self.signature = value

    @classmethod
    def create(
        cls,
        issuer_wallet: Wallet,
        subject_did: str,
        scope: Any,
        exp: Union[int, str],
        iat: Optional[Union[int, str]] = None,
    ) -> "Capability":
        """
        Create and sign a new capability.
        
        Args:
            issuer_wallet: Wallet that will sign the capability.
            subject_did: DID of the subject receiving the capability.
            scope: Access scope (string or list of dicts).
            exp: Expiration (Unix seconds or ISO string).
            iat: Issuance time (Unix seconds or ISO string).
        """
        if iat is None:
            iat = int(time.time())

        # Canonicalize timestamps to ISO strings as per Protocol v1.0
        issued_at_iso = cls._to_iso(iat)
        expires_at_iso = cls._to_iso(exp)

        cap_data = {
            "version": "1",
            "issuer": issuer_wallet.to_did(),
            "subject": subject_did,
            "scope": scope,
            "issued_at": issued_at_iso,
            "expires_at": expires_at_iso,
        }

        canon = canonical_json_bytes(cap_data)
        sig = issuer_wallet.sign(canon)
        cap_data["signature"] = base64url_encode(sig)

        return cls(cap_data)

    def verify(self, issuer_public_key: bytes, now: Optional[Union[int, float]] = None) -> bool:
        if not self.signature:
            return False

        # Verify expiry
        current_time = now if now is not None else time.time()
        
        try:
            exp_ts = self._to_timestamp(self.expires_at)
            if exp_ts < current_time:
                return False
        except (ValueError, TypeError):
            return False

        # Get content without signature for verification
        # We must support both 'signature' and 'sig' in the source data during transition
        content = {k: v for k, v in self.data.items() if k not in ("signature", "sig")}
        canon = canonical_json_bytes(content)
        sig_bytes = base64url_decode(self.signature)

        return Wallet.verify(canon, sig_bytes, issuer_public_key)

    def authorize(self, tool: str, action: str) -> bool:
        """Authorize a tool:action pair."""
        if isinstance(self.scope, list):
            for s in self.scope:
                if s.get("tool") == tool and action in s.get("actions", []):
                    return True
        
        if isinstance(self.scope, str):
            target = f"tool:{tool}"
            if self.scope == target:
                return True
            if self.scope.startswith(f"{target}/method:{action}"):
                return True
            if self.scope.startswith(f"{target}/"):
                return True
                
        return False

    @staticmethod
    def _to_iso(val: Union[int, str]) -> str:
        if isinstance(val, str):
            return val
        return datetime.fromtimestamp(val, tz=timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _to_timestamp(val: Union[int, str, None]) -> float:
        if val is None:
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        # Parse ISO string
        s = val.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
