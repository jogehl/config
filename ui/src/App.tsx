import { useEffect, useMemo, useState } from "react";
import {
  ConfigBuilderApiClient,
  type ConfigFormat,
  type ConfigMetadataResponse,
} from "./apiClient";
import { JsonTreeEditor } from "./components/JsonTreeEditor";
import { SchemaForm } from "./components/SchemaForm";
import type { ClassSchemaResponse, JsonValue } from "./types";

const api = new ConfigBuilderApiClient();

function inferFormatFromPath(path: string): ConfigFormat {
  if (path.endsWith(".yaml") || path.endsWith(".yml")) {
    return "yaml";
  }
  if (path.endsWith(".toml")) {
    return "toml";
  }
  return "json";
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

  const objectDraft = useMemo(() => {
    if (configDraft && typeof configDraft === "object" && !Array.isArray(configDraft)) {
      return configDraft as Record<string, JsonValue>;
    }
    return {};
  }, [configDraft]);

  useEffect(() => {
    Promise.all([api.getFormats(), api.getClasses()])
      .then(([formatList, classList]) => {
        setFormats(formatList);
        setClasses(classList);
        if (classList.length > 0) {
          setSelectedClass(classList[0]);
        }
      })
      .catch((error: unknown) => setStatus(`Init failed: ${String(error)}`));
  }, []);

  useEffect(() => {
    if (!selectedClass) {
      return;
    }
    api.getClassSchema(selectedClass)
      .then((result) => setSchema(result))
      .catch((error: unknown) => setStatus(`Schema load failed: ${String(error)}`));
  }, [selectedClass]);

  useEffect(() => {
    const poll = setInterval(async () => {
      if (!configPath) {
        return;
      }
      try {
        const metadata = await api.configMetadata({ config_path: configPath });
        setRemoteMetadata(metadata);
      } catch {
        // ignore polling errors while typing paths
      }
    }, 4000);

    return () => clearInterval(poll);
  }, [configPath]);

  const hasExternalChanges =
    loadedMetadata?.sha256 !== undefined &&
    remoteMetadata?.sha256 !== undefined &&
    loadedMetadata?.sha256 !== remoteMetadata?.sha256;

  return (
    <main>
      <h1>Simple Config Builder UI</h1>
      <p className="subtitle">
        Load config, choose a config class schema, edit in form/tree mode, validate,
        and save.
      </p>

      <section className="card controls">
        <label>
          Config path
          <input value={configPath} onChange={(event) => setConfigPath(event.target.value)} />
        </label>

        <label>
          Config class
          <select value={selectedClass} onChange={(event) => setSelectedClass(event.target.value)}>
            <option value="">-- pick class --</option>
            {classes.map((className) => (
              <option key={className} value={className}>
                {className}
              </option>
            ))}
          </select>
        </label>

        <div className="row">
          <button
            onClick={async () => {
              setStatus("Loading config...");
              try {
                const result = await api.loadConfig({ config_path: configPath });
                setConfigDraft(result.config);
                setLoadedMetadata(result.metadata);
                setStatus("Config loaded");
              } catch (error: unknown) {
                setStatus(`Load failed: ${String(error)}`);
              }
            }}
          >
            Load
          </button>

          <button
            onClick={async () => {
              if (!selectedClass || typeof configDraft !== "object" || Array.isArray(configDraft)) {
                setStatus("Pick a class and use an object config before validating");
                return;
              }
              setStatus("Validating...");
              try {
                await api.validateConfig({
                  class_name: selectedClass,
                  data: configDraft as Record<string, JsonValue>,
                });
                setStatus("Validation passed");
              } catch (error: unknown) {
                setStatus(`Validation failed: ${String(error)}`);
              }
            }}
          >
            Validate
          </button>

          <button
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

        <p>Status: {status}</p>
        <p>Supported formats: {formats.join(", ")}</p>
        {hasExternalChanges ? (
          <p className="warning">Warning: file changed externally since you loaded it.</p>
        ) : null}
      </section>

      <section className="grid">
        <SchemaForm
          fields={schema?.normalized_schema.fields ?? []}
          value={objectDraft}
          onChange={(next) => setConfigDraft(next)}
        />
        <JsonTreeEditor value={configDraft} onChange={setConfigDraft} />
      </section>
    </main>
  );
}
