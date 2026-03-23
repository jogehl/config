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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import ELK from "elkjs/lib/elk.bundled.js";
import type {
  ClassSchemaResponse,
  JsonValue,
  NormalizedField,
  ValidationIssue,
} from "../types";

/* ── Props ──────────────────────────────────────────────────────── */

type Props = {
  fields: NormalizedField[];
  value: Record<string, JsonValue>;
  onChange: (next: Record<string, JsonValue>) => void;
  classes: string[];
  selectedClass: string;
  onClassChange: (cls: string) => void;
  isEmpty: boolean;
  classSchemas: Record<string, ClassSchemaResponse>;
  validationIssues: ValidationIssue[];
  onInstantiateField: (path: string[], className: string) => void;
  onArrayAdd: (
    path: string[],
    children: NormalizedField[],
    className?: string,
  ) => void;
  onDictAdd: (
    path: string[],
    key: string,
    children: NormalizedField[],
    className?: string,
  ) => void;
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

function classNameLabel(className: string): string {
  return className.split(".").pop() ?? className;
}

function getConfigClassType(value: JsonValue | undefined): string | null {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    const classType = (value as Record<string, JsonValue>)._config_class_type;
    return typeof classType === "string" ? classType : null;
  }
  return null;
}

function hasIssueAtOrBelow(issues: ValidationIssue[], path: string[]): boolean {
  return issues.some((issue) =>
    path.every((part, index) => issue.path[index] === part),
  );
}

function issuesAtPath(issues: ValidationIssue[], path: string[]): ValidationIssue[] {
  return issues.filter(
    (issue) =>
      issue.path.length === path.length
      && issue.path.every((part, index) => part === path[index]),
  );
}

function hasDirectFieldIssues(
  issues: ValidationIssue[],
  path: string[],
): boolean {
  return issues.some(
    (issue) =>
      issue.path.length === path.length + 1
      && path.every((part, index) => issue.path[index] === part),
  );
}

function ErrorBadge({ message }: { message: string }) {
  return (
    <span className="scb-tooltip">
      <span
        className="inline-flex items-center justify-center shrink-0 rounded-full text-[9px] font-bold text-danger"
        style={{
          width: 14,
          height: 14,
          background: "color-mix(in srgb, var(--color-danger) 10%, white)",
          border: "1px solid color-mix(in srgb, var(--color-danger) 28%, transparent)",
        }}
        aria-label={message}
      >
        !
      </span>
      <span className="scb-tooltip-bubble">{message}</span>
    </span>
  );
}

function isCallableSchema(
  value: unknown,
): value is Record<string, unknown> {
  if (!value || typeof value !== "object") return false;
  const properties = (value as Record<string, unknown>).properties;
  if (!properties || typeof properties !== "object") return false;
  const typeField = (properties as Record<string, unknown>).type;
  if (!typeField || typeof typeField !== "object") return false;
  return (typeField as Record<string, unknown>).const === "callable";
}

function formatTypeLabel(field: NormalizedField): string {
  if (isCallableSchema(field.raw)) return "Callable";
  const rawSchema = field.raw as Record<string, unknown>;
  if (field.type === "array" && isCallableSchema(rawSchema.items)) {
    return "Callable[]";
  }
  if (
    field.type === "object"
    && isCallableSchema(rawSchema.additionalProperties)
  ) {
    return "dict<Callable>";
  }
  if (isNestedClass(field)) return configClassLabel(field);
  if (isClassArray(field)) return `${configClassLabel(field)}[]`;
  if (isClassDict(field)) return `dict<${configClassLabel(field)}>`;
  if (field.type === "array") return "array";
  if (field.type === "object" && field.raw && typeof field.raw === "object" && "additionalProperties" in field.raw) return "dict";
  return field.type ?? "unknown";
}

function isNestedClass(f: NormalizedField): boolean {
  return (
    f.type === "object"
    && (
      !!f.config_class
      || (Array.isArray(f.subclass_options) && f.subclass_options.length > 0)
      || (Array.isArray(f.children) && f.children.length > 0)
    )
  );
}

function isClassArray(f: NormalizedField): boolean {
  return (
    f.type === "array"
    && (
      !!f.item_config_class
      || (Array.isArray(f.item_subclass_options) && f.item_subclass_options.length > 0)
      || (Array.isArray(f.item_children) && f.item_children.length > 0)
    )
  );
}

function isClassDict(f: NormalizedField): boolean {
  return (
    f.type === "object"
    && !!(f.raw && typeof f.raw === "object" && "additionalProperties" in f.raw)
    && (
      !!f.value_config_class
      || (Array.isArray(f.value_subclass_options) && f.value_subclass_options.length > 0)
      || (Array.isArray(f.value_children) && f.value_children.length > 0)
    )
  );
}

function isComplex(f: NormalizedField): boolean {
  return isNestedClass(f) || isClassArray(f) || isClassDict(f);
}

/* ── Layout constants ───────────────────────────────────────────── */

const NODE_WIDTH = 408;
const HEADER_H = 42;
const ROW_H = 34;
const PAD_BOTTOM = 8;
const LABEL_W = 118;

type CollapsedChildItem = {
  id: string;
  label: string;
  index?: number;
  key?: string;
  hasError?: boolean;
};

type CollapsedChildGroup = {
  type: "array" | "dict" | "object";
  items: CollapsedChildItem[];
  field: NormalizedField;
};

function collapsedChildHeight(group?: CollapsedChildGroup): number {
  if (!group || group.items.length === 0) return 0;
  const pillsPerRow = 3;
  const rows = Math.ceil(group.items.length / pillsPerRow);
  return 8 + rows * 24;
}

function fieldHeight(field: NormalizedField, group?: CollapsedChildGroup): number {
  if (!isComplex(field)) return ROW_H;
  return ROW_H + collapsedChildHeight(group);
}

function nodeHeight(
  fields: NormalizedField[],
  collapsed: boolean,
  collapsedChildren: Record<string, CollapsedChildGroup>,
): number {
  if (collapsed) return HEADER_H;
  return (
    HEADER_H
    + fields.reduce(
      (total, field) => total + fieldHeight(field, collapsedChildren[field.name]),
      0,
    )
    + PAD_BOTTOM
  );
}

function rowCenter(
  fields: NormalizedField[],
  index: number,
  collapsedChildren: Record<string, CollapsedChildGroup>,
): number {
  const top = HEADER_H + fields
    .slice(0, index)
    .reduce(
      (total, field) => total + fieldHeight(field, collapsedChildren[field.name]),
      0,
    );
  return top + ROW_H / 2;
}

/* ── ELK layout with ports ──────────────────────────────────────── */

const elk = new ELK();

type ElkPort = { id: string; x: number; y: number; width: number; height: number };

type RoutedPoint = { x: number; y: number };

function distance(a: RoutedPoint, b: RoutedPoint): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

function moveToward(from: RoutedPoint, to: RoutedPoint, amount: number): RoutedPoint {
  const total = distance(from, to);
  if (total === 0) return from;
  const ratio = Math.min(amount / total, 1);
  return {
    x: from.x + (to.x - from.x) * ratio,
    y: from.y + (to.y - from.y) * ratio,
  };
}

function edgePathFromPoints(points: RoutedPoint[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;

  const radius = 14;
  let path = `M ${points[0].x} ${points[0].y}`;

  for (let index = 1; index < points.length - 1; index++) {
    const prev = points[index - 1];
    const current = points[index];
    const next = points[index + 1];

    const incoming = Math.min(radius, distance(prev, current) / 2);
    const outgoing = Math.min(radius, distance(current, next) / 2);

    const curveStart = moveToward(current, prev, incoming);
    const curveEnd = moveToward(current, next, outgoing);
    const controlIn = moveToward(curveStart, current, incoming * 0.6);
    const controlOut = moveToward(curveEnd, current, outgoing * 0.6);

    path += ` L ${curveStart.x} ${curveStart.y}`;
    path += ` C ${controlIn.x} ${controlIn.y} ${controlOut.x} ${controlOut.y} ${curveEnd.x} ${curveEnd.y}`;
  }

  const last = points[points.length - 1];
  path += ` L ${last.x} ${last.y}`;
  return path;
}

function edgeMidpointFromPoints(
  points: RoutedPoint[],
  fallback: RoutedPoint,
): RoutedPoint {
  if (points.length < 2) return fallback;

  const segments = points.slice(1).map((point, index) => {
    const start = points[index];
    const dx = point.x - start.x;
    const dy = point.y - start.y;
    return {
      start,
      end: point,
      length: Math.hypot(dx, dy),
    };
  });

  const totalLength = segments.reduce((sum, segment) => sum + segment.length, 0);
  if (totalLength === 0) return fallback;

  const targetLength = totalLength / 2;
  let traversed = 0;

  for (const segment of segments) {
    if (traversed + segment.length >= targetLength) {
      const ratio = (targetLength - traversed) / segment.length;
      return {
        x: segment.start.x + (segment.end.x - segment.start.x) * ratio,
        y: segment.start.y + (segment.end.y - segment.start.y) * ratio,
      };
    }
    traversed += segment.length;
  }

  return fallback;
}

async function layoutGraph(
  nodes: Node[],
  edges: Edge[],
): Promise<{ nodes: Node[]; edges: Edge[] }> {
  const elkGraph = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": "RIGHT",
      "elk.edgeRouting": "ORTHOGONAL",
      "elk.spacing.nodeNode": "56",
      "elk.spacing.edgeEdge": "20",
      "elk.layered.spacing.nodeNodeBetweenLayers": "120",
      "elk.layered.spacing.edgeNodeBetweenLayers": "56",
      "elk.layered.crossingMinimization.strategy": "LAYER_SWEEP",
      "elk.layered.thoroughness": "12",
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
        properties: {
          "elk.port.side": p.x <= 0 ? "WEST" : "EAST",
        },
      })),
    })),
    edges: edges.map((e) => ({
      id: e.id,
      sources: [e.data?.elkSourcePort as string ?? e.source],
      targets: [e.data?.elkTargetPort as string ?? e.target],
    })),
  };
  const layout = await elk.layout(elkGraph);
  const laidOutNodes = nodes.map((node) => {
    const elkNode = layout.children?.find((n) => n.id === node.id);
    return { ...node, position: { x: elkNode?.x ?? 0, y: elkNode?.y ?? 0 } };
  });
  const laidOutEdges = edges.map((edge) => {
    const elkEdge = (layout.edges as Array<{ id: string; sections?: Array<{ startPoint?: RoutedPoint; bendPoints?: RoutedPoint[]; endPoint?: RoutedPoint }> }> | undefined)
      ?.find((candidate) => candidate.id === edge.id);
    const section = elkEdge?.sections?.[0];
    const points: RoutedPoint[] = [];
    if (section?.startPoint) points.push(section.startPoint);
    if (section?.bendPoints?.length) points.push(...section.bendPoints);
    if (section?.endPoint) points.push(section.endPoint);
    return {
      ...edge,
      data: {
        ...edge.data,
        elkPoints: points,
      },
    };
  });
  return { nodes: laidOutNodes, edges: laidOutEdges };
}

/* ── Node data type ─────────────────────────────────────────────── */

type ClassNodeData = {
  label: string;
  badge?: string;
  allFields: NormalizedField[];
  basePath: string[];
  rootValue: Record<string, JsonValue>;
  onFieldChange: (path: string[], value: JsonValue) => void;
  onInstantiateField: (path: string[], className: string) => void;
  onArrayAdd: (
    path: string[],
    children: NormalizedField[],
    className?: string,
  ) => void;
  onArrayDelete: (path: string[], index: number) => void;
  onDictAdd: (
    path: string[],
    key: string,
    children: NormalizedField[],
    className?: string,
  ) => void;
  onDictDelete: (path: string[], key: string) => void;
  onCollapseChildren: (ids: string[]) => void;
  onExpandChild: (id: string) => void;
  collapsed: boolean;
  onToggle: () => void;
  nodeWidth: number;
  nodeHeight: number;
  elkPorts: ElkPort[];
  itemDelete?: () => void;
  collapsedChildren: Record<string, CollapsedChildGroup>;
  validationIssues: ValidationIssue[];
  [key: string]: unknown;
};

/** Human-friendly label from a field name (e.g. "sub_key" -> "Sub Key"). */
function friendlyName(name: string): string {
  return name.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function configClassLabel(field: NormalizedField): string {
  if (field.config_class) return classNameLabel(field.config_class);
  if (field.item_config_class) return classNameLabel(field.item_config_class);
  if (field.value_config_class) return classNameLabel(field.value_config_class);
  if (isClassArray(field)) {
    const itemTitle = field.raw?.items;
    if (itemTitle && typeof itemTitle === "object" && "title" in itemTitle) {
      const title = itemTitle.title;
      if (typeof title === "string" && title) return title;
    }
  }
  if (isClassDict(field)) {
    const valueSchema = field.raw?.additionalProperties;
    if (
      valueSchema
      && typeof valueSchema === "object"
      && "title" in valueSchema
    ) {
      const title = valueSchema.title;
      if (typeof title === "string" && title) return title;
    }
  }
  const title = field.raw?.title;
  if (typeof title === "string" && title) return title;
  return field.title || friendlyName(field.name);
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
  field, path, rootValue, onFieldChange, validationIssues,
}: {
  field: NormalizedField;
  path: string[];
  rootValue: Record<string, JsonValue>;
  onFieldChange: (path: string[], value: JsonValue) => void;
  validationIssues: ValidationIssue[];
}) {
  const fieldPath = [...path, field.name];
  const current = getAtPath(rootValue, fieldPath);
  const fieldIssues = issuesAtPath(validationIssues, fieldPath);
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
          className={`text-[10px] leading-tight font-medium shrink-0 truncate ${fieldIssues.length > 0 ? "text-danger" : "text-text"}`}
          style={{ width: LABEL_W }}
          title={field.title}
        >
          {field.title}
          {field.required && <span className="text-danger ml-0.5">*</span>}
        </span>
        <span className="text-[8px] leading-tight font-mono text-primary bg-primary-ghost px-1 rounded shrink-0">
          {formatTypeLabel(field)}
        </span>
        {fieldIssues.length > 0 && (
          <ErrorBadge message={fieldIssues[0].message} />
        )}
      </div>
      <div className={isPrimitiveContainer ? '' : 'flex-1 min-w-[116px]'}>
        {field.enum && field.enum.length > 0 ? (
          <select value={String(current ?? "")} onChange={handleChange} className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 w-full">
            <option value="">--</option>
            {field.enum.map((v) => <option key={String(v)} value={String(v)}>{String(v)}</option>)}
          </select>
        ) : field.type === "boolean" ? (
          <select value={String(current ?? "false")} onChange={handleChange} className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 w-full">
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
            className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 font-mono w-full"
          />
        ) : (
          <input
            type={field.type === "number" || field.type === "integer" ? "number" : "text"}
            value={asString}
            onChange={handleChange}
            className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 w-full"
          />
        )}
      </div>
    </div>
  );
}

/* ── Complex field row (nested object / array / dict) ───────────── */

function ComplexRow({
  field,
  index,
  allFields,
  basePath,
  rootValue,
  onInstantiateField,
  onArrayAdd,
  onArrayDelete,
  onDictAdd,
  onDictDelete,
  onExpandChild,
  collapsedChild,
  collapsedChildren,
  validationIssues,
}: {
  field: NormalizedField;
  index: number;
  allFields: NormalizedField[];
  basePath: string[];
  rootValue: Record<string, JsonValue>;
  onInstantiateField: (path: string[], className: string) => void;
  onArrayAdd: (
    path: string[],
    children: NormalizedField[],
    className?: string,
  ) => void;
  onArrayDelete: (path: string[], index: number) => void;
  onDictAdd: (
    path: string[],
    key: string,
    children: NormalizedField[],
    className?: string,
  ) => void;
  onDictDelete: (path: string[], key: string) => void;
  onExpandChild: (id: string) => void;
  collapsedChild?: CollapsedChildGroup;
  collapsedChildren: Record<string, CollapsedChildGroup>;
  validationIssues: ValidationIssue[];
}) {
  const [newKey, setNewKey] = useState("");
  const [selectedSubclass, setSelectedSubclass] = useState(
    field.subclass_options[0] ?? "",
  );
  const [selectedArraySubclass, setSelectedArraySubclass] = useState(
    field.item_subclass_options[0] ?? "",
  );
  const [selectedDictSubclass, setSelectedDictSubclass] = useState(
    field.value_subclass_options[0] ?? "",
  );
  const fieldPath = [...basePath, field.name];
  const current = getAtPath(rootValue, fieldPath);
  const currentClassType = getConfigClassType(current);
  const fieldIssues = issuesAtPath(validationIssues, fieldPath);
  const nestedIssues = hasIssueAtOrBelow(validationIssues, fieldPath);

  let countLabel = "";
  if (isClassArray(field)) {
    const arr = Array.isArray(current) ? current : [];
    countLabel = `[${arr.length}]`;
  } else if (isClassDict(field)) {
    const dict = current && typeof current === "object" && !Array.isArray(current) ? current as Record<string, JsonValue> : {};
    countLabel = `[${Object.keys(dict).length}]`;
  }

  return (
    <div className="px-3 py-0.5">
      {/* Source handle — top is relative to the node root (no position:relative here) */}
      <Handle
        type="source"
        position={Position.Right}
        id={`field-${field.name}`}
        className="!bg-primary !w-2.5 !h-2.5 !border-primary/50 !border-2"
        style={{
          top: rowCenter(
            allFields,
            index,
            collapsedChildren,
          ),
        }}
      />

      <div className="flex items-center gap-1.5" style={{ minHeight: ROW_H }}>
        <span
          className={`text-[10px] leading-tight font-semibold shrink-0 truncate ${nestedIssues ? "text-danger" : "text-text"}`}
          style={{ width: LABEL_W }}
          title={field.name}
        >
          {friendlyName(field.name)}
        </span>
        <span className="text-[8px] leading-tight font-mono text-primary bg-primary-ghost px-1 rounded shrink-0">
          {(currentClassType ? classNameLabel(currentClassType) : formatTypeLabel(field))}{countLabel}
        </span>
        {fieldIssues.length > 0 && (
          <ErrorBadge message={fieldIssues[0].message} />
        )}

        {field.subclass_options.length > 0 && !currentClassType && isNestedClass(field) && (
          <div className="flex items-center gap-1 ml-auto shrink-0">
            <select
              value={selectedSubclass}
              onChange={(e) => setSelectedSubclass(e.target.value)}
              className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 !w-[132px]"
              onClick={(e) => e.stopPropagation()}
            >
              {field.subclass_options.map((option) => (
                <option key={option} value={option}>
                  {classNameLabel(option)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="text-[10px] bg-surface-alt text-text border border-border hover:bg-border px-1.5 py-0 rounded"
              onClick={(e) => {
                e.stopPropagation();
                if (selectedSubclass) onInstantiateField(fieldPath, selectedSubclass);
              }}
            >
              Create
            </button>
          </div>
        )}

        {isClassArray(field) && (
          <div className="flex items-center gap-1 ml-auto shrink-0">
            {field.item_subclass_options.length > 0 && (
              <select
                value={selectedArraySubclass}
                onChange={(e) => setSelectedArraySubclass(e.target.value)}
                className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 !w-[132px]"
                onClick={(e) => e.stopPropagation()}
              >
                {field.item_subclass_options.map((option) => (
                  <option key={option} value={option}>
                    {classNameLabel(option)}
                  </option>
                ))}
              </select>
            )}
            <button
              type="button"
              className="text-[10px] bg-surface-alt text-text border border-border hover:bg-border px-1.5 py-0 rounded shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onArrayAdd(
                  fieldPath,
                  field.item_children ?? [],
                  selectedArraySubclass || undefined,
                );
              }}
            >
              +
            </button>
          </div>
        )}

        {isClassDict(field) && (
          <div className="flex items-center gap-1 ml-auto shrink-0">
            {field.value_subclass_options.length > 0 && (
              <select
                value={selectedDictSubclass}
                onChange={(e) => setSelectedDictSubclass(e.target.value)}
                className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 !w-[132px]"
                onClick={(e) => e.stopPropagation()}
              >
                {field.value_subclass_options.map((option) => (
                  <option key={option} value={option}>
                    {classNameLabel(option)}
                  </option>
                ))}
              </select>
            )}
            <input
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
              placeholder="key"
              className="!text-[10px] !leading-tight !min-h-[24px] !py-0.5 !px-1.5 !w-[68px]"
              onClick={(e) => e.stopPropagation()}
            />
            <button
              type="button"
              className="text-[10px] bg-surface-alt text-text border border-border hover:bg-border px-1.5 py-0 rounded"
              onClick={(e) => {
                e.stopPropagation();
                if (!newKey) return;
                onDictAdd(
                  fieldPath,
                  newKey,
                  field.value_children ?? [],
                  selectedDictSubclass || undefined,
                );
                setNewKey("");
              }}
            >
              +
            </button>
          </div>
        )}
      </div>

      {collapsedChild && collapsedChild.items.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pb-1 pl-[118px]">
          {collapsedChild.items.map((item) => (
            <div
              key={item.id}
              className="inline-flex items-center gap-1 rounded-full text-[10px] font-medium"
              style={{
                background: item.hasError
                  ? 'color-mix(in srgb, var(--color-danger) 8%, white)'
                  : 'color-mix(in srgb, var(--color-primary) 7%, white)',
                border: item.hasError
                  ? '1px solid color-mix(in srgb, var(--color-danger) 28%, transparent)'
                  : '1px solid color-mix(in srgb, var(--color-primary) 22%, transparent)',
                padding: '2px 4px 2px 9px',
              }}
            >
              <span className={`${item.hasError ? "text-danger" : "text-text-muted"} max-w-[90px] truncate`} title={item.label}>{item.label}</span>
              <button
                type="button"
                title="Expand"
                className="w-4 h-4 rounded-full flex items-center justify-center text-primary hover:bg-primary hover:text-white transition-colors text-[9px] font-bold"
                style={{ border: '1px solid color-mix(in srgb, var(--color-primary) 30%, transparent)' }}
                onClick={() => onExpandChild(item.id)}
              >
                ↗
              </button>
              {collapsedChild.type !== 'object' && (
                <button
                  type="button"
                  title="Delete"
                  className="w-4 h-4 rounded-full flex items-center justify-center text-danger hover:bg-danger hover:text-white transition-colors text-[9px] font-bold"
                  style={{ border: '1px solid color-mix(in srgb, var(--color-danger) 30%, transparent)' }}
                  onClick={() => collapsedChild.type === 'array'
                    ? onArrayDelete(fieldPath, item.index ?? -1)
                    : onDictDelete(fieldPath, item.key ?? "")
                  }
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Class node component ───────────────────────────────────────── */

function ClassNode({ data }: NodeProps<Node<ClassNodeData>>) {
  const {
    label, badge, allFields, basePath, rootValue, onFieldChange,
    onInstantiateField, onArrayAdd, onArrayDelete, onDictAdd, onDictDelete, onCollapseChildren, onExpandChild,
    collapsed, onToggle, itemDelete, collapsedChildren, validationIssues,
  } = data;
  const nodeHasIssues = hasDirectFieldIssues(validationIssues, basePath);

  return (
    <div style={{ width: NODE_WIDTH }}>
      {/* Target handle */}
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-primary !w-3 !h-3 !border-2 !border-white"
        style={{
          top: "50%",
          transform: "translateY(-50%)",
          boxShadow: '0 0 0 1.5px var(--color-primary)',
        }}
      />

      <div
        className="bg-surface rounded-lg shadow-md overflow-visible"
        style={{
          border: collapsed
            ? `2px solid ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'}`
            : `1.5px solid color-mix(in srgb, ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'} 28%, transparent)`,
          boxShadow: collapsed
            ? `0 0 0 3px color-mix(in srgb, ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'} 10%, transparent), 0 2px 8px rgba(0,0,0,0.07)`
            : '0 2px 8px rgba(0,0,0,0.06)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-2 px-3 cursor-pointer select-none transition-colors"
          style={{
            height: HEADER_H,
            background: collapsed
              ? `color-mix(in srgb, ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'} 12%, transparent)`
              : `color-mix(in srgb, ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'} 5%, transparent)`,
            borderBottom: collapsed ? 'none' : `1px solid color-mix(in srgb, ${nodeHasIssues ? 'var(--color-danger)' : 'var(--color-primary)'} 18%, transparent)`,
            borderRadius: collapsed ? '8px' : '8px 8px 0 0',
          }}
          onClick={onToggle}
        >
          <span
            className={`${nodeHasIssues ? "text-danger" : "text-primary"} transition-transform duration-200 text-[10px]`}
            style={{ transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)', display: 'inline-block' }}
          >
            &#9660;
          </span>
          <span className={`font-bold text-[13px] truncate flex-1 ${nodeHasIssues ? "text-danger" : "text-text"}`}>{label}</span>
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
              allFields={allFields}
              basePath={basePath}
              rootValue={rootValue}
              onInstantiateField={onInstantiateField}
              onArrayAdd={onArrayAdd}
              onArrayDelete={onArrayDelete}
              onDictAdd={onDictAdd}
              onDictDelete={onDictDelete}
              onExpandChild={onExpandChild}
              collapsedChild={collapsedChildren[field.name]}
              collapsedChildren={collapsedChildren}
              validationIssues={validationIssues}
            />
          ) : (
            <PrimitiveRow
              key={field.name}
              field={field}
              path={basePath}
              rootValue={rootValue}
              onFieldChange={onFieldChange}
              validationIssues={validationIssues}
            />
          ),
        )}
      </div>
    </div>
  );
}

const nodeTypes = { classNode: ClassNode };

/* ── Minimizable edge component ─────────────────────────────────── */

function MinimizableEdge({ sourceX, sourceY, targetX, targetY, data, style }: EdgeProps) {
  const routedPoints = Array.isArray((data as { elkPoints?: RoutedPoint[] } | undefined)?.elkPoints)
    ? ((data as { elkPoints?: RoutedPoint[] }).elkPoints ?? [])
    : [];
  const edgePath = routedPoints.length > 1
    ? edgePathFromPoints(routedPoints)
    : `M ${sourceX} ${sourceY} L ${targetX} ${targetY}`;
  const midpoint = edgeMidpointFromPoints(routedPoints, {
    x: (sourceX + targetX) / 2,
    y: (sourceY + targetY) / 2,
  });
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
          transform={`translate(${midpoint.x}, ${midpoint.y})`}
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
  classSchemas: Record<string, ClassSchemaResponse>,
  validationIssues: ValidationIssue[],
  collapsed: Set<string>,
  onToggle: (id: string) => void,
  onFieldChange: (path: string[], value: JsonValue) => void,
  onInstantiateField: (path: string[], className: string) => void,
  onArrayAdd: (
    path: string[],
    children: NormalizedField[],
    className?: string,
  ) => void,
  onArrayDelete: (path: string[], index: number) => void,
  onDictAdd: (
    path: string[],
    key: string,
    children: NormalizedField[],
    className?: string,
  ) => void,
  onDictDelete: (path: string[], key: string) => void,
  collapsedItems: Set<string>,
  onCollapseChildren: (ids: string[]) => void,
  onExpandChild: (id: string) => void,
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function collectCollapsedChildren(
    allFields: NormalizedField[],
    basePath: string[],
  ): Record<string, CollapsedChildGroup> {
    const groups: Record<string, CollapsedChildGroup> = {};

    for (const field of allFields) {
      const fieldPath = [...basePath, field.name];
      const fieldId = fieldPath.join(".");

      if (isNestedClass(field) && collapsedItems.has(fieldId)) {
        groups[field.name] = {
          type: "object",
          items: [{
            id: fieldId,
            label: friendlyName(field.name),
            hasError: hasIssueAtOrBelow(validationIssues, fieldPath),
          }],
          field,
        };
        continue;
      }

      if (isClassArray(field)) {
        const arrValue = getAtPath(value, fieldPath);
        const arr = Array.isArray(arrValue) ? arrValue : [];
        const items = arr
          .map((_, idx) => ({
            id: `${fieldId}[${idx}]`,
            label: `${configClassLabel(field)} #${idx}`,
            index: idx,
            hasError: hasIssueAtOrBelow(
              validationIssues,
              [...fieldPath, String(idx)],
            ),
          }))
          .filter((item) => collapsedItems.has(item.id));
        if (items.length > 0) groups[field.name] = { type: "array", items, field };
        continue;
      }

      if (isClassDict(field)) {
        const dictValue = getAtPath(value, fieldPath);
        const dict = dictValue && typeof dictValue === "object" && !Array.isArray(dictValue)
          ? dictValue as Record<string, JsonValue>
          : {};
        const items = Object.keys(dict)
          .sort()
          .map((key) => ({
            id: `${fieldId}.${key}`,
            label: key,
            key,
            hasError: hasIssueAtOrBelow(validationIssues, [...fieldPath, key]),
          }))
          .filter((item) => collapsedItems.has(item.id));
        if (items.length > 0) groups[field.name] = { type: "dict", items, field };
      }
    }

    return groups;
  }

  function addClassNode(
    nodeId: string,
    label: string,
    badge: string | undefined,
    allFields: NormalizedField[],
    basePath: string[],
    itemDelete?: () => void,
  ) {
    const isCollapsed = collapsed.has(nodeId);
    const collapsedChildren = collectCollapsedChildren(allFields, basePath);
    const h = nodeHeight(allFields, isCollapsed, collapsedChildren);

    // Build ELK ports for each complex field (source handles)
    const elkPorts: ElkPort[] = [];
    elkPorts.push({
      id: `${nodeId}:target`,
      x: 0,
      y: h / 2,
      width: 8,
      height: 8,
    });
    if (!isCollapsed) {
      allFields.forEach((f, i) => {
        if (isComplex(f)) {
          elkPorts.push({
            id: `${nodeId}:field-${f.name}`,
            x: NODE_WIDTH,
            y: rowCenter(allFields, i, collapsedChildren),
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
        onInstantiateField,
        onArrayAdd,
        onArrayDelete,
        onDictAdd,
        onDictDelete,
        onCollapseChildren,
        onExpandChild,
        validationIssues,
        collapsed: isCollapsed,
        onToggle: () => onToggle(nodeId),
        nodeWidth: NODE_WIDTH,
        nodeHeight: h,
        elkPorts,
        itemDelete,
        collapsedChildren,
      },
    });

    if (isCollapsed) return;

    for (const field of allFields) {
      const fieldPath = [...basePath, field.name];
      const fieldId = fieldPath.join(".");
      const handleId = `field-${field.name}`;
      const elkPortId = `${nodeId}:${handleId}`;

      if (isNestedClass(field)) {
        const currentValue = getAtPath(value, fieldPath);
        const currentClassType = getConfigClassType(currentValue);
        if (field.subclass_options.length > 0 && !currentClassType) {
          continue;
        }
        const children = currentClassType && classSchemas[currentClassType]
          ? classSchemas[currentClassType].normalized_schema.fields
          : (field.children ?? []);
        const classTitle = currentClassType
          ? classNameLabel(currentClassType)
          : configClassLabel(field);
        if (collapsedItems.has(fieldId)) {
          continue;
        }
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
              elkTargetPort: `${fieldId}:target`,
              onCollapse: () => onCollapseChildren([fieldId]),
              isCollapsed: false,
            },
        });
      } else if (isClassArray(field)) {
        const arrValue = getAtPath(value, fieldPath);
        const arr = Array.isArray(arrValue) ? arrValue : [];

        // Add items in order (index 0, 1, 2, ...)
        for (let idx = 0; idx < arr.length; idx++) {
          const itemId = `${fieldId}[${idx}]`;
          if (collapsedItems.has(itemId)) {
            continue;
          } else {
            const itemPath = [...fieldPath, String(idx)];
            const capturedIdx = idx;
            const currentClassType = getConfigClassType(arr[idx]);
            const itemChildren = currentClassType && classSchemas[currentClassType]
              ? classSchemas[currentClassType].normalized_schema.fields
              : (field.item_children ?? []);
            addClassNode(
              itemId,
              `${currentClassType ? classNameLabel(currentClassType) : configClassLabel(field)} #${idx}`,
              "item",
              itemChildren,
              itemPath,
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
                elkTargetPort: `${itemId}:target`,
                onCollapse: () => onCollapseChildren([itemId]),
                isCollapsed: false,
              },
            });
          }
        }
      } else if (isClassDict(field)) {
        const dictValue = getAtPath(value, fieldPath);
        const dict = dictValue && typeof dictValue === "object" && !Array.isArray(dictValue)
          ? dictValue as Record<string, JsonValue> : {};

        for (const key of Object.keys(dict).sort()) {
          const entryId = `${fieldId}.${key}`;
          if (collapsedItems.has(entryId)) {
            continue;
          } else {
            const entryPath = [...fieldPath, key];
            const capturedKey = key;
            const currentClassType = getConfigClassType(dict[key]);
            const valueChildren = currentClassType && classSchemas[currentClassType]
              ? classSchemas[currentClassType].normalized_schema.fields
              : (field.value_children ?? []);
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
                elkTargetPort: `${entryId}:target`,
                onCollapse: () => onCollapseChildren([entryId]),
                isCollapsed: false,
              },
            });
          }
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

export function SchemaForm({
  fields,
  value,
  onChange,
  classes,
  selectedClass,
  onClassChange,
  isEmpty,
  classSchemas,
  validationIssues,
  onInstantiateField,
  onArrayAdd: onArrayAddProp,
  onDictAdd: onDictAddProp,
}: Props) {
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

  const onArrayDelete = useCallback(
    (path: string[], index: number) => {
      const current = getAtPath(value, path);
      const arr = Array.isArray(current) ? current : [];
      onChange(setAtPath(value, path, arr.filter((_, i) => i !== index)));
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
    () => buildGraph(
      fields,
      rootLabel,
      value,
      classSchemas,
      validationIssues,
      collapsed,
      onToggle,
      onFieldChange,
      onInstantiateField,
      onArrayAddProp,
      onArrayDelete,
      onDictAddProp,
      onDictDelete,
      collapsedItems,
      onCollapseChildren,
      onExpandChild,
    ),
    [fields, rootLabel, value, classSchemas, validationIssues, collapsed, onToggle, onFieldChange, onInstantiateField, onArrayAddProp, onArrayDelete, onDictAddProp, onDictDelete, collapsedItems, onCollapseChildren, onExpandChild],
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
        setFlowNodes(laid.nodes);
        setFlowEdges(laid.edges);
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
