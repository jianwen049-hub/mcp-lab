"""CLI demos for humans."""
from __future__ import annotations

import json
import sys

from .client import McpClient
from .failures import drill_partial_json, drill_version_skew
from .security import PermissionGate
from .server import McpServer
from .transport import tradeoffs


def demo() -> int:
    # least privilege: refund assistant may not create tickets
    gate = PermissionGate({"lookup_refund", "risk_score"})
    server = McpServer(permission=gate, redact=True)
    client = McpClient(server.handle_line)
    init = client.initialize()
    tools = client.list_tools()
    refund = client.call_tool("lookup_refund", {"order_id": "ORD-2024-881"})
    # PII should be redacted before handler sees it — pass phone in fingerprint field for demo
    risk = client.call_tool(
        "risk_score",
        {"device_fingerprint": "device-13812345678-ok"},
    )
    sla = client.read_resource("sla://payment/refund")
    prompt = client.get_prompt("refund_assist", {"order_id": "ORD-2024-881"})

    denied = None
    try:
        client.call_tool("create_ops_ticket", {"title": "should fail"})
    except RuntimeError as e:
        denied = str(e)

    print(json.dumps({
        "init": init["serverInfo"],
        "tools": [t["name"] for t in tools],
        "refund": refund,
        "risk": risk,
        "sla_head": sla.splitlines()[0],
        "prompt_head": prompt.splitlines()[0],
        "ticket_denied": denied,
        "transport_tradeoffs": tradeoffs(),
        "partial_json": drill_partial_json(),
        "version_skew": drill_version_skew(),
    }, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] == "demo":
        return demo()
    print("usage: python -m mcp_lab.cli demo", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
