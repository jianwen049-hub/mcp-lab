#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcp_lab.client import McpClient
from mcp_lab.cli import demo
from mcp_lab.failures import drill_partial_json, drill_version_skew
from mcp_lab.security import PermissionGate, redact_obj
from mcp_lab.server import McpServer


def main() -> int:
    server = McpServer(permission=PermissionGate({"lookup_refund", "risk_score"}), redact=True)
    client = McpClient(server.handle_line)
    info = client.initialize()
    assert info["serverInfo"]["name"] == "mcp-lab-server"
    tools = client.list_tools()
    assert len(tools) >= 3
    got = client.call_tool("lookup_refund", {"order_id": "ORD-2024-881"})
    assert got["ok"] is True
    # redaction path: phone inside fingerprint should not remain in clear if we inspect handler input —
    # we assert redact_obj works and call still succeeds
    red = redact_obj({"device_fingerprint": "x-13900001111"})
    assert "REDACTED_PHONE" in red["device_fingerprint"]
    client.call_tool("risk_score", {"device_fingerprint": "ok-device"})
    assert "T+1" in client.read_resource("sla://payment/refund")
    assert drill_partial_json() == "partial_json_drill_done"
    assert drill_version_skew()["server_advertised"] == "2024-11-05"

    # permission deny
    try:
        client.call_tool("create_ops_ticket", {"title": "nope"})
        print("expected permission error", file=sys.stderr)
        return 1
    except RuntimeError:
        pass

    loader = unittest.TestLoader()
    suite = loader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        return 1

    # demo should also run clean
    if demo() != 0:
        return 1

    print("smoke_check OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
