import { useState, type ChangeEvent } from "react";
import type { JsonValue, NormalizedField } from "../types";

type Props = {
  fields: NormalizedField[];
  value: Record<string, JsonValue>;
  onChange: (next: Record<string, JsonValue>) => void;
};

function formatTypeLabel(field: NormalizedField): string {
  if (field.type === "array") {
    return "array";
  }
  if (
    field.type === "object" &&
    field.raw &&
    typeof field.raw === "object" &&
    "additionalProperties" in field.raw
  ) {
    return "dict";
  }
  return field.type ?? "unknown";
}

function parsePrimitive(input: string, type?: string): JsonValue {
  if (type === "integer" || type === "number") {
    const asNumber = Number(input);
    return Number.isNaN(asNumber) ? 0 : asNumber;
  }
  if (type === "boolean") {
    return input === "true";
  }
  return input;
}

function getAtPath(
  obj: Record<string, JsonValue>,
  path: string[]
): JsonValue | undefined {
  let current: JsonValue | Record<string, JsonValue> = obj;
  for (const key of path) {
    if (
      typeof current !== "object" ||
      current === null ||
      Array.isArray(current) ||
      !(key in current)
    ) {
      return undefined;
    }
    current = current[key] as JsonValue;
  }
  return current as JsonValue;
}

function setAtPath(
  obj: Record<string, JsonValue>,
  path: string[],
  fieldValue: JsonValue
): Record<string, JsonValue> {
  const copy: Record<string, JsonValue> = JSON.parse(JSON.stringify(obj));
  let current: Record<string, JsonValue> = copy;

  for (let i = 0; i < path.length - 1; i += 1) {
    const key = path[i];
    const currentValue = current[key];
    if (
      typeof currentValue !== "object" ||
      currentValue === null ||
      Array.isArray(currentValue)
    ) {
      current[key] = {};
    }
    current = current[key] as Record<string, JsonValue>;
  }

  current[path[path.length - 1]] = fieldValue;
  return copy;
}

function defaultValueForField(field: NormalizedField): JsonValue {
  if (field.type === "array") {
    return [];
  }
  if (field.type === "object") {
    return {};
  }
  if (field.type === "number" || field.type === "integer") {
    return 0;
  }
  if (field.type === "boolean") {
    return false;
  }
  return "";
}

function FieldNode({
  field,
  path,
  rootValue,
  onChange,
}: {
  field: NormalizedField;
  path: string[];
  rootValue: Record<string, JsonValue>;
  onChange: (next: Record<string, JsonValue>) => void;
}) {
  const [newMapKey, setNewMapKey] = useState("");
  const fullPath = [...path, field.name];
  const current = getAtPath(rootValue, fullPath);
  const asString =
    typeof current === "string"
      ? current
      : current === undefined
      ? ""
      : JSON.stringify(current, null, 2);

  const applyChange = (
    event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const rawValue = event.target.value;
    let parsed: JsonValue;

    if (field.type === "array" || field.type === "object") {
      try {
        parsed = JSON.parse(rawValue) as JsonValue;
      } catch {
        parsed = rawValue;
      }
    } else {
      parsed = parsePrimitive(rawValue, field.type);
    }

    onChange(setAtPath(rootValue, fullPath, parsed));
  };

  if (field.type === "array") {
    const arr = Array.isArray(current) ? current : [];
    return (
      <fieldset className="nested-fieldset">
        <legend>{field.title}</legend>
        <small>Type: {formatTypeLabel(field)}</small>
        {field.description ? <small>{field.description}</small> : null}
        <div className="row">
          <button
            type="button"
            onClick={() => {
              const next = [...arr, {} as JsonValue];
              onChange(setAtPath(rootValue, fullPath, next));
            }}
          >
            Add element
          </button>
        </div>
        {arr.map((item, index) => (
          <div className="array-item" key={`${fullPath.join(".")}-${index}`}>
            <textarea
              rows={4}
              value={JSON.stringify(item, null, 2)}
              onChange={(event) => {
                try {
                  const parsed = JSON.parse(event.target.value) as JsonValue;
                  const next = [...arr];
                  next[index] = parsed;
                  onChange(setAtPath(rootValue, fullPath, next));
                } catch {
                  // keep textarea editable without forcing valid json at each keystroke
                }
              }}
            />
            <button
              type="button"
              onClick={() => {
                const next = arr.filter((_, i) => i !== index);
                onChange(setAtPath(rootValue, fullPath, next));
              }}
            >
              Delete element
            </button>
          </div>
        ))}
      </fieldset>
    );
  }

  if (
    field.type === "object" &&
    Array.isArray(field.children) &&
    field.children.length > 0
  ) {
    return (
      <fieldset className="nested-fieldset">
        <legend>{field.title}</legend>
        <small>Type: {formatTypeLabel(field)}</small>
        {field.description ? <small>{field.description}</small> : null}
        {field.children.map((child) => (
          <FieldNode
            key={`${fullPath.join(".")}.${child.name}`}
            field={child}
            path={fullPath}
            rootValue={rootValue}
            onChange={onChange}
          />
        ))}
      </fieldset>
    );
  }

  if (
    field.type === "object" &&
    field.raw &&
    typeof field.raw === "object" &&
    "additionalProperties" in field.raw
  ) {
    const mapValue =
      current && typeof current === "object" && !Array.isArray(current)
        ? (current as Record<string, JsonValue>)
        : {};

    return (
      <fieldset className="nested-fieldset">
        <legend>{field.title}</legend>
        <small>Type: {formatTypeLabel(field)}</small>
        {field.description ? <small>{field.description}</small> : null}

        <div className="row">
          <input
            placeholder="new key"
            value={newMapKey}
            onChange={(event) => setNewMapKey(event.target.value)}
          />
          <button
            type="button"
            onClick={() => {
              if (!newMapKey) {
                return;
              }
              const next = {
                ...mapValue,
                [newMapKey]: defaultValueForField(field),
              };
              onChange(setAtPath(rootValue, fullPath, next));
              setNewMapKey("");
            }}
          >
            Add key
          </button>
        </div>

        {Object.entries(mapValue).map(([key, item]) => (
          <div className="map-item" key={`${fullPath.join(".")}-${key}`}>
            <strong>{key}</strong>
            <textarea
              rows={4}
              value={JSON.stringify(item, null, 2)}
              onChange={(event) => {
                try {
                  const parsed = JSON.parse(event.target.value) as JsonValue;
                  const next = { ...mapValue, [key]: parsed };
                  onChange(setAtPath(rootValue, fullPath, next));
                } catch {
                  // keep editable while invalid json
                }
              }}
            />
            <button
              type="button"
              onClick={() => {
                const { [key]: _, ...rest } = mapValue;
                onChange(setAtPath(rootValue, fullPath, rest));
              }}
            >
              Delete key
            </button>
          </div>
        ))}
      </fieldset>
    );
  }

  return (
    <label className="field">
      <span>
        {field.title} {field.required ? "*" : ""}
      </span>
      <small>Type: {formatTypeLabel(field)}</small>
      {field.enum && field.enum.length > 0 ? (
        <select value={String(current ?? "")} onChange={applyChange}>
          <option value="">-- select --</option>
          {field.enum.map((item) => (
            <option key={String(item)} value={String(item)}>
              {String(item)}
            </option>
          ))}
        </select>
      ) : field.type === "object" ? (
        <textarea rows={4} value={asString} onChange={applyChange} />
      ) : (
        <input
          type={field.type === "number" || field.type === "integer" ? "number" : "text"}
          value={asString}
          onChange={applyChange}
        />
      )}
      {field.description ? <small>{field.description}</small> : null}
    </label>
  );
}

export function SchemaForm({ fields, value, onChange }: Props) {
  return (
    <div className="card">
      <h2>Schema Form</h2>
      {fields.length === 0 ? <p>No schema selected yet.</p> : null}
      {fields.map((field) => (
        <FieldNode
          key={field.name}
          field={field}
          path={[]}
          rootValue={value}
          onChange={onChange}
        />
      ))}
    </div>
  );
}
