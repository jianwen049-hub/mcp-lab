"""MCP-shaped client speaking newline-delimited JSON to a server handler."""
from __future__ import annotations

import json
from typing import Any, Callable

from .protocol import PROTOCOL_VERSION, JsonRpcRequest, new_id, parse_message


Handler = Callable[[str], str]


class McpClient:
    def __init__(self, handler: Handler, *, protocol_version: str = PROTOCOL_VERSION) -> None:
        self.handler = handler
        self.protocol_version = protocol_version
        self._initialized = False

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        req = JsonRpcRequest(method=method, params=params or {}, id=new_id())
        raw = self.handler(req.encode())
        msg = parse_message(raw)
        if "error" in msg and msg["error"]:
            err = msg["error"]
            raise RuntimeError(f"RPC error {err.get('code')}: {err.get('message')}")
        return msg.get("result")

    def initialize(self) -> Any:
        result = self.request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "clientInfo": {"name": "mcp-lab-client", "version": "0.1.0"},
                "capabilities": {},
            },
        )
        self._initialized = True
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        return list(self.request("tools/list")["tools"])

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        # unwrap text JSON if present
        content = result.get("content") or []
        if content and content[0].get("type") == "text":
            try:
                return json.loads(content[0]["text"])
            except json.JSONDecodeError:
                return content[0]["text"]
        return result

    def list_resources(self) -> list[dict[str, Any]]:
        return list(self.request("resources/list")["resources"])

    def read_resource(self, uri: str) -> str:
        result = self.request("resources/read", {"uri": uri})
        return result["contents"][0]["text"]

    def get_prompt(self, name: str, arguments: dict[str, Any]) -> str:
        result = self.request("prompts/get", {"name": name, "arguments": arguments})
        return result["messages"][0]["content"]
