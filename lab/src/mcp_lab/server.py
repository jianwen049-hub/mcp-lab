"""Tiny MCP-shaped server over an in-memory / stdio transport."""
from __future__ import annotations

import json
import time
from typing import Any

from .protocol import (
    PROTOCOL_VERSION,
    JsonRpcResponse,
    error_obj,
    new_id,
    parse_message,
)
from .schema import SchemaError, validate
from .security import PermissionGate, redact_obj
from .tools_catalog import ToolSpec, build_catalog


class McpServer:
    def __init__(
        self,
        *,
        hang_tools: set[str] | None = None,
        hang_seconds: float = 0.05,
        permission: PermissionGate | None = None,
        redact: bool = True,
    ) -> None:
        self.tools, self.resources, self.prompts = build_catalog()
        self.hang_tools = hang_tools or set()
        self.hang_seconds = hang_seconds
        self.permission = permission
        self.redact = redact
        self.initialized = False

    def handle_line(self, line: str) -> str:
        try:
            msg = parse_message(line)
        except json.JSONDecodeError as e:
            resp = JsonRpcResponse(id=None, error=error_obj(-32700, f"parse error: {e}"))
            return resp.encode()
        except ValueError as e:
            resp = JsonRpcResponse(id=None, error=error_obj(-32600, str(e)))
            return resp.encode()

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        if not isinstance(params, dict):
            return JsonRpcResponse(id=req_id, error=error_obj(-32602, "params must be object")).encode()

        try:
            result = self.dispatch(method, params)
            return JsonRpcResponse(id=req_id, result=result).encode()
        except PermissionError as e:
            return JsonRpcResponse(id=req_id, error=error_obj(-320403, str(e))).encode()
        except SchemaError as e:
            return JsonRpcResponse(id=req_id, error=error_obj(-32602, f"schema: {e}")).encode()
        except KeyError as e:
            return JsonRpcResponse(id=req_id, error=error_obj(-32601, f"unknown: {e}")).encode()
        except Exception as e:  # noqa: BLE001 — lab surface
            return JsonRpcResponse(id=req_id, error=error_obj(-32000, str(e))).encode()

    def dispatch(self, method: str | None, params: dict[str, Any]) -> Any:
        if method == "initialize":
            client_ver = params.get("protocolVersion")
            if client_ver and client_ver != PROTOCOL_VERSION:
                # version skew: still answer but advertise server version
                pass
            self.initialized = True
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": "mcp-lab-server", "version": "0.1.0"},
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
            }
        if method == "ping":
            return {"ok": True}
        if not self.initialized and method not in {"initialize", "ping"}:
            raise RuntimeError("server not initialized")

        if method == "tools/list":
            return {
                "tools": [
                    {
                        "name": t.name,
                        "description": t.description,
                        "inputSchema": t.input_schema,
                    }
                    for t in self.tools.values()
                ]
            }
        if method == "tools/call":
            return self.call_tool(params)
        if method == "resources/list":
            return {
                "resources": [
                    {
                        "uri": r.uri,
                        "name": r.name,
                        "description": r.description,
                        "mimeType": r.mime_type,
                    }
                    for r in self.resources.values()
                ]
            }
        if method == "resources/read":
            uri = params["uri"]
            r = self.resources[uri]
            return {"contents": [{"uri": uri, "mimeType": r.mime_type, "text": r.reader()}]}
        if method == "prompts/list":
            return {
                "prompts": [
                    {"name": p.name, "description": p.description, "arguments": p.arguments_schema}
                    for p in self.prompts.values()
                ]
            }
        if method == "prompts/get":
            name = params["name"]
            args = params.get("arguments") or {}
            p = self.prompts[name]
            validate(args, p.arguments_schema)
            return {"description": p.description, "messages": [{"role": "system", "content": p.render(args)}]}
        raise KeyError(method)

    def call_tool(self, params: dict[str, Any]) -> Any:
        name = params["name"]
        arguments = params.get("arguments") or {}
        if self.permission:
            self.permission.check(name)
        tool: ToolSpec = self.tools[name]
        validate(arguments, tool.input_schema)
        if self.redact:
            arguments = redact_obj(arguments)
        if name in self.hang_tools:
            time.sleep(self.hang_seconds)
        result = tool.handler(arguments)
        return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False}
