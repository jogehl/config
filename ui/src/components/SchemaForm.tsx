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

export function SchemaForm({ fields, value, onChange }: Props) {
  const onFieldChange =
    (field: NormalizedField) => (event: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const next = { ...value };
      const rawValue = event.target.value;

      if (field.type === "array" || field.type === "object") {
        try {
          next[field.name] = JSON.parse(rawValue) as JsonValue;
        } catch {
          next[field.name] = rawValue;
        }
      } else {
        next[field.name] = parsePrimitive(rawValue, field.type);
      }
      onChange(next);
    };

  return (
    <div className="card">
      <h2>Schema Form</h2>
      {fields.length === 0 ? <p>No schema selected yet.</p> : null}
      {fields.map((field) => {
        const current = value[field.name];
        const asString =
          typeof current === "string"
            ? current
            : current === undefined
            ? ""
            : JSON.stringify(current, null, 2);

        return (
          <label className="field" key={field.name}>
            <span>
              {field.title} {field.required ? "*" : ""}
            </span>
            {field.enum && field.enum.length > 0 ? (
              <select value={String(current ?? "")} onChange={onFieldChange(field)}>
                <option value="">-- select --</option>
                {field.enum.map((item) => (
                  <option key={String(item)} value={String(item)}>
                    {String(item)}
                  </option>
                ))}
              </select>
            ) : field.type === "array" || field.type === "object" ? (
              <textarea rows={4} value={asString} onChange={onFieldChange(field)} />
            ) : (
              <input
                type={field.type === "number" || field.type === "integer" ? "number" : "text"}
                value={asString}
                onChange={onFieldChange(field)}
              />
            )}
            {field.description ? <small>{field.description}</small> : null}
          </label>
        );
      })}
    </div>
  );
}
