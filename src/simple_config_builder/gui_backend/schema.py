"""Schema helpers for GUI clients."""

from __future__ import annotations

from typing import Any


def normalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize pydantic JSON schema for schema-driven TypeScript UIs."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    normalized_fields: list[dict[str, Any]] = []
    for name, field_schema in properties.items():
        normalized_fields.append(
            {
                "name": name,
                "required": name in required,
                "type": field_schema.get("type"),
                "title": field_schema.get("title", name),
                "description": field_schema.get("description", ""),
                "default": field_schema.get("default"),
                "enum": field_schema.get("enum"),
                "items": field_schema.get("items"),
                "raw": field_schema,
            }
        )

    return {
        "title": schema.get("title"),
        "description": schema.get("description"),
        "fields": normalized_fields,
        "required": list(required),
        "raw": schema,
    }
