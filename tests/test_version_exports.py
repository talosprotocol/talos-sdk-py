import base64
import hashlib
import json
from pathlib import Path

from talos_sdk import CONTRACT_MANIFEST_HASH, SDK_VERSION, SUPPORTED_PROTOCOL_RANGE


def _expected_contract_manifest_hash() -> str:
    manifest_path = (
        Path(__file__).resolve().parents[3]
        / "contracts"
        / "sdk"
        / "contract_manifest.json"
    )
    payload = json.loads(manifest_path.read_text())
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).digest()
    return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")


def test_sdk_version_exports_are_present():
    assert SDK_VERSION == "1.0.0"
    assert SUPPORTED_PROTOCOL_RANGE == ("1.0", "1.x")


def test_contract_manifest_hash_matches_canonical_contract_manifest():
    assert CONTRACT_MANIFEST_HASH == _expected_contract_manifest_hash()
    assert ":" not in CONTRACT_MANIFEST_HASH
