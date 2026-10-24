import os
from typing import Any, cast

import requests


class McpClient:
    def __init__(self, gateway_url: str, api_token: str | None = None):
        self.gateway_url = gateway_url.rstrip("/")
        self.api_token = api_token or os.getenv("TALOS_API_TOKEN")

    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def list_servers(self) -> list[dict[str, Any]]:
        """List available MCP servers known to the gateway."""
        url = f"{self.gateway_url}/v1/mcp/servers"
        resp = requests.get(url, headers=self._get_headers(), timeout=10)
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json().get("servers", []))

    def list_tools(self, server_id: str) -> list[dict[str, Any]]:
        """List tools provided by a specific server."""
        url = f"{self.gateway_url}/v1/mcp/servers/{server_id}/tools"
        resp = requests.get(url, headers=self._get_headers(), timeout=10)
        resp.raise_for_status()
        return cast(list[dict[str, Any]], resp.json().get("tools", []))

    def get_tool_schema(self, server_id: str, tool_name: str) -> dict[str, Any]:
        """Get the JSON schema for a tool."""
        url = f"{self.gateway_url}/v1/mcp/servers/{server_id}/tools/{tool_name}/schema"
        resp = requests.get(url, headers=self._get_headers(), timeout=10)
        resp.raise_for_status()
        return cast(dict[str, Any], resp.json().get("json_schema", {}))

    def invoke_tool(
        self, server_id: str, tool_name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Invoke a tool via the gateway."""
        url = f"{self.gateway_url}/v1/mcp/servers/{server_id}/tools/{tool_name}:call"
        payload = {"input": arguments}

        resp = requests.post(url, json=payload, headers=self._get_headers(), timeout=30)
        resp.raise_for_status()

        data = resp.json()
        if "error" in data:
            raise RuntimeError(f"MCP Invocation Error: {data['error']}")

        return cast(dict[str, Any], data.get("output", {}))
