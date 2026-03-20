import { useEffect, useState } from "react";
import type { JsonValue } from "../types";

type Props = {
  value: JsonValue;
  onChange: (next: JsonValue) => void;
};

export function JsonTreeEditor({ value, onChange }: Props) {
  const [draft, setDraft] = useState(JSON.stringify(value, null, 2));

  useEffect(() => {
    setDraft(JSON.stringify(value, null, 2));
  }, [value]);

  return (
    <div className="card">
      <h2>Config Tree (JSON)</h2>
      <textarea
        rows={18}
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
      />
      <button
        onClick={() => {
          const parsed = JSON.parse(draft) as JsonValue;
          onChange(parsed);
        }}
      >
        Apply JSON
      </button>
    </div>
  );
}
