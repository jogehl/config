// NEW: dagre import (ESM)
import dagre from "dagre";

import {
  ReactFlow, Background, Controls, MiniMap, Handle, Position,
  addEdge, applyNodeChanges, applyEdgeChanges
} from "@xyflow/react";
import { useCallback, useMemo, useEffect, useState } from "react";

// Hilfsfunktion: String -> XYFlow Position
function getPosition(pos) {
  switch (pos) {
    case "Bottom": return Position.Bottom;
    case "Left":   return Position.Left;
    case "Right":  return Position.Right;
    default:       return Position.Top; // "Top"
  }
}

// ---- DAGRE LAYOUT ------------------------------------------------------------

/**
 * Wendet dagre-Layout auf Nodes/Edges an und gibt neue Arrays zurück.
 * direction: "TB" | "LR" (Top->Bottom bzw. Left->Right)
 * nodesep/ranksep: Abstände (px)
 * width/height werden aus node.data.width/height gelesen, sonst Fallbacks.
 */
function layoutWithDagre(nodes, edges, {
  direction = "TB",
  nodesep = 50,
  ranksep = 80,
  fallbackSize = { w: 220, h: 80 }
}) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: direction, nodesep, ranksep });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((n) => {
    const w = n?.data?.width ? Number(n.data.width) : fallbackSize.w;
    const h = n?.data?.height ? Number(n.data.height) : fallbackSize.h;
    g.setNode(n.id, { width: w, height: h });
  });

  edges.forEach((e) => {
    // dagre erwartet nur source/target (sourceHandle/targetHandle egal)
    g.setEdge(e.source, e.target);
  });

  dagre.layout(g);

  const nodeMap = new Map(nodes.map((n) => [n.id, n]));
  g.nodes().forEach((id) => {
    const n = nodeMap.get(id);
    if (!n) return;
    const pos = g.node(id); // {x, y, width, height}
    // React Flow erwartet top-left Position; dagre liefert center.
    const x = pos.x - pos.width / 2;
    const y = pos.y - pos.height / 2;
    n.position = { x, y };
  });

  // Edges unverändert zurückgeben
  return {
    nodes: nodes.map((n) => ({ ...n })), // Kopien
    edges: edges.map((e) => ({ ...e }))
  };
}

// ---- PANEL NODE --------------------------------------------------------------

function PanelNode({ data, model }) {
  const nodeStyle = {
    padding: 0,
    border: `${data.border_width || 1}px solid ${data.border_color || "#ddd"}`,
    borderRadius: `${data.border_radius || 8}px`,
    backgroundColor: data.background_color || "white",
    minWidth: data.width ? `${data.width}px` : "auto",
    minHeight: data.height ? `${data.height}px` : "auto",
    position: "relative",
    overflow: "hidden"
  };

  const contentStyle = {
    padding: `${data.padding || 10}px`,
    minHeight: "100%"
  };

  // Panel-Kind rendern
  const children = model.get_child("objects");
  
  // Access the node_keys directly from model state (not object_keys)
  const [keys] = model.useState("node_keys");
  
  // get the index from object keys by node id and use it as index in objects
  const index = (keys && Array.isArray(keys)) ? keys.indexOf(data.node_id) : -1;
  const child = (index >= 0 && children && Array.isArray(children)) ? children[index] : null;

  // Handles (einfach: has_input_handle / has_output_handle)
  return (
    <div style={nodeStyle}>
      {data.has_input_handle && (
        <Handle type="target" position={getPosition(data.input_handle_position || "Top")} />
      )}
      <div style={contentStyle}>
        {child || <div style={{ color: "#666", fontStyle: "italic" }}>No content</div>}
      </div>
      {data.has_output_handle && (
        <Handle type="source" position={getPosition(data.output_handle_position || "Bottom")} />
      )}
    </div>
  );
}

export function render({ model }) {
  const [nodes, setNodes] = model.useState("nodes");
  const [edges, setEdges] = model.useState("edges");
  const [fitView] = model.useState("fit_view");

  // NEW: Panel-Parameter lesen
  // Boolean: ob dagre benutzt werden soll
  const [useDagre] = model.useState("use_dagre");            // <-- kommt aus Python
  // Optionen (optional)
  const [dagreDirection] = model.useState("dagre_direction"); // "TB" | "LR"
  const [dagreNodeSep] = model.useState("dagre_nodesep");     // Zahl
  const [dagreRankSep] = model.useState("dagre_ranksep");     // Zahl

  const nodeTypes = useMemo(
    () => ({ panelNode: (props) => <PanelNode {...props} model={model} /> }),
    [model]
  );

  // **Anzeige-Daten**: ggf. gelayoutete Kopien der Nodes/Edges
  const { displayNodes, displayEdges } = useMemo(() => {
    if (!useDagre) {
      return { displayNodes: nodes, displayEdges: edges };
    }
    // Tiefe Kopien, damit wir state nicht mutieren
    const nCopy = nodes.map((n) => ({ ...n, data: { ...n.data } }));
    const eCopy = edges.map((e) => ({ ...e }));
    const { nodes: laidOutNodes, edges: laidOutEdges } = layoutWithDagre(nCopy, eCopy, {
      direction: dagreDirection || "TB",
      nodesep: typeof dagreNodeSep === "number" ? dagreNodeSep : 50,
      ranksep: typeof dagreRankSep === "number" ? dagreRankSep : 80
    });
    return { displayNodes: laidOutNodes, displayEdges: laidOutEdges };
  }, [nodes, edges, useDagre, dagreDirection, dagreNodeSep, dagreRankSep]);

  const onNodesChange = useCallback(
    (changes) => {
      // Use setNodes with a function to get the most current state
      setNodes((currentNodes) => {
        const next = applyNodeChanges(changes, currentNodes);
        model.send_event("nodes_change", new CustomEvent("nodes_change", { detail: { nodes: next } }));
        return next;
      });
    },
    [] // Remove nodes dependency to avoid stale closure
  );

  const onEdgeClick = useCallback((event, edge) => {
    // edge = the clicked edge object
    model.send_event(
      "edge_click",
      new CustomEvent("edge_click", { detail: { edge } })
    );
  }, []);

  const onEdgesChange = useCallback(
    (changes) => {
      // Use setEdges with a function to get the most current state
      setEdges((currentEdges) => {
        const next = applyEdgeChanges(changes, currentEdges);
        model.send_event("edges_change", new CustomEvent("edges_change", { detail: { edges: next } }));
        return next;
      });
    },
    [] // Remove edges dependency to avoid stale closure
  );

  const onConnect = useCallback(
    (connection) => {
      // Use setEdges with a function to get the most current state
      setEdges((currentEdges) => {
        const next = addEdge(connection, currentEdges);
        model.send_event("connect", new CustomEvent("connect", { detail: { edges: next, connection } }));
        return next;
      });
    },
    [] // Remove edges dependency to avoid stale closure
  );

  return (
    <div style={{ width: "100%", height: "100%" }}>
      <ReactFlow
        nodes={displayNodes}
        edges={displayEdges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onEdgeClick={onEdgeClick}
        onConnect={onConnect}
        fitView={fitView}
        animate={true}
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  );
}
