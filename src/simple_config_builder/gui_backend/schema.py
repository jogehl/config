"""Schema helpers for GUI clients."""

from __future__ import annotations

from typing import Any


def _resolve_ref(schema: dict[str, Any], ref: str) -> dict[str, Any]:
    """Resolve local JSON schema references like '#/$defs/MyClass'."""
    if not ref.startswith("#/"):
        return {}
    current: Any = schema
    for part in ref[2:].split("/"):
        if not isinstance(current, dict):
            return {}
        current = current.get(part)
        if current is None:
            return {}
    return current if isinstance(current, dict) else {}


def _normalize_field(
    root_schema: dict[str, Any],
    name: str,
    field_schema: dict[str, Any],
    required: set[str],
) -> dict[str, Any]:
    """Normalize a single field schema recursively."""
    resolved_schema = field_schema
    if "$ref" in field_schema:
        resolved = _resolve_ref(root_schema, field_schema["$ref"])
        if resolved:
            resolved_schema = resolved

    field_type = resolved_schema.get("type")
    if field_type is None and "properties" in resolved_schema:
        field_type = "object"

    normalized: dict[str, Any] = {
        "name": name,
        "required": name in required,
        "type": field_type,
        "title": resolved_schema.get("title", name),
        "description": resolved_schema.get("description", ""),
        "default": resolved_schema.get("default"),
        "enum": resolved_schema.get("enum"),
        "items": resolved_schema.get("items"),
        "raw": resolved_schema,
        "children": [],
        "item_children": [],
        "value_children": [],
        "config_class": resolved_schema.get("x-config-class"),
        "subclass_options": resolved_schema.get("x-config-subclasses", []),
        "item_config_class": None,
        "item_subclass_options": [],
        "value_config_class": None,
        "value_subclass_options": [],
    }

    if field_type == "object":
        child_properties = resolved_schema.get("properties", {})
        child_required = set(resolved_schema.get("required", []))
        normalized["children"] = [
            _normalize_field(root_schema, child_name, child_schema, child_required)
            for child_name, child_schema in child_properties.items()
            if isinstance(child_schema, dict)
        ]
        additional_properties = resolved_schema.get("additionalProperties")
        if isinstance(additional_properties, dict):
            value_schema = additional_properties
            if "$ref" in value_schema:
                resolved = _resolve_ref(root_schema, value_schema["$ref"])
                if resolved:
                    value_schema = resolved
            normalized["value_config_class"] = value_schema.get(
                "x-config-class"
            )
            normalized["value_subclass_options"] = value_schema.get(
                "x-config-subclasses", []
            )
            if isinstance(value_schema.get("properties"), dict):
                value_required = set(value_schema.get("required", []))
                normalized["value_children"] = [
                    _normalize_field(
                        root_schema,
                        child_name,
                        child_schema,
                        value_required,
                    )
                    for child_name, child_schema in value_schema[
                        "properties"
                    ].items()
                    if isinstance(child_schema, dict)
                ]
    elif field_type == "array":
        items = resolved_schema.get("items")
        if isinstance(items, dict):
            item_schema = items
            if "$ref" in item_schema:
                resolved = _resolve_ref(root_schema, item_schema["$ref"])
                if resolved:
                    item_schema = resolved
            normalized["item_config_class"] = item_schema.get(
                "x-config-class"
            )
            normalized["item_subclass_options"] = item_schema.get(
                "x-config-subclasses", []
            )
            if isinstance(item_schema.get("properties"), dict):
                item_required = set(item_schema.get("required", []))
                normalized["item_children"] = [
                    _normalize_field(
                        root_schema,
                        child_name,
                        child_schema,
                        item_required,
                    )
                    for child_name, child_schema in item_schema[
                        "properties"
                    ].items()
                    if isinstance(child_schema, dict)
                ]

    return normalized


def normalize_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize pydantic JSON schema for schema-driven TypeScript UIs."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))

    normalized_fields: list[dict[str, Any]] = []
    for name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            continue
        normalized_fields.append(
            _normalize_field(schema, name, field_schema, required)
        )

    return {
        "title": schema.get("title"),
        "description": schema.get("description"),
        "fields": normalized_fields,
        "required": list(required),
        "raw": schema,
    }
