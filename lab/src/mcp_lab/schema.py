"""Minimal JSON-Schema-ish validator for tool arguments."""
from __future__ import annotations

from typing import Any


class SchemaError(ValueError):
    pass


def validate(instance: Any, schema: dict[str, Any], path: str = "$") -> None:
    t = schema.get("type")
    if t == "object":
        if not isinstance(instance, dict):
            raise SchemaError(f"{path}: expected object")
        required = schema.get("required") or []
        for key in required:
            if key not in instance:
                raise SchemaError(f"{path}: missing required '{key}'")
        props = schema.get("properties") or {}
        additional = schema.get("additionalProperties", True)
        for key, val in instance.items():
            if key in props:
                validate(val, props[key], f"{path}.{key}")
            elif additional is False:
                raise SchemaError(f"{path}: unexpected property '{key}'")
    elif t == "string":
        if not isinstance(instance, str):
            raise SchemaError(f"{path}: expected string")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            raise SchemaError(f"{path}: string too short")
    elif t == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            raise SchemaError(f"{path}: expected integer")
    elif t == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            raise SchemaError(f"{path}: expected number")
    elif t == "boolean":
        if not isinstance(instance, bool):
            raise SchemaError(f"{path}: expected boolean")
    elif t == "array":
        if not isinstance(instance, list):
            raise SchemaError(f"{path}: expected array")
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                validate(item, item_schema, f"{path}[{i}]")
