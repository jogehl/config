import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ConfigBuilderApiClient,
  type ConfigFormat,
  type ConfigMetadataResponse,
} from "./apiClient";
import { FileBrowser } from "./components/FileBrowser";
import { SchemaForm } from "./components/SchemaForm";
import type { ClassSchemaResponse, JsonValue, NormalizedField } from "./types";

const api = new ConfigBuilderApiClient();

/** Build a default config object from normalized schema fields. */
function defaultsFromFields(fields: NormalizedField[]): Record<string, JsonValue> {
  const result: Record<string, JsonValue> = {};
  for (const f of fields) {
    if (f.default !== undefined && f.default !== null) {
      result[f.name] = f.default;
    } else if (f.type === "object" && f.children.length > 0) {
      result[f.name] = defaultsFromFields(f.children);
    } else if (f.type === "array") {
      result[f.name] = [];
    } else if (f.type === "object") {
      result[f.name] = {};
    } else if (f.type === "integer" || f.type === "number") {
      result[f.name] = 0;
    } else if (f.type === "boolean") {
      result[f.name] = false;
    } else {
      result[f.name] = "";
    }
  }
  return result;
}

/** Find the first _config_class_type in a (possibly nested) config object.
 *  Returns the class name and the key-path to the sub-object that holds it. */
function findConfigClassEntry(
  value: JsonValue,
  path: string[] = [],
): { classType: string; path: string[] } | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const obj = value as Record<string, JsonValue>;
    if (typeof obj._config_class_type === "string") {
      return { classType: obj._config_class_type, path };
    }
    for (const [k, v] of Object.entries(obj)) {
      const found = findConfigClassEntry(v, [...path, k]);
      if (found) return found;
    }
  }
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i++) {
      const found = findConfigClassEntry(value[i], [...path, String(i)]);
      if (found) return found;
    }
  }
  return null;
}

/** Read a nested value by key-path. */
function getNestedValue(obj: Record<string, JsonValue>, path: string[]): Record<string, JsonValue> {
  let cur: JsonValue = obj;
  for (const key of path) {
    if (cur && typeof cur === "object" && !Array.isArray(cur)) {
      cur = (cur as Record<string, JsonValue>)[key];
    } else {
      return {};
    }
  }
  return (cur && typeof cur === "object" && !Array.isArray(cur))
    ? cur as Record<string, JsonValue>
    : {};
}

/** Return a deep clone of obj with the value at path replaced. */
function setNestedValue(
  obj: Record<string, JsonValue>,
  path: string[],
  value: Record<string, JsonValue>,
): Record<string, JsonValue> {
  if (path.length === 0) return value;
  const copy: Record<string, JsonValue> = JSON.parse(JSON.stringify(obj));
  let cur: Record<string, JsonValue> = copy;
  for (let i = 0; i < path.length - 1; i++) {
    const k = path[i];
    const v = cur[k];
    if (typeof v !== "object" || v === null || Array.isArray(v)) cur[k] = {};
    cur = cur[k] as Record<string, JsonValue>;
  }
  cur[path[path.length - 1]] = value;
  return copy;
}

function inferFormatFromPath(path: string): ConfigFormat {
  if (path.endsWith(".yaml") || path.endsWith(".yml")) return "yaml";
  if (path.endsWith(".toml")) return "toml";
  return "json";
}

type StatusKind = "idle" | "loading" | "success" | "error";

const statusStyles: Record<StatusKind, string> = {
  idle: "bg-surface-alt text-text-muted",
  loading: "bg-primary-ghost text-primary",
  success: "bg-success-bg text-green-700",
  error: "bg-error-bg text-danger",
};

function classifyStatus(status: string): StatusKind {
  const s = status.toLowerCase();
  if (s === "idle") return "idle";
  if (s.includes("loading") || s.includes("saving") || s.includes("validating")) return "loading";
  if (s.includes("failed") || s.includes("error")) return "error";
  return "success";
}

export function App() {
  const [configPath, setConfigPath] = useState("tests/unit/config_files/config_with_class.json");
  const [formats, setFormats] = useState<ConfigFormat[]>([]);
  const [classes, setClasses] = useState<string[]>([]);
  const [selectedClass, setSelectedClass] = useState("");
  const [schema, setSchema] = useState<ClassSchemaResponse | null>(null);
  const [configDraft, setConfigDraft] = useState<JsonValue>({});
  const [status, setStatus] = useState("Idle");
  const [loadedMetadata, setLoadedMetadata] = useState<ConfigMetadataResponse | null>(null);
  const [remoteMetadata, setRemoteMetadata] = useState<ConfigMetadataResponse | null>(null);
  const [showFileBrowser, setShowFileBrowser] = useState(false);
  const [classDataPath, setClassDataPath] = useState<string[]>([]);

  const loadConfigFromPath = useCallback(async (path: string) => {
    setStatus("Loading config...");
    try {
      const result = await api.loadConfig({ config_path: path });
      setConfigDraft(result.config);
      setLoadedMetadata(result.metadata);
      // Auto-detect config class from _config_class_type (search recursively)
      const entry = findConfigClassEntry(result.config);
      if (entry) {
        setSelectedClass(entry.classType);
        setClassDataPath(entry.path);
      } else {
        setSelectedClass("");
        setClassDataPath([]);
      }
      setStatus("Config loaded");
    } catch {
      // New file — start with empty draft
      setConfigDraft({});
      setLoadedMetadata(null);
      setStatus("New file (will be created on save)");
    }
  }, []);

  const objectDraft = useMemo(() => {
    if (configDraft && typeof configDraft === "object" && !Array.isArray(configDraft)) {
      return configDraft as Record<string, JsonValue>;
    }
    return {};
  }, [configDraft]);

  const isEmpty = useMemo(() => {
    if (!configDraft || (typeof configDraft === "object" && !Array.isArray(configDraft) && Object.keys(configDraft as Record<string, JsonValue>).length === 0)) {
      return true;
    }
    return false;
  }, [configDraft]);

  // Debounced auto-validation
  const validateTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (!selectedClass || isEmpty) return;
    if (typeof configDraft !== "object" || Array.isArray(configDraft)) return;

    const validationData = classDataPath.length > 0
      ? getNestedValue(configDraft as Record<string, JsonValue>, classDataPath)
      : (configDraft as Record<string, JsonValue>);

    if (validateTimer.current) clearTimeout(validateTimer.current);
    validateTimer.current = setTimeout(async () => {
      try {
        await api.validateConfig({
          class_name: selectedClass,
          data: validationData,
        });
        setStatus("Validation passed");
      } catch (error: unknown) {
        setStatus(`Validation failed: ${String(error)}`);
      }
    }, 600);

    return () => {
      if (validateTimer.current) clearTimeout(validateTimer.current);
    };
  }, [configDraft, selectedClass, isEmpty, classDataPath]);

  useEffect(() => {
    Promise.all([api.getFormats(), api.getClasses()])
      .then(([formatList, classList]) => {
        setFormats(formatList);
        setClasses(classList);
      })
      .catch((error: unknown) => setStatus(`Init failed: ${String(error)}`));
  }, []);

  useEffect(() => {
    if (!selectedClass) return;
    api.getClassSchema(selectedClass)
      .then((result) => setSchema(result))
      .catch((error: unknown) => setStatus(`Schema load failed: ${String(error)}`));
  }, [selectedClass]);

  // When a class is picked on an empty file, populate with defaults from the schema
  useEffect(() => {
    if (!isEmpty || !schema?.normalized_schema.fields.length) return;
    const defaults = defaultsFromFields(schema.normalized_schema.fields);
    if (Object.keys(defaults).length > 0) {
      setConfigDraft(defaults);
      setClassDataPath([]);
      setStatus("Default config created from schema");
    }
  }, [schema, isEmpty]);

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!configPath) return;
      try {
        const metadata = await api.configMetadata({ config_path: configPath });
        setRemoteMetadata(metadata);
      } catch {
        /* ignore polling errors */
      }
    }, 4000);
    return () => clearInterval(poll);
  }, [configPath]);

  const hasExternalChanges =
    loadedMetadata?.sha256 !== undefined &&
    remoteMetadata?.sha256 !== undefined &&
    loadedMetadata?.sha256 !== remoteMetadata?.sha256;

  const statusKind = classifyStatus(status);

  return (
    <>
      {/* ── Header ────────────────────────────────────────────── */}
      <header className="bg-surface border-b border-border px-8 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm">
        <h1 className="m-0 text-lg font-bold tracking-tight flex items-center gap-2.5">
          <span className="w-7 h-7 bg-primary rounded-sm inline-flex items-center justify-center text-white font-extrabold text-sm">
            C
          </span>
          Simple Config Builder
        </h1>
        <div className="flex items-center gap-4 text-[13px] text-text-muted">
          Formats: {formats.join(", ") || "..."}
        </div>
      </header>

      {/* ── Main ──────────────────────────────────────────────── */}
      <main className="px-4 pt-4 pb-8">
        {/* Controls card */}
        <section className="bg-surface rounded-lg border border-border p-5 shadow-sm mb-5">
          <h2 className="m-0 mb-4 text-[15px] font-semibold flex items-center gap-2 pb-3 border-b border-border">
            <span className="text-base opacity-60">&#9881;</span>
            Configuration
          </h2>

          <div className="flex flex-col gap-1">
            <span className="text-[13px] font-[550] text-text">Config path</span>
            <div className="flex gap-2">
              <input
                value={configPath}
                readOnly
                placeholder="Select a file via Browse..."
                className="flex-1 bg-surface-alt cursor-default"
              />
              <button
                className="bg-surface-alt text-text border border-border hover:bg-border shrink-0"
                onClick={() => setShowFileBrowser(true)}
              >
                Browse
              </button>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex gap-2.5 items-center mt-3.5 flex-wrap">
            <button
              className="bg-primary text-white hover:bg-primary-hover hover:shadow-md active:scale-[0.97]"
              onClick={async () => {
                setStatus("Saving...");
                try {
                  const result = await api.saveConfig({
                    config_path: configPath,
                    config_type: inferFormatFromPath(configPath),
                    data: Array.isArray(configDraft)
                      ? configDraft
                      : (configDraft as Record<string, JsonValue>),
                  });
                  setLoadedMetadata({
                    exists: true,
                    mtime_ns: (result as { mtime_ns: number | null }).mtime_ns,
                    sha256: (result as { sha256: string | null }).sha256,
                  });
                  setStatus("Saved");
                } catch (error: unknown) {
                  setStatus(`Save failed: ${String(error)}`);
                }
              }}
            >
              Save
            </button>
          </div>

          {/* Status bar */}
          <div className="flex items-center justify-between mt-3.5 py-2 px-3 rounded-sm bg-surface-alt border border-border text-[13px]">
            <span className={`inline-flex items-center gap-1.5 font-medium text-xs px-2.5 py-0.5 rounded-full ${statusStyles[statusKind]}`}>
              <span className="w-[7px] h-[7px] rounded-full bg-current" />
              {status}
            </span>
            <span className="text-xs text-text-faint">
              {selectedClass ? selectedClass.split(".").pop() : "No class selected"}
            </span>
          </div>

          {hasExternalChanges && (
            <div className="flex items-center gap-2 mt-3 px-3.5 py-2.5 rounded-sm bg-warning-bg border border-amber-300/25 text-amber-900 text-[13px] font-medium">
              &#9888; File changed externally since you loaded it. Reload to see the latest version.
            </div>
          )}
        </section>

        {/* Schema graph */}
        <section>
          <SchemaForm
            fields={schema?.normalized_schema.fields ?? []}
            value={classDataPath.length > 0 ? getNestedValue(objectDraft, classDataPath) : objectDraft}
            onChange={(next) => {
              if (classDataPath.length > 0) {
                setConfigDraft(setNestedValue(objectDraft, classDataPath, next));
              } else {
                setConfigDraft(next);
              }
            }}
            classes={classes}
            selectedClass={selectedClass}
            onClassChange={setSelectedClass}
            isEmpty={isEmpty}
          />
        </section>
      </main>

      {showFileBrowser && (
        <FileBrowser
          api={api}
          onSelect={(path) => {
            setConfigPath(path);
            setShowFileBrowser(false);
            loadConfigFromPath(path);
          }}
          onClose={() => setShowFileBrowser(false)}
        />
      )}
    </>
  );
}
