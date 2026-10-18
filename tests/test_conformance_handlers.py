"""Regression coverage for JSON input handled by the conformance runner."""

import json
from pathlib import Path

import pytest

from talos_sdk.conformance.runner import run_conformance


@pytest.mark.parametrize(
    ("canonical", "expected_success"),
    [("{\"a\":1,\"z\":2}", True), ("{\"a\":9,\"z\":2}", False)],
    ids=["valid-canonical-result", "incorrect-canonical-result"],
)
def test_conformance_checks_pretty_printed_json(
    tmp_path: Path, canonical: str, expected_success: bool
) -> None:
    vector_path = tmp_path / "canonical_json.json"
    vector_path.write_text(
        json.dumps(
            {
                "inputs": {"pretty_printed": "{\n  \"z\": 2,\n  \"a\": 1\n}"},
                "expected": {"canonical": canonical},
            }
        ),
        encoding="utf-8",
    )

    assert run_conformance(str(vector_path)) is expected_success
