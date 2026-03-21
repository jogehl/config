import { useCallback, useEffect, useState } from "react";
import { ConfigBuilderApiClient, type BrowseEntry } from "../apiClient";

type Props = {
  api: ConfigBuilderApiClient;
  onSelect: (path: string) => void;
  onClose: () => void;
};

const CONFIG_EXTENSIONS = [".json", ".yaml", ".yml", ".toml"];

function hasConfigExtension(name: string): boolean {
  return CONFIG_EXTENSIONS.some((ext) => name.toLowerCase().endsWith(ext));
}

export function FileBrowser({ api, onSelect, onClose }: Props) {
  const [resolvedPath, setResolvedPath] = useState("");
  const [parentPath, setParentPath] = useState<string | null>(null);
  const [entries, setEntries] = useState<BrowseEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [filename, setFilename] = useState("");

  const load = useCallback(
    async (dir: string) => {
      setLoading(true);
      setError(null);
      try {
        const result = await api.browse(dir);
        setEntries(result.entries);
        setResolvedPath(result.path);
        setParentPath(result.parent);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    },
    [api],
  );

  useEffect(() => {
    load(".");
  }, [load]);

  const confirmSelection = (name?: string) => {
    const chosen = name ?? filename.trim();
    if (!chosen) return;
    const sep = resolvedPath.includes("\\") ? "\\" : "/";
    onSelect(resolvedPath + sep + chosen);
  };

  const handleEntry = (entry: BrowseEntry) => {
    if (entry.type === "directory") {
      const sep = resolvedPath.includes("\\") ? "\\" : "/";
      load(resolvedPath + sep + entry.name);
      setFilename("");
    } else {
      confirmSelection(entry.name);
    }
  };

  const canConfirm = filename.trim().length > 0 && hasConfigExtension(filename.trim());

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-[2px]"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-surface rounded-lg border border-border shadow-md w-full max-w-xl max-h-[80vh] flex flex-col overflow-hidden animate-[dialog-in_150ms_ease]">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3.5 border-b border-border">
          <h3 className="m-0 text-[15px] font-semibold flex items-center gap-2">
            <span className="opacity-60">&#128193;</span>
            Open Config File
          </h3>
          <button
            className="bg-transparent! text-text-muted hover:text-text p-1! border-none!"
            onClick={onClose}
            aria-label="Close"
          >
            &#10005;
          </button>
        </div>

        {/* Breadcrumb */}
        <div className="px-5 py-2 bg-surface-alt border-b border-border flex items-center gap-2 text-[12px] font-mono text-text-muted overflow-x-auto">
          <span className="shrink-0 select-none">&#128194;</span>
          <span className="truncate">{resolvedPath || "..."}</span>
        </div>

        {/* Entry list */}
        <div className="flex-1 overflow-y-auto px-2 py-2 min-h-[200px]">
          {loading && (
            <div className="text-center py-8 text-text-faint text-[13px]">Loading...</div>
          )}
          {error && (
            <div className="text-center py-8 text-danger text-[13px]">{error}</div>
          )}
          {!loading && !error && (
            <ul className="list-none m-0 p-0">
              {parentPath && (
                <li>
                  <button
                    className="w-full! text-left! bg-transparent! hover:bg-surface-alt! rounded-sm px-3! py-2! text-[13px] text-text-muted border-none!"
                    onClick={() => { load(parentPath); setFilename(""); }}
                  >
                    <span className="mr-2 opacity-60">&#11168;</span>
                    ..
                  </button>
                </li>
              )}
              {entries.length === 0 && !parentPath && (
                <li className="text-center py-6 text-text-faint text-[13px]">
                  No config files or folders found.
                </li>
              )}
              {entries.map((entry) => (
                <li key={entry.name}>
                  <button
                    className={`w-full! text-left! bg-transparent! hover:bg-surface-alt! rounded-sm px-3! py-2! text-[13px] border-none! ${
                      entry.type === "directory" ? "text-text font-medium" : "text-primary"
                    }`}
                    onClick={() => handleEntry(entry)}
                  >
                    <span className="mr-2 opacity-70">
                      {entry.type === "directory" ? "\u{1F4C1}" : "\u{1F4C4}"}
                    </span>
                    {entry.name}
                    {entry.type === "directory" && (
                      <span className="ml-1 text-text-faint">/</span>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer with filename input */}
        <div className="px-5 py-3 border-t border-border flex flex-col gap-2">
          <div className="flex gap-2 items-center">
            <input
              className="flex-1"
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && canConfirm) confirmSelection(); }}
              placeholder="config.json (or pick a file above)"
            />
            <button
              className={`shrink-0 ${
                canConfirm
                  ? "bg-primary text-white hover:bg-primary-hover hover:shadow-md"
                  : "bg-surface-alt text-text-faint cursor-not-allowed! border border-border"
              }`}
              disabled={!canConfirm}
              onClick={() => confirmSelection()}
            >
              {filename.trim() && !entries.some((e) => e.type === "file" && e.name === filename.trim())
                ? "Create"
                : "Open"}
            </button>
          </div>
          <span className="text-[11px] text-text-faint">
            Supported: {CONFIG_EXTENSIONS.join(", ")}
          </span>
        </div>
      </div>
    </div>
  );
}
