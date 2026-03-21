import { useEffect, useState } from "react";
import type { JsonValue } from "../types";

type Props = {
  value: JsonValue;
  onChange: (next: JsonValue) => void;
};

export function JsonTreeEditor({ value, onChange }: Props) {
  const [draft, setDraft] = useState(JSON.stringify(value, null, 2));
  const [parseError, setParseError] = useState<string | null>(null);

  useEffect(() => {
    setDraft(JSON.stringify(value, null, 2));
    setParseError(null);
  }, [value]);

  const lineCount = draft.split("\n").length;

  const handleApply = () => {
    try {
      const parsed = JSON.parse(draft) as JsonValue;
      setParseError(null);
      onChange(parsed);
    } catch (e: unknown) {
      setParseError(e instanceof Error ? e.message : "Invalid JSON");
    }
  };

  return (
    <div className="bg-surface rounded-lg border border-border p-5 shadow-sm transition-shadow hover:shadow-md">
      <h2 className="m-0 mb-4 text-[15px] font-semibold flex items-center gap-2 pb-3 border-b border-border">
        <span className="text-base opacity-60">{"{ }"}</span>
        Config Tree (JSON)
      </h2>

      <div className={parseError ? "json-error" : ""}>
        <textarea
          className="json-dark-textarea"
          rows={18}
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value);
            setParseError(null);
          }}
          spellCheck={false}
        />
        {parseError && (
          <div className="text-xs text-danger mt-1.5 font-mono">{parseError}</div>
        )}
      </div>

      <div className="flex items-center justify-between mt-2.5">
        <span className="text-[11px] text-text-faint font-mono">{lineCount} lines</span>
        <button
          className="bg-primary text-white hover:bg-primary-hover hover:shadow-md active:scale-[0.97]"
          onClick={handleApply}
        >
          Apply JSON
        </button>
      </div>
    </div>
  );
}
