"""Demo tools / resources / prompts for payment-risk-ops style agents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Any]


@dataclass
class ResourceSpec:
    uri: str
    name: str
    description: str
    mime_type: str
    reader: Callable[[], str]


@dataclass
class PromptSpec:
    name: str
    description: str
    arguments_schema: dict[str, Any]
    render: Callable[[dict[str, Any]], str]


def build_catalog() -> tuple[dict[str, ToolSpec], dict[str, ResourceSpec], dict[str, PromptSpec]]:
    refunds: dict[str, dict[str, Any]] = {
        "ORD-2024-881": {"status": "eligible", "amount_cents": 1990, "channel": "alipay"},
        "ORD-2024-999": {"status": "blocked", "amount_cents": 88000, "channel": "card", "reason": "R-403"},
    }

    def lookup_refund(args: dict[str, Any]) -> Any:
        oid = args["order_id"]
        row = refunds.get(oid)
        if not row:
            return {"ok": False, "error": "not_found", "order_id": oid}
        return {"ok": True, "order_id": oid, **row}

    def risk_score(args: dict[str, Any]) -> Any:
        device = str(args.get("device_fingerprint", ""))
        score = 88 if device.startswith("bad-") else 12
        return {"risk_score": score, "decision": "reject" if score >= 80 else "pass"}

    def create_ticket(args: dict[str, Any]) -> Any:
        return {
            "ticket_id": "T-" + str(abs(hash(args["title"])) % 100000),
            "title": args["title"],
            "priority": args.get("priority", "P2"),
        }

    tools = {
        "lookup_refund": ToolSpec(
            name="lookup_refund",
            description="查询订单退款资格与渠道（支付域只读）",
            input_schema={
                "type": "object",
                "required": ["order_id"],
                "additionalProperties": False,
                "properties": {"order_id": {"type": "string", "minLength": 3}},
            },
            handler=lookup_refund,
        ),
        "risk_score": ToolSpec(
            name="risk_score",
            description="按设备指纹粗评风险分（风控域）",
            input_schema={
                "type": "object",
                "required": ["device_fingerprint"],
                "additionalProperties": False,
                "properties": {"device_fingerprint": {"type": "string", "minLength": 1}},
            },
            handler=risk_score,
        ),
        "create_ops_ticket": ToolSpec(
            name="create_ops_ticket",
            description="创建运营工单（有副作用，需最小权限）",
            input_schema={
                "type": "object",
                "required": ["title"],
                "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "priority": {"type": "string"},
                },
            },
            handler=create_ticket,
        ),
    }

    def read_sla() -> str:
        return (
            "# 退款 SLA\n"
            "- 原路退回一般 T+1 到账\n"
            "- 大额需风控复核\n"
            "- 夜间 02:00-04:00 批处理窗口查询可能延迟\n"
        )

    def read_reject_codes() -> str:
        return (
            "# 风控拒绝码\n"
            "- R-403 设备指纹异常，需重新核身\n"
            "- R-501 累计退款频次过高\n"
        )

    resources = {
        "sla://payment/refund": ResourceSpec(
            uri="sla://payment/refund",
            name="refund_sla",
            description="支付退款 SLA 说明",
            mime_type="text/markdown",
            reader=read_sla,
        ),
        "policy://risk/reject-codes": ResourceSpec(
            uri="policy://risk/reject-codes",
            name="reject_codes",
            description="风控拒绝码手册",
            mime_type="text/markdown",
            reader=read_reject_codes,
        ),
    }

    def render_refund_assist(args: dict[str, Any]) -> str:
        oid = args.get("order_id", "")
        return (
            "你是支付域助手。只依据工具与资源回答。\n"
            f"用户订单：{oid}\n"
            "步骤：先 lookup_refund，必要时 risk_score，禁止编造到账时间。\n"
        )

    prompts = {
        "refund_assist": PromptSpec(
            name="refund_assist",
            description="退款助手系统提示模板",
            arguments_schema={
                "type": "object",
                "required": ["order_id"],
                "properties": {"order_id": {"type": "string"}},
            },
            render=render_refund_assist,
        )
    }
    return tools, resources, prompts
