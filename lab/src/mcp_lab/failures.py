"""Injectable failure modes: hanging tools, partial JSON, version skew."""
from __future__ import annotations

from .client import McpClient
from .protocol import PROTOCOL_VERSION
from .server import McpServer


def drill_hang(timeout_s: float = 0.01) -> str:
    """Server hangs on create_ops_ticket; client-side we just detect slow path via hang_seconds."""
    server = McpServer(hang_tools={"create_ops_ticket"}, hang_seconds=0.05)
    client = McpClient(server.handle_line)
    client.initialize()
    # In lab we don't implement async timeout client; we document the mode and still call.
    client.call_tool("create_ops_ticket", {"title": "hang-drill"})
    return "hang_drill_done"


def drill_partial_json() -> str:
    server = McpServer()
    # Feed truncated JSON
    resp = server.handle_line('{"jsonrpc":"2.0","id":"1","method":"tools/list"')  # missing closing
    assert "parse error" in resp or "-32700" in resp
    return "partial_json_drill_done"


def drill_version_skew() -> dict:
    server = McpServer()
    client = McpClient(server.handle_line, protocol_version="2099-01-01")
    result = client.initialize()
    # Server answers with its own PROTOCOL_VERSION
    assert result["protocolVersion"] == PROTOCOL_VERSION
    return {"client_sent": "2099-01-01", "server_advertised": result["protocolVersion"]}
