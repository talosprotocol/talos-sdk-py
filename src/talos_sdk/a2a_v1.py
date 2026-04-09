"""Minimal standards-first A2A v1 JSON-RPC client."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Literal
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib.parse import urljoin, urlsplit, urlunsplit

try:
    import requests as _requests
except ModuleNotFoundError:  # pragma: no cover - exercised in source-tree live smoke
    _requests = None


TALOS_ATTESTATION_EXTENSION = "https://talosprotocol.com/extensions/a2a/attestation/v1"
TALOS_SECURE_CHANNELS_EXTENSION = "https://talosprotocol.com/extensions/a2a/secure-channels/v1"
TALOS_COMPAT_JSONRPC_EXTENSION = "https://talosprotocol.com/extensions/a2a/compat-jsonrpc/v0"

A2AInteropProfile = Literal["canonical", "upstream_v0_3", "upstream_java_hybrid"]

_UPSTREAM_V0_3_METHOD_ALIASES = {
    "GetExtendedAgentCard": "agent/getAuthenticatedExtendedCard",
    "SendMessage": "message/send",
    "SendStreamingMessage": "message/stream",
    "GetTask": "tasks/get",
    "CancelTask": "tasks/cancel",
    "ListTasks": "tasks/list",
    "SubscribeToTask": "tasks/resubscribe",
    "CreateTaskPushNotificationConfig": "tasks/pushNotificationConfig/set",
    "GetTaskPushNotificationConfig": "tasks/pushNotificationConfig/get",
    "ListTaskPushNotificationConfigs": "tasks/pushNotificationConfig/list",
    "DeleteTaskPushNotificationConfig": "tasks/pushNotificationConfig/delete",
}


class A2AJsonRpcError(RuntimeError):
    """Raised when an A2A JSON-RPC response contains an error."""

    def __init__(self, code: int, message: str, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.data = data or {}


class _HttpStatusError(RuntimeError):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"HTTP {status_code}: {payload}")


class _StdlibResponse:
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self._body = body

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            try:
                payload = self.json()
            except Exception:
                payload = self._body.decode("utf-8", errors="replace")
            raise _HttpStatusError(self.status_code, payload)

    def json(self) -> Any:
        return json.loads(self._body.decode("utf-8"))


class _StdlibStreamResponse:
    def __init__(self, status_code: int, response: Any):
        self.status_code = status_code
        self._response = response

    def __enter__(self) -> _StdlibStreamResponse:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._response.close()

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            body = self._response.read()
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = body.decode("utf-8", errors="replace")
            raise _HttpStatusError(self.status_code, payload)

    def iter_lines(self) -> Iterator[bytes]:
        while True:
            line = self._response.readline()
            if not line:
                break
            yield line.rstrip(b"\r\n")


class _StdlibHttpClient:
    def get(self, url: str, *, headers: dict[str, str], timeout: int = 30) -> _StdlibResponse:
        request = urllib_request.Request(url, headers=headers, method="GET")
        return self._execute(request, timeout)

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: int = 30,
    ) -> _StdlibResponse:
        request = urllib_request.Request(
            url,
            data=self._json_bytes(json),
            headers=headers,
            method="POST",
        )
        return self._execute(request, timeout)

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
        timeout: int = 30,
    ) -> _StdlibStreamResponse:
        request = urllib_request.Request(
            url,
            data=self._json_bytes(json),
            headers=headers,
            method=method,
        )
        try:
            response = urllib_request.urlopen(request, timeout=timeout)
        except urllib_error.HTTPError as exc:
            response = exc
        return _StdlibStreamResponse(getattr(response, "status", response.getcode()), response)

    def _execute(self, request: urllib_request.Request, timeout: int) -> _StdlibResponse:
        try:
            response = urllib_request.urlopen(request, timeout=timeout)
        except urllib_error.HTTPError as exc:
            response = exc
        body = response.read()
        return _StdlibResponse(getattr(response, "status", response.getcode()), body)

    @staticmethod
    def _json_bytes(payload: dict[str, Any]) -> bytes:
        return json.dumps(payload).encode("utf-8")


@dataclass
class A2AJsonRpcClient:
    """Tiny JSON-RPC client for A2A v1-compatible agents."""

    base_url: str
    api_token: str | None = None
    http: Any | None = None
    interop_profile: A2AInteropProfile = "canonical"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if self.interop_profile not in {"canonical", "upstream_v0_3", "upstream_java_hybrid"}:
            raise ValueError(f"unsupported interop profile: {self.interop_profile}")
        if self.http is not None:
            self._http = self.http
        elif _requests is not None:
            self._http = _requests.Session()
        else:
            self._http = _StdlibHttpClient()
        self._agent_card_cache: dict[str, Any] | None = None

    def get_agent_card(self) -> dict[str, Any]:
        response = self._http.get(
            f"{self.base_url}/.well-known/agent-card.json",
            headers=self._headers(),
            **self._request_options(),
        )
        self._raise_for_status(response)
        payload = self._json(response)
        self._agent_card_cache = payload
        return payload

    def get_extended_agent_card(self) -> dict[str, Any]:
        if self._uses_upstream_v03_profile():
            return self.get_authenticated_extended_agent_card()
        response = self._http.get(
            f"{self.base_url}/extendedAgentCard",
            headers=self._headers(),
            **self._request_options(),
        )
        self._raise_for_status(response)
        return self._json(response)

    def get_authenticated_extended_agent_card(self) -> dict[str, Any]:
        return self.rpc("GetExtendedAgentCard")

    def supported_interfaces(self, card: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        payload = card or self.get_agent_card()
        interfaces = payload.get("supportedInterfaces")
        if isinstance(interfaces, list):
            return [item for item in interfaces if isinstance(item, dict)]
        compat_interface = self._compat_supported_interface(payload)
        if compat_interface is not None:
            return [compat_interface]
        return []

    def extension_uris(self, card: dict[str, Any] | None = None) -> list[str]:
        payload = card or self.get_agent_card()
        capabilities = payload.get("capabilities")
        if not isinstance(capabilities, dict):
            return []
        extensions = capabilities.get("extensions")
        if not isinstance(extensions, list):
            return []

        uris: list[str] = []
        for item in extensions:
            if not isinstance(item, dict):
                continue
            uri = item.get("uri")
            if isinstance(uri, str):
                uris.append(uri)
        return uris

    def supports_extension(self, uri: str, card: dict[str, Any] | None = None) -> bool:
        return uri in self.extension_uris(card)

    def supports_talos_secure_channels(self, card: dict[str, Any] | None = None) -> bool:
        return self.supports_extension(TALOS_SECURE_CHANNELS_EXTENSION, card)

    def supports_talos_attestation(self, card: dict[str, Any] | None = None) -> bool:
        return self.supports_extension(TALOS_ATTESTATION_EXTENSION, card)

    def supports_talos_compat_jsonrpc(self, card: dict[str, Any] | None = None) -> bool:
        return self.supports_extension(TALOS_COMPAT_JSONRPC_EXTENSION, card)

    def send_message(
        self,
        text: str,
        *,
        message_id: str | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        configuration: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "message": self._message(
                text=text,
                message_id=message_id,
                task_id=task_id,
                context_id=context_id,
                metadata=metadata,
            )
        }
        if configuration:
            params["configuration"] = configuration
        return self.rpc("SendMessage", params)

    def send_streaming_message(
        self,
        text: str,
        *,
        message_id: str | None = None,
        task_id: str | None = None,
        context_id: str | None = None,
        configuration: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {
            "message": self._message(
                text=text,
                message_id=message_id,
                task_id=task_id,
                context_id=context_id,
                metadata=metadata,
            )
        }
        if configuration:
            params["configuration"] = configuration
        return self.stream("SendStreamingMessage", params)

    def get_task(
        self,
        task_id: str,
        *,
        history_length: int | None = None,
        include_artifacts: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"id": task_id, "includeArtifacts": include_artifacts}
        if history_length is not None:
            params["historyLength"] = history_length
        return self.rpc("GetTask", params)

    def cancel_task(
        self,
        task_id: str,
        *,
        history_length: int | None = None,
        include_artifacts: bool = False,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"id": task_id, "includeArtifacts": include_artifacts}
        if history_length is not None:
            params["historyLength"] = history_length
        return self.rpc("CancelTask", params)

    def list_tasks(
        self,
        *,
        context_id: str | None = None,
        status: str | None = None,
        page_size: int | None = None,
        page_token: str | None = None,
        include_artifacts: bool = False,
        history_length: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"includeArtifacts": include_artifacts}
        if context_id is not None:
            params["contextId"] = context_id
        if status is not None:
            params["status"] = status
        if page_size is not None:
            params["pageSize"] = page_size
        if page_token is not None:
            params["pageToken"] = page_token
        if history_length is not None:
            params["historyLength"] = history_length
        return self.rpc("ListTasks", params)

    def subscribe_to_task(
        self,
        task_id: str,
        *,
        history_length: int | None = None,
        include_artifacts: bool = False,
    ) -> Iterator[dict[str, Any]]:
        params: dict[str, Any] = {"id": task_id, "includeArtifacts": include_artifacts}
        if history_length is not None:
            params["historyLength"] = history_length
        return self.stream("SubscribeToTask", params)

    def set_task_push_notification_config(
        self,
        task_id: str,
        *,
        url: str,
        token: str | None = None,
        authentication: dict[str, Any] | None = None,
        config_id: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "taskId": task_id,
            "id": config_id or self._new_id("push"),
            "url": url,
        }
        if token is not None:
            params["token"] = token
        if authentication is not None:
            params["authentication"] = authentication
        return self.rpc("CreateTaskPushNotificationConfig", params)

    def get_task_push_notification_config(self, task_id: str, config_id: str) -> dict[str, Any]:
        return self.rpc(
            "GetTaskPushNotificationConfig",
            {"taskId": task_id, "id": config_id},
        )

    def list_task_push_notification_configs(self, task_id: str) -> dict[str, Any]:
        return self.rpc("ListTaskPushNotificationConfigs", {"taskId": task_id})

    def delete_task_push_notification_config(self, task_id: str, config_id: str) -> dict[str, Any]:
        return self.rpc(
            "DeleteTaskPushNotificationConfig",
            {"taskId": task_id, "id": config_id},
        )

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._http.post(
            self._rpc_url(),
            json={
                "jsonrpc": "2.0",
                "id": self._new_id("rpc"),
                "method": self._rpc_method(method),
                "params": params or {},
            },
            headers=self._headers(),
            **self._request_options(),
        )
        self._raise_for_status(response)
        payload = self._json(response)
        return self._extract_result(payload)

    def stream(self, method: str, params: dict[str, Any] | None = None) -> Iterator[dict[str, Any]]:
        with self._open_stream_response(method, params) as response:
            self._raise_for_status(response)
            for line in response.iter_lines():
                if not line:
                    continue
                text = line.decode("utf-8") if isinstance(line, bytes) else str(line)
                if not text.startswith("data: "):
                    continue
                payload = json.loads(text[6:])
                yield self._extract_result(payload)

    def _message(
        self,
        *,
        text: str,
        message_id: str | None,
        task_id: str | None,
        context_id: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "messageId": message_id or self._new_id("msg"),
            "role": self._message_role(),
            "parts": [self._text_part(text)],
        }
        if task_id is not None:
            message["taskId"] = task_id
        if context_id is not None:
            message["contextId"] = context_id
        if metadata is not None:
            message["metadata"] = metadata
        return message

    def _extract_result(self, payload: dict[str, Any]) -> dict[str, Any]:
        error = payload.get("error")
        if isinstance(error, dict):
            raise A2AJsonRpcError(
                int(error.get("code", -32603)),
                str(error.get("message", "JSON-RPC error")),
                error.get("data") if isinstance(error.get("data"), dict) else None,
            )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError(f"Unexpected A2A response: {payload}")
        return result

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex}"

    def _raise_for_status(self, response: Any) -> None:
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()

    def _json(self, response: Any) -> dict[str, Any]:
        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError(f"Unexpected A2A response body: {payload}")
        return payload

    def _request_options(self) -> dict[str, Any]:
        module_name = type(self._http).__module__
        if module_name.startswith("starlette.testclient"):
            return {}
        return {"timeout": 30}

    def _uses_upstream_v03_profile(self) -> bool:
        return self.interop_profile == "upstream_v0_3"

    def _uses_upstream_java_hybrid_profile(self) -> bool:
        return self.interop_profile == "upstream_java_hybrid"

    def _rpc_method(self, method: str) -> str:
        if not self._uses_upstream_v03_profile():
            return method
        return _UPSTREAM_V0_3_METHOD_ALIASES.get(method, method)

    def _rpc_url(self) -> str:
        if self.interop_profile == "canonical":
            return f"{self.base_url}/rpc"
        card = self._agent_card_cache or self.get_agent_card()
        raw_url = self._profile_rpc_url(card)
        return self._normalize_localhost_url(urljoin(f"{self.base_url}/", raw_url))

    def _compat_supported_interface(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        if not self._uses_upstream_v03_profile():
            return None
        protocol_version = payload.get("protocolVersion")
        if not isinstance(protocol_version, str):
            return None
        protocol_binding = payload.get("preferredTransport")
        raw_url = payload.get("url") if isinstance(payload.get("url"), str) else self._rpc_url()
        return {
            "url": self._normalize_localhost_url(urljoin(f"{self.base_url}/", raw_url)),
            "protocolBinding": protocol_binding if isinstance(protocol_binding, str) else "JSONRPC",
            "protocolVersion": protocol_version,
        }

    def _text_part(self, text: str) -> dict[str, Any]:
        if self._uses_upstream_v03_profile():
            return {"kind": "text", "text": text}
        return {"text": text}

    def _message_role(self) -> str:
        if self._uses_upstream_java_hybrid_profile():
            return "ROLE_USER"
        return "user"

    def _profile_rpc_url(self, card: dict[str, Any]) -> str:
        if self._uses_upstream_java_hybrid_profile():
            interfaces = card.get("supportedInterfaces")
            if isinstance(interfaces, list):
                for item in interfaces:
                    if isinstance(item, dict) and isinstance(item.get("url"), str):
                        return item["url"]
        return card.get("url") if isinstance(card.get("url"), str) else "/"

    def _normalize_localhost_url(self, value: str) -> str:
        base = urlsplit(self.base_url)
        target = urlsplit(value)
        base_host = base.hostname
        target_host = target.hostname
        if not (
            isinstance(base_host, str)
            and isinstance(target_host, str)
            and self._is_local_alias(base_host)
            and self._is_local_alias(target_host)
            and base.port == target.port
        ):
            return value
        netloc = base_host
        if target.port is not None:
            netloc = f"{netloc}:{target.port}"
        return urlunsplit((target.scheme, netloc, target.path, target.query, target.fragment))

    @staticmethod
    def _is_local_alias(hostname: str) -> bool:
        return hostname in {"localhost", "127.0.0.1"}

    @contextmanager
    def _open_stream_response(
        self,
        method: str,
        params: dict[str, Any] | None,
    ) -> Iterator[Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._new_id("stream"),
            "method": self._rpc_method(method),
            "params": params or {},
        }
        stream_method = getattr(self._http, "stream", None)
        if callable(stream_method):
            with stream_method(
                "POST",
                self._rpc_url(),
                json=payload,
                headers=self._headers(),
                **self._request_options(),
            ) as response:
                yield response
            return

        response = self._http.post(
            self._rpc_url(),
            json=payload,
            headers=self._headers(),
            stream=True,
            **self._request_options(),
        )
        try:
            yield response
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
