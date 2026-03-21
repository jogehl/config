import { useCallback, useEffect, useMemo, useRef, useState, type ChangeEvent } from "react";
import {
  ReactFlow,
  type Node,
  type Edge,
  Handle,
  Position,
  useNodesState,
  useEdgesState,
  type NodeProps,
  Background,
  BackgroundVariant,
  BaseEdge,
  type EdgeProps,
  getSmoothStepPath,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import type { JsonValue, NormalizedField } from "../types";

/* ── Props ──────────────────────────────────────────────────────── */

type Props = {
  fields: NormalizedField[];
  value: Record<string, JsonValue>;
  onChange: (next: Record<string, JsonValue>) => void;
  classes: string[];
  selectedClass: string;
  onClassChange: (cls: string) => void;
  isEmpty: boolean;
};

/* ── Value helpers ──────────────────────────────────────────────── */

function parsePrimitive(input: string, type?: string): JsonValue {
  if (type === "integer" || type === "number") {
    const n = Number(input);
    return Number.isNaN(n) ? 0 : n;
  }
  if (type === "boolean") return input === "true";
  return input;
}

function getAtPath(obj: Record<string, JsonValue>, path: string[]): JsonValue | undefined {
  let cur: JsonValue = obj;
  for (const key of path) {
    if (typeof cur !== "object" || cur === null || Array.isArray(cur) || !(key in cur)) return undefined;
    cur = (cur as Record<string, JsonValue>)[key];
  }
  return cur;
}

function setAtPath(obj: Record<string, JsonValue>, path: string[], value: JsonValue): Record<string, JsonValue> {
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

function formatTypeLabel(field: NormalizedField): string {
  if (field.type === "array") return "array";
  if (field.type === "object" && field.raw && typeof field.raw === "object" && "additionalProperties" in field.raw) return "dict";
  if (field.type === "object" && isNestedClass(field)) {
    const title = field.raw?.title;
    if (typeof title === "string" && title) return title;
  }
  return field.type ?? "unknown";
}

function isNestedClass(f: NormalizedField): boolean {
  return f.type === "object" && Array.isArray(f.children) && f.children.length > 0;
}

function isClassArray(f: NormalizedField): boolean {
  return f.type === "array" && Array.isArray(f.item_children) && f.item_children.length > 0;
}

function isClassDict(f: NormalizedField): boolean {
  return f.type === "object" && Array.isArray(f.value_children) && f.value_children.length > 0 &&
    !!(f.raw && typeof f.raw === "object" && "additionalProperties" in f.raw);
}

function isComplex(f: NormalizedField): boolean {
  return isNestedClass(f) || isClassArray(f) || isClassDict(f);
}

function defaultValueForField(field: NormalizedField): JsonValue {
  if (field.type === "array") return [];
  if (field.type === "object") return {};
  if (field.type === "number" || field.type === "integer") return 0;
  if (field.type === "boolean") return false;
  return "";
}

function defaultObjectFromChildren(children: NormalizedField[]): Record<string, JsonValue> {
  const r: Record<string, JsonValue> = {};
  for (const c of children) r[c.name] = defaultValueForField(c);
  return r;
}

/* ── Layout constants ───────────────────────────────────────────── */

const NODE_WIDTH = 380;
const HEADER_H = 42;
const ROW_H = 32;
const PAD_BOTTOM = 8;
const LABEL_W = 110;

function nodeHeight(fieldCount: number, collapsed: boolean): number {
  if (collapsed) return HEADER_H;
  return HEADER_H + fieldCount * ROW_H + PAD_BOTTOM;
}

function rowCenter(i: number): number {
  return HEADER_H + i * ROW_H + ROW_H / 2;
}

/* ── ELK layout with ports ──────────────────────────────────────── */

const elk = new ELK();

type ElkPort = { id: string; x: number; y: number; width: number; height: number };

async function layoutGraph(nodes: Node[], edges: Edge[]): Promise<Node[]> {
  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.spacing.nodeNode": "40",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
      "elk.layered.spacing.edgeNodeBetweenLayers": "40",
      "elk.padding": "[top=20,left=20,bottom=20,right=20]",
      "elk.layered.considerModelOrder": "true",
      "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
      "elk.layered.nodePlacement.strategy": "LINEAR_SEGMENTS",
    },
    children: nodes.map((n) => ({
      id: n.id,
      width: n.measured?.width ?? (n.data?.nodeWidth as number ?? NODE_WIDTH),
      height: n.measured?.height ?? (n.data?.nodeHeight as number ?? 60),
      properties: {
        "elk.portConstraints": "FIXED_POS",
      },
      ports: (n.data?.elkPorts as ElkPort[] ?? []).map((p: ElkPort) => ({
        id: p.id,
        x: p.x,
        y: p.y,
        width: p.width,
        height: p.height,
        properties: { "elk.port.side": "EAST" },
      })),
    })),
    edges: edges.map((e) => ({
      id: e.id,
      sources: [e.data?.elkSourcePort as string ?? e.source],
      targets: [e.target],
    })),
  };
  const layout = await elk.layout(elkGraph);
  return nodes.map((node) => {
    const elkNode = layout.children?.find((n) => n.id === node.id);
    return { ...node, position: { x: elkNode?.x ?? 0, y: elkNode?.y ?? 0 } };
  });
}

/* ── Node data type ─────────────────────────────────────────────── */

type ClassNodeData = {
  label: string;
  badge?: string;
  allFields: NormalizedField[];
  basePath: string[];
  rootValue: Record<string, JsonValue>;
  onFieldChange: (path: string[], value: JsonValue) => void;
  onArrayAdd: (path: string[], children: NormalizedField[]) => void;
  onArrayDelete: (path: string[], index: number) => void;
  onDictAdd: (path: string[], key: string, children: NormalizedField[]) => void;
  onDictDelete: (path: string[], key: string) => void;
  onCollapseChildren: (ids: string[]) => void;
  onExpandChild: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  nodeWidth: number;
  nodeHeight: number;
  elkPorts: ElkPort[];
  itemDelete?: () => void;
  collapsedChildren: Record<string, { type: 'array' | 'dict' | 'object'; items: { id: string; label: string; index?: number; key?: string }[]; field: NormalizedField }>;
  [key: string]: unknown;
};

/** Human-friendly label from a field name (e.g. "sub_key" -> "Sub Key"). */
function friendlyName(name: string): string {
  return name.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/* ── Inline array editor (tags) ──────────────────────────────────── */

function InlineArrayEditor({ value, onChange }: { value: JsonValue[]; onChange: (v: JsonValue[]) => void }) {
  const [draft, setDraft] = useState("");

  const addItem = () => {
    const trimmed = draft.trim();
    if (!trimmed) return;
    // Try to parse as number/boolean/JSON, fallback to string
    let parsed: JsonValue = trimmed;
    if (trimmed === "true") parsed = true;
    else if (trimmed === "false") parsed = false;
    else if (/^-?\d+(\.\d+)?$/.test(trimmed)) parsed = Number(trimmed);
    else { try { parsed = JSON.parse(trimmed) as JsonValue; } catch { /* keep as string */ } }
    onChange([...value, parsed]);
    setDraft("");
  };

  return (
    <div className="flex flex-wrap items-center gap-1">
      {value.map((item, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-0.5 text-[10px] font-mono rounded-full px-2 py-px"
          style={{
            background: 'color-mix(in srgb, var(--color-primary) 8%, white)',
            border: '1px solid color-mix(in srgb, var(--color-primary) 22%, transparent)',
            color: 'var(--color-text)',
          }}
        >
          <span className="max-w-[80px] truncate" title={String(item)}>{String(item)}</span>
          <button
            type="button"
            className="ml-0.5 text-danger hover:text-white hover:bg-danger rounded-full w-3 h-3 flex items-center justify-center text-[8px] leading-none"
            onClick={() => onChange(value.filter((_, j) => j !== i))}
          >
            ✕
          </button>
        </span>
      ))}
      <input
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addItem(); } }}
        placeholder="+ add"
        className="!text-[10px] !py-0 !px-1.5 !w-[60px] !border-dashed"
      />
    </div>
  );
}

/* ── Inline dict editor (key=value tags) ────────────────────────── */

function InlineDictEditor({ value, onChange }: { value: Record<string, JsonValue>; onChange: (v: Record<string, JsonValue>) => void }) {
  const [draftKey, setDraftKey] = useState("");
  const [draftVal, setDraftVal] = useState("");

  const addEntry = () => {
    const k = draftKey.trim();
    if (!k) return;
    let parsed: JsonValue = draftVal;
    if (draftVal === "true") parsed = true;
    else if (draftVal === "false") parsed = false;
    else if (/^-?\d+(\.\d+)?$/.test(draftVal)) parsed = Number(draftVal);
    onChange({ ...value, [k]: parsed });
    setDraftKey("");
    setDraftVal("");
  };

  return (
    <div className="flex flex-wrap items-center gap-1">
      {Object.entries(value).map(([k, v]) => (
        <span
          key={k}
          className="inline-flex items-center gap-0.5 text-[10px] font-mono rounded-full px-2 py-px"
          style={{
            background: 'color-mix(in srgb, var(--color-primary) 8%, white)',
            border: '1px solid color-mix(in srgb, var(--color-primary) 22%, transparent)',
            color: 'var(--color-text)',
          }}
        >
          <span className="font-semibold text-primary">{k}</span>
          <span className="text-text-faint">=</span>
          <span className="max-w-[60px] truncate" title={String(v)}>{String(v)}</span>
          <button
            type="button"
            className="ml-0.5 text-danger hover:text-white hover:bg-danger rounded-full w-3 h-3 flex items-center justify-center text-[8px] leading-none"
            onClick={() => { const copy = { ...value }; delete copy[k]; onChange(copy); }}
          >
            ✕
          </button>
        </span>
      ))}
      <div className="inline-flex items-center gap-0.5">
        <input
          value={draftKey}
          onChange={(e) => setDraftKey(e.target.value)}
          placeholder="key"
          className="!text-[10px] !py-0 !px-1 !w-[40px] !border-dashed"
        />
        <input
          value={draftVal}
          onChange={(e) => setDraftVal(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addEntry(); } }}
          placeholder="val"
          className="!text-[10px] !py-0 !px-1 !w-[40px] !border-dashed"
        />
      </div>
    </div>
  );
}

/* ── Inline primitive editor ────────────────────────────────────── */

function PrimitiveRow({
  field, path, rootValue, onFieldChange,
}: {
  field: NormalizedField;
  path: string[];
  rootValue: Record<string, JsonValue>;
  onFieldChange: (path: string[], value: JsonValue) => void;
}) {
  const fieldPath = [...path, field.name];
  const current = getAtPath(rootValue, fieldPath);
  const asString =
    typeof current === "string" ? current : current === undefined ? "" : JSON.stringify(current);

  const handleChange = (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const raw = e.target.value;
    let parsed: JsonValue;
    if (field.type === "array" || field.type === "object") {
      try { parsed = JSON.parse(raw) as JsonValue; } catch { parsed = raw; }
    } else {
      parsed = parsePrimitive(raw, field.type);
    }
    onFieldChange(fieldPath, parsed);
  };

  const isPrimitiveContainer = (field.type === "array" || field.type === "object") && !isComplex(field);
  const isPrimitiveArray = field.type === "array" && !isComplex(field);
  const isPrimitiveDict = field.type === "object" && !isComplex(field)
    && field.raw && typeof field.raw === 'object' && 'additionalProperties' in field.raw;

  return (
    <div className={isPrimitiveContainer ? 'px-3 py-1.5' : 'flex items-center gap-1.5 px-3'} style={isPrimitiveContainer ? undefined : { height: ROW_H }}>
      <div className={isPrimitiveContainer ? 'flex items-center gap-1.5 mb-1' : 'contents'}>
        <span
          className="text-[11px] font-medium text-text shrink-0 truncate"
          style={{ width: LABEL_W }}
          title={field.title}
        >
          {field.title}
          {field.required && <span className="text-danger ml-0.5">*</span>}
        </span>
        <span className="text-[9px] font-mono text-primary bg-primary-ghost px-1 rounded shrink-0">
          {formatTypeLabel(field)}
        </span>
      </div>
      <div className={isPrimitiveContainer ? '' : 'flex-1 min-w-0 overflow-hidden'}>
        {field.enum && field.enum.length > 0 ? (
          <select value={String(current ?? "")} onChange={handleChange} className="!text-[11px] !py-0.5 !px-1.5 w-full">
            <option value="">--</option>
            {field.enum.map((v) => <option key={String(v)} value={String(v)}>{String(v)}</option>)}
          </select>
        ) : field.type === "boolean" ? (
          <select value={String(current ?? "false")} onChange={handleChange} className="!text-[11px] !py-0.5 !px-1.5 w-full">
            <option value="true">true</option>
            <option value="false">false</option>
          </select>
        ) : isPrimitiveArray ? (
          <InlineArrayEditor
            value={Array.isArray(current) ? current : []}
            onChange={(next) => onFieldChange(fieldPath, next)}
          />
        ) : isPrimitiveDict ? (
          <InlineDictEditor
            value={current && typeof current === 'object' && !Array.isArray(current) ? current as Record<string, JsonValue> : {}}
            onChange={(next) => onFieldChange(fieldPath, next)}
          />
        ) : isPrimitiveContainer ? (
          <input
            value={asString}
            onChange={handleChange}
            title={asString}
            className="!text-[11px] !py-0.5 !px-1.5 font-mono w-full !text-ellipsis"
          />
        ) : (
          <input
            type={field.type === "number" || field.type === "integer" ? "number" : "text"}
            value={asString}
            onChange={handleChange}
            className="!text-[11px] !py-0.5 !px-1.5 w-full"
          />
        )}
      </div>
    </div>
  );
}

/* ── Complex field row (nested object / array / dict) ───────────── */

function ComplexRow({
  field, index, basePath, rootValue, onArrayAdd, onDictAdd,
}: {
  field: NormalizedField;
  index: number;
  basePath: string[];
  rootValue: Record<string, JsonValue>;
  onArrayAdd: (path: string[], children: NormalizedField[]) => void;
  onDictAdd: (path: string[], key: string, children: NormalizedField[]) => void;
}) {
  const [newKey, setNewKey] = useState("");
  const fieldPath = [...basePath, field.name];
  const current = getAtPath(rootValue, fieldPath);

  let countLabel = "";
  if (isClassArray(field)) {
    const arr = Array.isArray(current) ? current : [];
    countLabel = `[${arr.length}]`;
  } else if (isClassDict(field)) {
    const dict = current && typeof current === "object" && !Array.isArray(current) ? current as Record<string, JsonValue> : {};
    countLabel = `[${Object.keys(dict).length}]`;
  }

  return (
    <div className="flex items-center gap-1.5 px-3" style={{ height: ROW_H }}>
      {/* Source handle — top is relative to the node root (no position:relative here) */}
      <Handle
        type="source"
        position={Position.Right}
        id={`field-${field.name}`}
        className="!bg-primary !w-2.5 !h-2.5 !border-primary/50 !border-2"
        style={{ top: rowCenter(index) }}
      />

      <span
        className="text-[11px] font-semibold text-text shrink-0 truncate"
        style={{ width: LABEL_W }}
        title={field.name}
      >
        {friendlyName(field.name)}
      </span>
      <span className="text-[9px] font-mono text-primary bg-primary-ghost px-1 rounded shrink-0">
        {formatTypeLabel(field)}{countLabel}
      </span>

      {/* Array: Add button */}
      {isClassArray(field) && (
        <button
          type="button"
          className="text-[10px] bg-surface-alt text-text border border-border hover:bg-border px-1.5 py-0 rounded ml-auto shrink-0"
          onClick={(e) => { e.stopPropagation(); onArrayAdd(fieldPath, field.item_children ?? []); }}
        >
          +
        </button>
      )}

      {/* Dict: Add key */}
      {isClassDict(field) && (
        <div className="flex items-center gap-1 ml-auto shrink-0">
          <input
            value={newKey}
            onChange={(e) => setNewKey(e.target.value)}
            placeholder="key"
            className="!text-[10px] !py-0 !px-1 !w-[60px]"
            onClick={(e) => e.stopPropagation()}
          />
          <button
            type="button"
            className="text-[10px] bg-surface-alt text-text border border-border hover:bg-border px-1.5 py-0 rounded"
            onClick={(e) => {
              e.stopPropagation();
              if (!newKey) return;
              onDictAdd(fieldPath, newKey, field.value_children ?? []);
              setNewKey("");
            }}
          >
            +
          </button>
        </div>
      )}
    </div>
  );
}

/* ── Class node component ───────────────────────────────────────── */

function ClassNode({ data }: NodeProps<Node<ClassNodeData>>) {
  const {
    label, badge, allFields, basePath, rootValue, onFieldChange,
    onArrayAdd, onArrayDelete, onDictAdd, onDictDelete, onCollapseChildren, onExpandChild,
    collapsed, onToggle, itemDelete, collapsedChildren,
  } = data;
  const [newKeys, setNewKeys] = useState<Record<string, string>>({});

  return (
    <div style={{ width: NODE_WIDTH }}>
      {/* Target handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-primary !w-3 !h-3 !border-2 !border-white"
        style={{ boxShadow: '0 0 0 1.5px var(--color-primary)' }}
      />

      <div
        className="bg-surface rounded-lg shadow-md overflow-visible"
        style={{
          border: collapsed
            ? '2px solid var(--color-primary)'
            : '1.5px solid color-mix(in srgb, var(--color-primary) 28%, transparent)',
          boxShadow: collapsed
            ? '0 0 0 3px color-mix(in srgb, var(--color-primary) 10%, transparent), 0 2px 8px rgba(0,0,0,0.07)'
            : '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-2 px-3 cursor-pointer select-none transition-colors"
          style={{
            height: HEADER_H,
            background: collapsed
              ? 'color-mix(in srgb, var(--color-primary) 12%, transparent)'
              : 'color-mix(in srgb, var(--color-primary) 5%, transparent)',
            borderBottom: collapsed ? 'none' : '1px solid color-mix(in srgb, var(--color-primary) 18%, transparent)',
            borderRadius: collapsed ? '8px' : '8px 8px 0 0',
          }}
          onClick={onToggle}
        >
          <span
            className="text-primary transition-transform duration-200 text-[10px]"
            style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', display: 'inline-block' }}
          >
            &#9660;
          </span>
          <span className="font-bold text-[13px] text-text truncate flex-1">{label}</span>
          {collapsed && (
            <span
              className="text-[9px] font-mono text-primary shrink-0"
              style={{
                background: 'color-mix(in srgb, var(--color-primary) 10%, transparent)',
                border: '1px solid color-mix(in srgb, var(--color-primary) 25%, transparent)',
                borderRadius: 999,
                padding: '1px 7px',
              }}
            >
              {allFields.length} field{allFields.length !== 1 ? 's' : ''}
            </span>
          )}
          {!collapsed && badge && (
            <span className="text-[9px] font-mono text-primary bg-primary-ghost px-1.5 py-px rounded shrink-0">
              {badge}
            </span>
          )}
          {itemDelete && (
            <button
              type="button"
              className="text-[10px] text-danger hover:bg-danger/10 px-1.5 py-0.5 rounded transition-colors shrink-0"
              style={{ lineHeight: 1 }}
              onClick={(e) => { e.stopPropagation(); itemDelete(); }}
            >
              &#10005;
            </button>
          )}
        </div>

        {/* Field rows */}
        {!collapsed && allFields.map((field, i) =>
          isComplex(field) ? (
            <ComplexRow
              key={field.name}
              field={field}
              index={i}
              basePath={basePath}
              rootValue={rootValue}
              onArrayAdd={onArrayAdd}
              onDictAdd={onDictAdd}
            />
          ) : (
            <PrimitiveRow
              key={field.name}
              field={field}
              path={basePath}
              rootValue={rootValue}
              onFieldChange={onFieldChange}
            />
          ),
        )}

        {/* Collapsed children */}
        {!collapsed && Object.entries(collapsedChildren).map(([fieldName, { type, items, field }]) => {
          const fieldPath = [...basePath, fieldName];
          return (
            <div key={fieldName} className="px-3 pt-2 pb-2.5 border-t border-border/60">
              {/* Section header */}
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[9px] font-mono font-semibold text-primary uppercase tracking-wide">{fieldName}</span>
                <span
                  className="text-[8px] font-mono rounded px-1 py-px"
                  style={{
                    background: 'color-mix(in srgb, var(--color-primary) 8%, transparent)',
                    border: '1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)',
                    color: 'var(--color-primary)',
                  }}
                >
                  {type}
                </span>
                {/* Add button (only for array/dict) */}
                {type === 'array' ? (
                  <button
                    type="button"
                    className="ml-auto text-[10px] font-bold text-primary hover:text-primary-hover px-2 py-0.5 rounded transition-colors"
                    style={{
                      background: 'color-mix(in srgb, var(--color-primary) 8%, transparent)',
                      border: '1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)',
                    }}
                    onClick={() => onArrayAdd(fieldPath, field.item_children ?? [])}
                  >
                    + Add
                  </button>
                ) : type === 'dict' ? (
                  <div className="ml-auto flex items-center gap-1">
                    <input
                      value={newKeys[fieldName] || ''}
                      onChange={(e) => setNewKeys(prev => ({ ...prev, [fieldName]: e.target.value }))}
                      placeholder="key"
                      className="!text-[10px] !py-0.5 !px-1.5 !w-[72px] !rounded"
                    />
                    <button
                      type="button"
                      className="text-[10px] font-bold text-primary hover:text-primary-hover px-2 py-0.5 rounded transition-colors"
                      style={{
                        background: 'color-mix(in srgb, var(--color-primary) 8%, transparent)',
                        border: '1px solid color-mix(in srgb, var(--color-primary) 20%, transparent)',
                      }}
                      onClick={() => {
                        if (!newKeys[fieldName]) return;
                        onDictAdd(fieldPath, newKeys[fieldName], field.value_children ?? []);
                        setNewKeys(prev => ({ ...prev, [fieldName]: '' }));
                      }}
                    >
                      + Add
                    </button>
                  </div>
                ) : null}
              </div>
              {/* Collapsed items as pills */}
              <div className="flex flex-wrap gap-1.5">
                {items.map((item) => (
                  <div
                    key={item.id}
                    className="inline-flex items-center gap-1 rounded-full text-[10px] font-medium"
                    style={{
                      background: 'color-mix(in srgb, var(--color-primary) 7%, white)',
                      border: '1px solid color-mix(in srgb, var(--color-primary) 22%, transparent)',
                      padding: '2px 4px 2px 9px',
                    }}
                  >
                    <span className="text-text-muted max-w-[90px] truncate" title={item.label}>{item.label}</span>
                    {/* Expand */}
                    <button
                      type="button"
                      title="Expand"
                      className="w-4 h-4 rounded-full flex items-center justify-center text-primary hover:bg-primary hover:text-white transition-colors text-[9px] font-bold"
                      style={{ border: '1px solid color-mix(in srgb, var(--color-primary) 30%, transparent)' }}
                      onClick={() => onExpandChild(item.id)}
                    >
                      ↗
                    </button>
                    {/* Delete (not for object sub-classes) */}
                    {type !== 'object' && (
                      <button
                        type="button"
                        title="Delete"
                        className="w-4 h-4 rounded-full flex items-center justify-center text-danger hover:bg-danger hover:text-white transition-colors text-[9px] font-bold"
                        style={{ border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)' }}
                        onClick={() => type === 'array'
                          ? onArrayDelete(fieldPath, (item as { index: number }).index)
                          : onDictDelete(fieldPath, (item as { key: string }).key)
                        }
                      >
                        ✕
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const nodeTypes = { classNode: ClassNode };

/* ── Minimizable edge component ─────────────────────────────────── */

function MinimizableEdge({ sourceX, sourceY, targetX, targetY, data, style }: EdgeProps) {
  const [edgePath] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, borderRadius: 14 });
  const midX = (sourceX + targetX) / 2;
  const midY = (sourceY + targetY) / 2;
  const hasCollapse = data && (data as any).onCollapse;
  const isCollapsed = !!(data as any)?.isCollapsed;

  const edgeStyle = style as (Record<string, unknown> | undefined);
  return (
    <>
      <BaseEdge
        path={edgePath}
        style={{
          stroke: (edgeStyle?.stroke as string) ?? "var(--color-primary)",
          strokeWidth: (edgeStyle?.strokeWidth as number) ?? 1.5,
          opacity: (edgeStyle?.opacity as number) ?? 0.55,
        }}
      />
      {hasCollapse && (
        <g
          transform={`translate(${midX}, ${midY})`}
          style={{ cursor: 'pointer', pointerEvents: 'all' }}
          onClick={() => (data as any).onCollapse()}
        >
          {/* Shadow ring */}
          <circle r="10" fill="rgba(99,102,241,0.08)" />
          {/* Main circle */}
          <circle
            r="8"
            fill="white"
            stroke="var(--color-primary)"
            strokeWidth="1.5"
          />
          {/* Icon: minus to collapse, plus to expand */}
          <text
            textAnchor="middle"
            dominantBaseline="middle"
            fontSize="12"
            fontWeight="700"
            fill="var(--color-primary)"
            style={{ userSelect: 'none' }}
          >
            {isCollapsed ? '+' : '−'}
          </text>
        </g>
      )}
    </>
  );
}

const edgeTypes = { minimizable: MinimizableEdge };

function buildGraph(
  fields: NormalizedField[],
  rootLabel: string,
  value: Record<string, JsonValue>,
  collapsed: Set<string>,
  onToggle: (id: string) => void,
  onFieldChange: (path: string[], value: JsonValue) => void,
  onArrayAdd: (path: string[], children: NormalizedField[]) => void,
  onArrayDelete: (path: string[], index: number) => void,
  onDictAdd: (path: string[], key: string, children: NormalizedField[]) => void,
  onDictDelete: (path: string[], key: string) => void,
  collapsedItems: Set<string>,
  onCollapseChildren: (ids: string[]) => void,
  onExpandChild: (id: string) => void,
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function addClassNode(
    nodeId: string,
    label: string,
    badge: string | undefined,
    allFields: NormalizedField[],
    basePath: string[],
    itemDelete?: () => void,
  ) {
    const isCollapsed = collapsed.has(nodeId);
    const h = nodeHeight(allFields.length, isCollapsed);

    // Build ELK ports for each complex field (source handles)
    const elkPorts: ElkPort[] = [];
    if (!isCollapsed) {
      allFields.forEach((f, i) => {
        if (isComplex(f)) {
          elkPorts.push({
            id: `${nodeId}:field-${f.name}`,
            x: NODE_WIDTH,
            y: rowCenter(i),
            width: 6,
            height: 6,
          });
        }
      });
    }

    nodes.push({
      id: nodeId,
      type: "classNode",
      position: { x: 0, y: 0 },
      data: {
        label,
        badge,
        allFields,
        basePath,
        rootValue: value,
        onFieldChange,
        onArrayAdd,
        onArrayDelete,
        onDictAdd,
        onDictDelete,
        onCollapseChildren,
        onExpandChild,
        collapsed: isCollapsed,
        onToggle: () => onToggle(nodeId),
        nodeWidth: NODE_WIDTH,
        nodeHeight: h,
        elkPorts,
        itemDelete,
        collapsedChildren: {},
      },
    });

    if (isCollapsed) return;

    for (const field of allFields) {
      const fieldPath = [...basePath, field.name];
      const fieldId = fieldPath.join(".");
      const handleId = `field-${field.name}`;
      const elkPortId = `${nodeId}:${handleId}`;

      if (isNestedClass(field)) {
        const children = field.children ?? [];
        const classTitle = (typeof field.raw?.title === 'string' && field.raw.title) || field.title;
        if (collapsedItems.has(fieldId)) {
          // Show as pill inside parent
          const parentNode = nodes.find(n => n.id === nodeId)! as Node<ClassNodeData>;
          parentNode.data.collapsedChildren[field.name] = {
            type: 'object',
            items: [{ id: fieldId, label: friendlyName(field.name) }],
            field,
          };
        } else {
          addClassNode(fieldId, friendlyName(field.name), classTitle, children, fieldPath);
          edges.push({
            id: `edge:${nodeId}->${fieldId}`,
            source: nodeId,
            sourceHandle: handleId,
            target: fieldId,
            type: "minimizable",
            style: { stroke: "var(--color-primary)", strokeWidth: 1.5, opacity: 0.6 },
            data: {
              elkSourcePort: elkPortId,
              onCollapse: () => onCollapseChildren([fieldId]),
              isCollapsed: false,
            },
          });
        }
      } else if (isClassArray(field)) {
        const itemChildren = field.item_children ?? [];
        const arrValue = getAtPath(value, fieldPath);
        const arr = Array.isArray(arrValue) ? arrValue : [];
        const collapsedArrayItems: { id: string; label: string; index: number }[] = [];

        // Add items in order (index 0, 1, 2, ...)
        for (let idx = 0; idx < arr.length; idx++) {
          const itemId = `${fieldId}[${idx}]`;
          if (collapsedItems.has(itemId)) {
            collapsedArrayItems.push({ id: itemId, label: `${field.title} #${idx}`, index: idx });
          } else {
            const itemPath = [...fieldPath, String(idx)];
            const capturedIdx = idx;
            addClassNode(
              itemId, `${field.title} #${idx}`, "item", itemChildren, itemPath,
              () => onArrayDelete(fieldPath, capturedIdx),
            );
            edges.push({
              id: `edge:${nodeId}->${itemId}`,
              source: nodeId,
              sourceHandle: handleId,
              target: itemId,
              type: "minimizable",
              style: { stroke: "var(--color-primary)", strokeWidth: 1.5, opacity: 0.55 },
              data: {
                elkSourcePort: elkPortId,
                onCollapse: () => onCollapseChildren([itemId]),
                isCollapsed: false,
              },
            });
          }
        }

        if (collapsedArrayItems.length > 0) {
          (nodes.find(n => n.id === nodeId)! as Node<ClassNodeData>).data.collapsedChildren[field.name] = { type: 'array', items: collapsedArrayItems, field };
        }
      } else if (isClassDict(field)) {
        const valueChildren = field.value_children ?? [];
        const dictValue = getAtPath(value, fieldPath);
        const dict = dictValue && typeof dictValue === "object" && !Array.isArray(dictValue)
          ? dictValue as Record<string, JsonValue> : {};
        const collapsedDictItems: { id: string; label: string; key: string }[] = [];

        for (const key of Object.keys(dict).sort()) {
          const entryId = `${fieldId}.${key}`;
          if (collapsedItems.has(entryId)) {
            collapsedDictItems.push({ id: entryId, label: key, key });
          } else {
            const entryPath = [...fieldPath, key];
            const capturedKey = key;
            addClassNode(
              entryId, key, "entry", valueChildren, entryPath,
              () => onDictDelete(fieldPath, capturedKey),
            );
            edges.push({
              id: `edge:${nodeId}->${entryId}`,
              source: nodeId,
              sourceHandle: handleId,
              target: entryId,
              type: "minimizable",
              style: { stroke: "var(--color-primary)", strokeWidth: 1.5, opacity: 0.55 },
              data: {
                elkSourcePort: elkPortId,
                onCollapse: () => onCollapseChildren([entryId]),
                isCollapsed: false,
              },
            });
          }
        }

        if (collapsedDictItems.length > 0) {
          (nodes.find(n => n.id === nodeId)! as Node<ClassNodeData>).data.collapsedChildren[field.name] = { type: 'dict', items: collapsedDictItems, field };
        }
      }
    }
  }

  const rootId = "root";
  addClassNode(rootId, rootLabel, undefined, fields, []);

  const nodeIds = new Set(nodes.map((n) => n.id));
  const filteredEdges = edges.filter((edge) =>
    nodeIds.has(edge.source) && nodeIds.has(edge.target),
  );

  return { nodes, edges: filteredEdges };
}

/* ── Main component ─────────────────────────────────────────────── */

export function SchemaForm({ fields, value, onChange, classes, selectedClass, onClassChange, isEmpty }: Props) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [collapsedItems, setCollapsedItems] = useState<Set<string>>(new Set());
  const [flowNodes, setFlowNodes, onNodesChange] = useNodesState<Node>([]);
  const [flowEdges, setFlowEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [layoutDone, setLayoutDone] = useState(false);

  const onToggle = useCallback((id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const onFieldChange = useCallback(
    (path: string[], val: JsonValue) => onChange(setAtPath(value, path, val)),
    [value, onChange],
  );

  const onArrayAdd = useCallback(
    (path: string[], itemChildren: NormalizedField[]) => {
      const current = getAtPath(value, path);
      const arr = Array.isArray(current) ? current : [];
      onChange(setAtPath(value, path, [...arr, defaultObjectFromChildren(itemChildren)]));
    },
    [value, onChange],
  );

  const onArrayDelete = useCallback(
    (path: string[], index: number) => {
      const current = getAtPath(value, path);
      const arr = Array.isArray(current) ? current : [];
      onChange(setAtPath(value, path, arr.filter((_, i) => i !== index)));
    },
    [value, onChange],
  );

  const onDictAdd = useCallback(
    (path: string[], key: string, valueChildren: NormalizedField[]) => {
      const current = getAtPath(value, path);
      const dict = current && typeof current === "object" && !Array.isArray(current)
        ? current as Record<string, JsonValue> : {};
      onChange(setAtPath(value, path, { ...dict, [key]: defaultObjectFromChildren(valueChildren) }));
    },
    [value, onChange],
  );

  const onDictDelete = useCallback(
    (path: string[], key: string) => {
      const current = getAtPath(value, path);
      const dict = current && typeof current === "object" && !Array.isArray(current)
        ? { ...(current as Record<string, JsonValue>) } : {};
      delete dict[key];
      onChange(setAtPath(value, path, dict));
    },
    [value, onChange],
  );

  const onCollapseChildren = useCallback((ids: string[]) => {
    setCollapsedItems(prev => new Set([...prev, ...ids]));
  }, []);

  const onExpandChild = useCallback((id: string) => {
    setCollapsedItems(prev => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }, []);

  const rootLabel = selectedClass ? selectedClass.split(".").pop() ?? "Config" : "Config";

  const { nodes: rawNodes, edges: rawEdges } = useMemo(
    () => buildGraph(fields, rootLabel, value, collapsed, onToggle, onFieldChange, onArrayAdd, onArrayDelete, onDictAdd, onDictDelete, collapsedItems, onCollapseChildren, onExpandChild),
    [fields, rootLabel, value, collapsed, onToggle, onFieldChange, onArrayAdd, onArrayDelete, onDictAdd, onDictDelete, collapsedItems, onCollapseChildren, onExpandChild],
  );

  const structureKey = useMemo(
    () => rawNodes.map((n) => n.id).join("|") + "||" + rawEdges.map((e) => e.id).join("|"),
    [rawNodes, rawEdges],
  );

  const prevStructure = useRef(structureKey);

  useEffect(() => {
    if (rawNodes.length === 0) {
      setFlowNodes([]);
      setFlowEdges([]);
      prevStructure.current = structureKey;
      return;
    }

    if (structureKey !== prevStructure.current) {
      prevStructure.current = structureKey;
      setLayoutDone(false);
      layoutGraph(rawNodes, rawEdges).then((laid) => {
        setFlowNodes(laid);
        setFlowEdges(rawEdges);
        setLayoutDone(true);
      });
    } else {
      setFlowNodes((prev) =>
        prev.map((n) => {
          const raw = rawNodes.find((r) => r.id === n.id);
          return raw ? { ...n, data: raw.data } : n;
        }),
      );
      setFlowEdges(rawEdges);
    }
  }, [rawNodes, rawEdges, structureKey, setFlowNodes, setFlowEdges]);

  if (isEmpty) {
    return (
      <div className="bg-surface rounded-lg border border-border p-5 shadow-sm">
        <h2 className="m-0 mb-4 text-[15px] font-semibold flex items-center gap-2 pb-3 border-b border-border">
          <span className="text-base opacity-60">&#9998;</span>
          Schema Graph
        </h2>
        <div className="flex flex-col gap-3 py-4">
          <p className="text-[13px] text-text-muted m-0">File is empty. Choose a config class to start:</p>
          <select value={selectedClass} onChange={(e) => onClassChange(e.target.value)}>
            <option value="">-- pick class --</option>
            {classes.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-surface rounded-lg border border-border shadow-sm overflow-hidden" style={{ height: "80vh" }}>
      <div className="px-5 py-3 border-b border-border flex items-center justify-between">
        <h2 className="m-0 text-[15px] font-semibold flex items-center gap-2">
          <span className="text-base opacity-60">&#9998;</span>
          Schema Graph
        </h2>
        {selectedClass && (
          <span className="text-xs text-text-muted font-mono bg-surface-alt px-2 py-0.5 rounded">
            {selectedClass}
          </span>
        )}
      </div>
      <ReactFlow
        nodes={flowNodes}
        edges={flowEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.15}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        nodesDraggable
        nodesConnectable={false}
        style={{ opacity: layoutDone ? 1 : 0, transition: "opacity 0.2s" }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--color-border)" />
      </ReactFlow>
    </div>
  );
}
