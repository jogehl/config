import type { ChangeEvent } from "react";
import type { JsonValue, NormalizedField } from "../types";

type Props = {
  fields: NormalizedField[];
  value: Record<string, JsonValue>;
  onChange: (next: Record<string, JsonValue>) => void;
};

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

function getAtPath(obj: Record<string, JsonValue>, path: string[]): JsonValue | undefined {
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

  if (field.children.length > 0) {
    return (
      <fieldset className="nested-fieldset">
        <legend>{field.title}</legend>
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

  return (
    <label className="field">
      <span>
        {field.title} {field.required ? "*" : ""}
      </span>
      {field.enum && field.enum.length > 0 ? (
        <select value={String(current ?? "")} onChange={applyChange}>
          <option value="">-- select --</option>
          {field.enum.map((item) => (
            <option key={String(item)} value={String(item)}>
              {String(item)}
            </option>
          ))}
        </select>
      ) : field.type === "array" || field.type === "object" ? (
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
