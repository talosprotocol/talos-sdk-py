"""Reference-style A2A v1 fixture server for local interoperability smoke tests."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local A2A v1 reference fixture server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind")
    parser.add_argument("--port", default=8011, type=int, help="Port to bind")
    parser.add_argument("--api-token", default="sdk-token", help="Bearer token required for RPC")
    return parser.parse_args()


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _task(task_id: str, context_id: str, text: str) -> dict[str, Any]:
    return {
        "id": task_id,
        "contextId": context_id,
        "status": {
            "state": "TASK_STATE_COMPLETED",
            "timestamp": _utc_timestamp(),
        },
        "artifacts": [
            {
                "artifactId": f"artifact-{task_id}",
                "parts": [{"text": text}],
            }
        ],
    }


class ReferenceA2AServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], api_token: str | None) -> None:
        super().__init__(server_address, ReferenceA2AHandler)
        self.api_token = api_token
        self.base_url = f"http://{server_address[0]}:{self.server_port}"
        self.tasks: dict[str, dict[str, Any]] = {
            "task-bootstrap": _task("task-bootstrap", "ctx-bootstrap", "bootstrap task"),
        }


class ReferenceA2AHandler(BaseHTTPRequestHandler):
    server: ReferenceA2AServer
    server_version = "ReferenceA2A/1.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/.well-known/agent-card.json":
            self._write_json(HTTPStatus.OK, self._agent_card())
            return
        if path == "/extendedAgentCard":
            if not self._authorized():
                self._write_json(HTTPStatus.UNAUTHORIZED, {"detail": "Unauthorized"})
                return
            self._write_json(HTTPStatus.OK, self._extended_agent_card())
            return
        self._write_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/rpc":
            self._write_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return
        if not self._authorized():
            self._write_json(HTTPStatus.UNAUTHORIZED, {"detail": "Unauthorized"})
            return

        payload = self._read_json()
        request_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") if isinstance(payload.get("params"), dict) else {}

        if method == "GetExtendedAgentCard":
            self._write_json(
                HTTPStatus.OK,
                {"jsonrpc": "2.0", "id": request_id, "result": self._extended_agent_card()},
            )
            return

        if method == "ListTasks":
            tasks = list(self.server.tasks.values())
            result = {
                "tasks": tasks,
                "pageSize": int(params.get("pageSize", 50) or 50),
                "totalSize": len(tasks),
            }
            self._write_json(HTTPStatus.OK, {"jsonrpc": "2.0", "id": request_id, "result": result})
            return

        if method == "SendMessage":
            message = params.get("message") if isinstance(params.get("message"), dict) else {}
            task_id = str(message.get("taskId") or f"task-{len(self.server.tasks) + 1}")
            context_id = str(message.get("contextId") or f"ctx-{task_id}")
            text = self._message_text(message)
            response_text = f"reference echo: {text}" if text else "reference echo"
            task = _task(task_id, context_id, response_text)
            self.server.tasks[task_id] = task
            result = {
                "task": task,
                "message": {
                    "messageId": f"agent-{task_id}",
                    "role": "agent",
                    "parts": [{"text": response_text}],
                    "taskId": task_id,
                    "contextId": context_id,
                },
            }
            self._write_json(HTTPStatus.OK, {"jsonrpc": "2.0", "id": request_id, "result": result})
            return

        if method == "SendStreamingMessage":
            message = params.get("message") if isinstance(params.get("message"), dict) else {}
            task_id = str(message.get("taskId") or f"task-{len(self.server.tasks) + 1}")
            context_id = str(message.get("contextId") or f"ctx-{task_id}")
            text = self._message_text(message)
            response_text = f"reference echo: {text}" if text else "reference echo"
            task = _task(task_id, context_id, response_text)
            self.server.tasks[task_id] = task
            self._write_sse(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "task": {
                                "id": task_id,
                                "contextId": context_id,
                                "status": {
                                    "state": "TASK_STATE_WORKING",
                                    "timestamp": _utc_timestamp(),
                                },
                            }
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "statusUpdate": {
                                "taskId": task_id,
                                "contextId": context_id,
                                "status": {
                                    "state": "TASK_STATE_COMPLETED",
                                    "timestamp": _utc_timestamp(),
                                },
                                "metadata": {"final": True},
                            }
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "message": {
                                "messageId": f"agent-{task_id}",
                                "role": "agent",
                                "parts": [{"text": response_text}],
                                "taskId": task_id,
                                "contextId": context_id,
                            }
                        },
                    },
                ]
            )
            return

        if method == "GetTask":
            task_id = str(params.get("id") or "")
            task = self.server.tasks.get(task_id)
            if task is None:
                self._write_json(
                    HTTPStatus.OK,
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {"code": -32001, "message": "Task not found"},
                    },
                )
                return
            self._write_json(HTTPStatus.OK, {"jsonrpc": "2.0", "id": request_id, "result": task})
            return

        if method == "SubscribeToTask":
            task_id = str(params.get("id") or "")
            task = self.server.tasks.get(task_id)
            if task is None:
                self._write_sse(
                    [
                        {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32001, "message": "Task not found"},
                        }
                    ]
                )
                return
            self._write_sse(
                [
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "task": {
                                "id": task["id"],
                                "contextId": task["contextId"],
                                "status": {
                                    "state": "TASK_STATE_WORKING",
                                    "timestamp": _utc_timestamp(),
                                },
                            }
                        },
                    },
                    {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "statusUpdate": {
                                "taskId": task["id"],
                                "contextId": task["contextId"],
                                "status": task["status"],
                                "metadata": {"final": True},
                            }
                        },
                    },
                ]
            )
            return

        self._write_json(
            HTTPStatus.OK,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            },
        )

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def _agent_card(self) -> dict[str, Any]:
        return {
            "name": "Reference Interop Agent",
            "description": "Canonical A2A v1 fixture server",
            "version": "1.0.0",
            "provider": {"organization": "Talos Protocol"},
            "documentationUrl": "https://a2a-protocol.org/latest/",
            "supportedInterfaces": [
                {
                    "url": f"{self.server.base_url}/rpc",
                    "protocolBinding": "JSONRPC",
                    "protocolVersion": "1.0",
                }
            ],
            "capabilities": {
                "streaming": True,
                "pushNotifications": False,
                "extendedAgentCard": True,
                "extensions": [],
            },
            "securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}},
            "securityRequirements": [{"bearerAuth": []}],
        }

    def _extended_agent_card(self) -> dict[str, Any]:
        payload = self._agent_card()
        payload["skills"] = [
            {
                "id": "reference-echo",
                "name": "Reference Echo",
                "description": "Echoes back the submitted text via canonical A2A v1 RPC.",
            }
        ]
        return payload

    def _authorized(self) -> bool:
        token = self.server.api_token
        if not token:
            return True
        return self.headers.get("Authorization") == f"Bearer {token}"

    def _read_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        body = self.rfile.read(length)
        if not body:
            return {}
        payload = json.loads(body.decode("utf-8"))
        return payload if isinstance(payload, dict) else {}

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _write_sse(self, payloads: list[dict[str, Any]]) -> None:
        body = "".join(f"data: {json.dumps(item)}\n\n" for item in payloads).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _message_text(message: dict[str, Any]) -> str:
        parts = message.get("parts")
        if not isinstance(parts, list) or not parts:
            return ""
        first = parts[0]
        if not isinstance(first, dict):
            return ""
        text = first.get("text")
        return str(text) if isinstance(text, str) else ""


def main() -> int:
    args = parse_args()
    server = ReferenceA2AServer((args.host, args.port), args.api_token)
    print(f"Serving reference A2A v1 fixture on {server.base_url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover - manual shutdown
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
