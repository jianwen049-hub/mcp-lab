"""MCP-shaped JSON-RPC-ish messages (subset for offline lab)."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

PROTOCOL_VERSION = "2024-11-05"  # lab label; not a claim of full MCP compliance


def new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class JsonRpcRequest:
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: str | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "method": self.method, "params": self.params}
        if self.id is not None:
            d["id"] = self.id
        return d

    def encode(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class JsonRpcResponse:
    id: str | None
    result: Any = None
    error: dict[str, Any] | None = None
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error is not None:
            d["error"] = self.error
        else:
            d["result"] = self.result
        return d

    def encode(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


def parse_message(line: str) -> dict[str, Any]:
    """Parse one newline-delimited JSON message. Raises json.JSONDecodeError / ValueError."""
    raw = line.strip()
    if not raw:
        raise ValueError("empty message")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("message must be object")
    if obj.get("jsonrpc") != "2.0":
        raise ValueError("jsonrpc version skew or missing")
    return obj


def error_obj(code: int, message: str, data: Any = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        err["data"] = data
    return err
