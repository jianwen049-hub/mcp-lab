from __future__ import annotations

import unittest

from mcp_lab.client import McpClient
from mcp_lab.failures import drill_partial_json, drill_version_skew
from mcp_lab.schema import SchemaError, validate
from mcp_lab.security import PermissionGate, redact_text
from mcp_lab.server import McpServer


class McpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = McpServer(permission=PermissionGate({"lookup_refund", "risk_score"}))
        self.client = McpClient(self.server.handle_line)
        self.client.initialize()

    def test_list_and_call(self) -> None:
        names = {t["name"] for t in self.client.list_tools()}
        self.assertIn("lookup_refund", names)
        got = self.client.call_tool("lookup_refund", {"order_id": "ORD-2024-881"})
        self.assertTrue(got["ok"])
        self.assertEqual(got["amount_cents"], 1990)

    def test_permission_denied(self) -> None:
        with self.assertRaises(RuntimeError):
            self.client.call_tool("create_ops_ticket", {"title": "x"})

    def test_schema_fail(self) -> None:
        with self.assertRaises(RuntimeError):
            self.client.call_tool("lookup_refund", {})

    def test_resource_and_prompt(self) -> None:
        text = self.client.read_resource("sla://payment/refund")
        self.assertIn("T+1", text)
        prompt = self.client.get_prompt("refund_assist", {"order_id": "ORD-1"})
        self.assertIn("ORD-1", prompt)

    def test_redact(self) -> None:
        self.assertIn("REDACTED_PHONE", redact_text("联系电话13812345678谢谢"))

    def test_validate_extra(self) -> None:
        schema = {
            "type": "object",
            "required": ["a"],
            "additionalProperties": False,
            "properties": {"a": {"type": "string"}},
        }
        validate({"a": "x"}, schema)
        with self.assertRaises(SchemaError):
            validate({"a": "x", "b": 1}, schema)

    def test_failures(self) -> None:
        self.assertEqual(drill_partial_json(), "partial_json_drill_done")
        skew = drill_version_skew()
        self.assertEqual(skew["server_advertised"], "2024-11-05")


if __name__ == "__main__":
    unittest.main()
