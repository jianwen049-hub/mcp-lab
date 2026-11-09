"""Least privilege helpers + PII redaction before tool args leave the box."""
from __future__ import annotations

import re
from typing import Any

PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
ID_CARD_RE = re.compile(r"(?<!\d)(\d{17}[\dXx])(?!\d)")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CARD_RE = re.compile(r"(?<!\d)(\d{13,19})(?!\d)")


def redact_text(text: str) -> str:
    if not text:
        return text
    out = PHONE_RE.sub("[REDACTED_PHONE]", text)
    out = ID_CARD_RE.sub("[REDACTED_ID]", out)
    out = EMAIL_RE.sub("[REDACTED_EMAIL]", out)
    # crude card: only if Luhn-ish length; still redact long digit runs carefully
    def _card(m: re.Match[str]) -> str:
        digits = m.group(1)
        if 15 <= len(digits) <= 19:
            return "[REDACTED_CARD]"
        return digits
    out = CARD_RE.sub(_card, out)
    return out


def redact_obj(obj: Any) -> Any:
    if isinstance(obj, str):
        return redact_text(obj)
    if isinstance(obj, list):
        return [redact_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_obj(v) for k, v in obj.items()}
    return obj


class PermissionGate:
    """Allow-list of tool names an agent role may call."""

    def __init__(self, allowed: set[str]):
        self.allowed = set(allowed)

    def check(self, tool_name: str) -> None:
        if tool_name not in self.allowed:
            raise PermissionError(f"tool '{tool_name}' not allowed for this principal")
