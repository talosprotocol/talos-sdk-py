from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from talos_sdk import (
    A2AJsonRpcClient,
    A2AJsonRpcError,
    TALOS_ATTESTATION_EXTENSION,
    TALOS_COMPAT_JSONRPC_EXTENSION,
    TALOS_SECURE_CHANNELS_EXTENSION,
)
from talos_sdk import a2a_v1 as a2a_v1_module
import json


def _app() -> FastAPI:
    app = FastAPI()

    @app.get("/.well-known/agent-card.json")
    def get_agent_card():
        return {
            "name": "Interop Agent",
            "description": "Test A2A agent",
            "version": "1.0.0",
            "provider": {"organization": "Talos Protocol"},
            "documentationUrl": "https://talosprotocol.com/docs",
            "supportedInterfaces": [
                {
                    "url": "http://testserver/rpc",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "capabilities": {
                "streaming": True,
                "pushNotifications": True,
                "extendedAgentCard": True,
                "extensions": [
                    {"uri": TALOS_ATTESTATION_EXTENSION},
                    {"uri": TALOS_SECURE_CHANNELS_EXTENSION},
                    {"uri": TALOS_COMPAT_JSONRPC_EXTENSION},
                ],
            },
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "securityRequirements": [{"bearerAuth": []}],
        }

    @app.get("/extendedAgentCard")
    def get_extended_agent_card(authorization: str | None = Header(default=None)):
        if authorization != "Bearer sdk-token":
            raise HTTPException(status_code=401, detail="Unauthorized")
        return {
            "name": "Interop Agent",
            "description": "Extended card",
            "version": "1.0.0",
            "provider": {"organization": "Talos Protocol"},
            "documentationUrl": "https://talosprotocol.com/docs",
            "supportedInterfaces": [
                {
                    "url": "http://testserver/rpc",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "capabilities": {
                "streaming": True,
                "pushNotifications": True,
                "extendedAgentCard": True,
                "extensions": [
                    {"uri": TALOS_ATTESTATION_EXTENSION},
                    {"uri": TALOS_SECURE_CHANNELS_EXTENSION},
                ],
            },
            "skills": [{"id": "interop", "name": "Interop", "description": "Test"}],
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "securityRequirements": [{"bearerAuth": []}],
        }

    @app.post("/rpc")
    def rpc(payload: dict):
        method = payload["method"]
        if method == "GetExtendedAgentCard":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {"name": "Interop Agent", "capabilities": {"extendedAgentCard": True}},
            }
        if method == "SendMessage":
            message = payload["params"]["message"]
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "task": {
                        "id": message.get("taskId", "task-1"),
                        "contextId": message.get("contextId", "ctx-1"),
                        "status": {
                            "state": "TASK_STATE_COMPLETED",
                            "timestamp": "2026-03-13T00:00:00Z",
                        },
                    },
                    "message": {
                        "messageId": "agent-1",
                        "role": "agent",
                        "parts": [{"text": "hello"}],
                    },
                },
            }
        if method == "ListTasks":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "tasks": [
                        {
                            "id": "task-1",
                            "contextId": "ctx-1",
                            "status": {
                                "state": "TASK_STATE_COMPLETED",
                                "timestamp": "2026-03-13T00:00:00Z",
                            },
                        }
                    ],
                    "pageSize": payload["params"].get("pageSize", 50),
                    "totalSize": 1,
                },
            }
        if method == "SubscribeToTask":
            async def event_stream():
                payloads = [
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {
                            "task": {
                                "id": "task-1",
                                "contextId": "ctx-1",
                                "status": {
                                    "state": "TASK_STATE_WORKING",
                                    "timestamp": "2026-03-13T00:00:00Z",
                                },
                            }
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {
                            "statusUpdate": {
                                "taskId": "task-1",
                                "contextId": "ctx-1",
                                "status": {
                                    "state": "TASK_STATE_COMPLETED",
                                    "timestamp": "2026-03-13T00:00:01Z",
                                },
                                "metadata": {"final": True},
                            }
                        },
                    },
                ]
                for item in payloads:
                    yield f"data: {json.dumps(item)}\n\n"

            return StreamingResponse(event_stream(), media_type="text/event-stream")
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32601, "message": "Method not found"},
        }

    return app


def _v03_app() -> FastAPI:
    app = FastAPI()

    @app.get("/.well-known/agent-card.json")
    def get_agent_card():
        return {
            "name": "Legacy Interop Agent",
            "description": "Test v0.3.0 A2A agent",
            "protocolVersion": "0.3.0",
            "preferredTransport": "JSONRPC",
            "url": "http://testserver/",
            "supportsAuthenticatedExtendedCard": True,
            "capabilities": {
                "extensions": [
                    {"uri": TALOS_COMPAT_JSONRPC_EXTENSION},
                ]
            },
        }

    @app.post("/")
    def rpc(payload: dict):
        method = payload["method"]
        if method == "agent/getAuthenticatedExtendedCard":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "name": "Legacy Interop Agent",
                    "protocolVersion": "0.3.0",
                    "preferredTransport": "JSONRPC",
                    "url": "http://testserver/",
                },
            }
        if method == "message/send":
            message = payload["params"]["message"]
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "task": {
                        "id": message.get("taskId", "legacy-task-1"),
                        "contextId": message.get("contextId", "legacy-ctx-1"),
                    },
                    "message": {
                        "messageId": "agent-legacy-1",
                        "role": "agent",
                        "parts": message["parts"],
                    },
                },
            }
        if method == "tasks/list":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "tasks": [{"id": "legacy-task-1"}],
                    "pageSize": payload["params"].get("pageSize", 50),
                    "totalSize": 1,
                },
            }
        if method == "tasks/get":
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "id": payload["params"]["id"],
                    "status": {
                        "state": "TASK_STATE_COMPLETED",
                        "timestamp": "2026-03-13T00:00:00Z",
                    },
                },
            }
        if method == "message/stream":
            async def stream_events():
                payloads = [
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"delta": "legacy-one"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"delta": "legacy-two"},
                    },
                ]
                for item in payloads:
                    yield f"data: {json.dumps(item)}\n\n"

            return StreamingResponse(stream_events(), media_type="text/event-stream")
        if method == "tasks/resubscribe":
            async def subscribe_events():
                payloads = [
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"task": {"id": payload["params"]["id"]}},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"statusUpdate": {"taskId": payload["params"]["id"]}},
                    },
                ]
                for item in payloads:
                    yield f"data: {json.dumps(item)}\n\n"

            return StreamingResponse(subscribe_events(), media_type="text/event-stream")
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32601, "message": "Method not found"},
        }

    return app


def _java_hybrid_app() -> FastAPI:
    app = FastAPI()

    @app.get("/.well-known/agent-card.json")
    def get_agent_card():
        return {
            "name": "Java Hybrid Interop Agent",
            "description": "Test hybrid Java A2A agent",
            "version": "1.0.0",
            "supportedInterfaces": [
                {
                    "url": "http://testserver/",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "capabilities": {
                "streaming": True,
                "pushNotifications": True,
                "extendedAgentCard": False,
            },
        }

    @app.post("/")
    def rpc(payload: dict):
        method = payload["method"]
        if method == "SendMessage":
            message = payload["params"]["message"]
            if message["role"] != "ROLE_USER":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "error": {
                        "code": -32602,
                        "message": f"Invalid request content: {message['role']}",
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": payload["id"],
                "result": {
                    "message": {
                        "messageId": "java-agent-1",
                        "role": "ROLE_AGENT",
                        "parts": [{"text": "hello from java"}],
                    }
                },
            }
        if method == "SendStreamingMessage":
            async def stream_events():
                payloads = [
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"delta": "java-one"},
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": payload["id"],
                        "result": {"delta": "java-two"},
                    },
                ]
                for item in payloads:
                    yield f"data: {json.dumps(item)}\n\n"

            return StreamingResponse(stream_events(), media_type="text/event-stream")
        return {
            "jsonrpc": "2.0",
            "id": payload["id"],
            "error": {"code": -32601, "message": "Method not found"},
        }

    return app


def test_a2a_v1_client_discovers_cards_and_rpc_methods():
    client = TestClient(_app())
    sdk = A2AJsonRpcClient("http://testserver", api_token="sdk-token", http=client)

    card = sdk.get_agent_card()
    extended = sdk.get_extended_agent_card()
    rpc_extended = sdk.get_authenticated_extended_agent_card()
    send_result = sdk.send_message("hello")
    listed = sdk.list_tasks(page_size=5)

    assert card["supportedInterfaces"][0]["protocolVersion"] == "1.0"
    assert sdk.supported_interfaces(card)[0]["protocolBinding"] == "JSONRPC"
    assert sdk.supports_talos_attestation(card) is True
    assert sdk.supports_talos_secure_channels(card) is True
    assert sdk.supports_talos_compat_jsonrpc(card) is True
    assert sdk.supports_extension("https://example.com/extensions/unknown", card) is False
    assert extended["capabilities"]["extendedAgentCard"] is True
    assert rpc_extended["capabilities"]["extendedAgentCard"] is True
    assert send_result["task"]["status"]["state"] == "TASK_STATE_COMPLETED"
    assert send_result["message"]["parts"][0]["text"] == "hello"
    assert listed["totalSize"] == 1


def test_a2a_v1_client_streams_sse_results():
    client = TestClient(_app())
    sdk = A2AJsonRpcClient("http://testserver", api_token="sdk-token", http=client)

    results = list(sdk.subscribe_to_task("task-1"))

    assert results[0]["task"]["status"]["state"] == "TASK_STATE_WORKING"
    assert results[1]["statusUpdate"]["metadata"]["final"] is True


def test_a2a_v1_client_supports_upstream_v03_compat_profile():
    client = TestClient(_v03_app())
    sdk = A2AJsonRpcClient(
        "http://testserver",
        api_token="sdk-token",
        http=client,
        interop_profile="upstream_v0_3",
    )

    card = sdk.get_agent_card()
    interfaces = sdk.supported_interfaces(card)
    extended = sdk.get_extended_agent_card()
    sent = sdk.send_message("legacy hello")
    listed = sdk.list_tasks(page_size=5)
    task = sdk.get_task("legacy-task-1")
    streamed = list(sdk.send_streaming_message("legacy hello"))
    subscribed = list(sdk.subscribe_to_task("legacy-task-1"))

    assert interfaces == [
        {
            "url": "http://testserver/",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "0.3.0",
        }
    ]
    assert extended["protocolVersion"] == "0.3.0"
    assert sent["message"]["parts"] == [{"kind": "text", "text": "legacy hello"}]
    assert listed["totalSize"] == 1
    assert task["id"] == "legacy-task-1"
    assert streamed == [{"delta": "legacy-one"}, {"delta": "legacy-two"}]
    assert subscribed[1]["statusUpdate"]["taskId"] == "legacy-task-1"


def test_a2a_v1_client_supports_upstream_java_hybrid_profile():
    client = TestClient(_java_hybrid_app())
    sdk = A2AJsonRpcClient(
        "http://testserver",
        api_token="sdk-token",
        http=client,
        interop_profile="upstream_java_hybrid",
    )

    card = sdk.get_agent_card()
    interfaces = sdk.supported_interfaces(card)
    sent = sdk.send_message("java hello")
    streamed = list(sdk.send_streaming_message("java hello"))

    assert interfaces == [
        {
            "url": "http://testserver/",
            "protocolBinding": "JSONRPC",
            "protocolVersion": "1.0",
        }
    ]
    assert sent["message"]["parts"] == [{"text": "hello from java"}]
    assert streamed == [{"delta": "java-one"}, {"delta": "java-two"}]


def test_a2a_v1_client_raises_jsonrpc_error():
    client = TestClient(_app())
    sdk = A2AJsonRpcClient("http://testserver", api_token="sdk-token", http=client)

    try:
        sdk.rpc("unknown/method")
    except A2AJsonRpcError as exc:
        assert exc.code == -32601
    else:  # pragma: no cover
        raise AssertionError("Expected A2AJsonRpcError")


def test_a2a_v1_client_falls_back_when_requests_is_unavailable(monkeypatch):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeStdlibHttpClient:
        def get(self, url, *, headers, timeout=30):
            assert url.endswith("/.well-known/agent-card.json")
            return FakeResponse({"name": "Fallback Agent"})

    monkeypatch.setattr(a2a_v1_module, "_requests", None)
    monkeypatch.setattr(a2a_v1_module, "_StdlibHttpClient", FakeStdlibHttpClient)

    sdk = A2AJsonRpcClient("http://testserver")

    assert isinstance(sdk._http, FakeStdlibHttpClient)
    assert sdk.get_agent_card()["name"] == "Fallback Agent"


def test_a2a_v1_client_streams_with_requests_style_http_client():
    class FakeStreamResponse:
        def __init__(self):
            self.closed = False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield b'data: {"jsonrpc":"2.0","id":"evt-1","result":{"index":1}}'
            yield b""
            yield b'data: {"jsonrpc":"2.0","id":"evt-2","result":{"index":2}}'

        def close(self):
            self.closed = True

    class FakeRequestsLikeClient:
        stream = False

        def post(self, url, *, json, headers, stream=False, timeout=30):
            assert url.endswith("/rpc")
            assert json["method"] == "SubscribeToTask"
            assert headers["Authorization"] == "Bearer sdk-token"
            assert stream is True
            assert timeout == 30
            return FakeStreamResponse()

    sdk = A2AJsonRpcClient(
        "http://testserver",
        api_token="sdk-token",
        http=FakeRequestsLikeClient(),
    )

    results = list(sdk.subscribe_to_task("task-1"))

    assert results == [{"index": 1}, {"index": 2}]


def test_a2a_v1_client_upstream_v03_profile_normalizes_localhost_rpc_url():
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeHttpClient:
        def __init__(self):
            self.post_urls = []

        def get(self, url, *, headers, timeout=30):
            assert url == "http://127.0.0.1:9999/.well-known/agent-card.json"
            return FakeResponse(
                {
                    "protocolVersion": "0.3.0",
                    "preferredTransport": "JSONRPC",
                    "url": "http://localhost:9999/",
                }
            )

        def post(self, url, *, json, headers, timeout=30):
            self.post_urls.append(url)
            return FakeResponse({"jsonrpc": "2.0", "id": json["id"], "result": {"ok": True}})

    http = FakeHttpClient()
    sdk = A2AJsonRpcClient(
        "http://127.0.0.1:9999",
        http=http,
        interop_profile="upstream_v0_3",
    )

    assert sdk.get_authenticated_extended_agent_card()["ok"] is True
    assert http.post_urls == ["http://127.0.0.1:9999/"]


def test_a2a_v1_client_upstream_java_hybrid_profile_normalizes_localhost_rpc_url():
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    class FakeHttpClient:
        def __init__(self):
            self.post_urls = []

        def get(self, url, *, headers, timeout=30):
            assert url == "http://127.0.0.1:9999/.well-known/agent-card.json"
            return FakeResponse(
                {
                    "supportedInterfaces": [
                        {
                            "url": "http://localhost:9999/",
                            "protocolBinding": "JSONRPC",
                            "protocolVersion": "1.0",
                        }
                    ],
                    "capabilities": {"extendedAgentCard": False},
                }
            )

        def post(self, url, *, json, headers, timeout=30):
            self.post_urls.append(url)
            return FakeResponse({"jsonrpc": "2.0", "id": json["id"], "result": {"ok": True}})

    http = FakeHttpClient()
    sdk = A2AJsonRpcClient(
        "http://127.0.0.1:9999",
        http=http,
        interop_profile="upstream_java_hybrid",
    )

    assert sdk.send_message("java hello")["ok"] is True
    assert http.post_urls == ["http://127.0.0.1:9999/"]
