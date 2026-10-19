"""Regression coverage for optional whitespace in SSE data fields."""

import json
from collections.abc import Iterator
from typing import Any

import pytest

from talos_sdk import A2AJsonRpcClient, A2AJsonRpcError


class _StreamResponse:
    def __init__(self, lines: list[bytes | str]) -> None:
        self.lines = lines
        self.closed = False

    def raise_for_status(self) -> None:
        pass

    def iter_lines(self) -> Iterator[bytes | str]:
        return iter(self.lines)

    def close(self) -> None:
        self.closed = True


class _HttpClient:
    def __init__(self, response: _StreamResponse) -> None:
        self.response = response

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        stream: bool = False,
        timeout: int = 30,
    ) -> _StreamResponse:
        return self.response


@pytest.mark.parametrize("prefix", ["data: ", "data:"], ids=["space", "no-space"])
@pytest.mark.parametrize("as_bytes", [False, True], ids=["text", "bytes"])
def test_stream_accepts_optional_space_after_data_colon(
    prefix: str, as_bytes: bool
) -> None:
    event = prefix + '{"jsonrpc":"2.0","id":"evt-1","result":{"index":1}}'
    lines: list[bytes | str] = [event.encode() if as_bytes else event, b""]
    response = _StreamResponse(lines)
    client = A2AJsonRpcClient("http://testserver", http=_HttpClient(response))

    assert list(client.subscribe_to_task("task-1")) == [{"index": 1}]
    assert response.closed


@pytest.mark.parametrize("prefix", ["data: ", "data:"], ids=["space", "no-space"])
@pytest.mark.parametrize("as_bytes", [False, True], ids=["text", "bytes"])
def test_stream_preserves_jsonrpc_errors_with_optional_data_space(
    prefix: str, as_bytes: bool
) -> None:
    event = (
        prefix + '{"jsonrpc":"2.0","id":"evt-1",'
        '"error":{"code":-32001,"message":"Task not found"}}'
    )
    lines: list[bytes | str] = [event.encode() if as_bytes else event, b""]
    response = _StreamResponse(lines)
    client = A2AJsonRpcClient("http://testserver", http=_HttpClient(response))

    with pytest.raises(A2AJsonRpcError) as error:
        list(client.subscribe_to_task("task-1"))

    assert error.value.code == -32001
    assert response.closed


@pytest.mark.parametrize("empty_data", ["data:", "data: ", "data:\t"])
@pytest.mark.parametrize("as_bytes", [False, True], ids=["text", "bytes"])
def test_stream_skips_empty_data_before_valid_event(
    empty_data: str, as_bytes: bool
) -> None:
    event = 'data:{"jsonrpc":"2.0","id":"evt-1","result":{"index":1}}'
    text_lines = [empty_data, "", event, ""]
    lines: list[bytes | str] = [
        line.encode() if as_bytes else line for line in text_lines
    ]
    response = _StreamResponse(lines)
    client = A2AJsonRpcClient("http://testserver", http=_HttpClient(response))

    assert list(client.subscribe_to_task("task-1")) == [{"index": 1}]
    assert response.closed


@pytest.mark.parametrize("as_bytes", [False, True], ids=["text", "bytes"])
def test_stream_preserves_nonempty_invalid_json_error(as_bytes: bool) -> None:
    event = "data:{invalid json}"
    lines: list[bytes | str] = [event.encode() if as_bytes else event, b""]
    response = _StreamResponse(lines)
    client = A2AJsonRpcClient("http://testserver", http=_HttpClient(response))

    with pytest.raises(json.JSONDecodeError):
        list(client.subscribe_to_task("task-1"))

    assert response.closed
