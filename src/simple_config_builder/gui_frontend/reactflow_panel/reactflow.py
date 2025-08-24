"""React Flow python interface."""
import uuid

import panel as pn
import param
from panel.custom import ReactComponent, Children
from panel.viewable import Viewable

pn.extension()


class ReactFlowNode(param.Parameterized):
    """React Flow Node."""

    node_id = param.String(doc="Unique identifier for the node")
    position = param.Dict(
        default={"x": 0, "y": 0},
        doc="Position on the canvas"
    )

    width = param.Integer(default=None, bounds=(50, 1000))
    height = param.Integer(default=None, bounds=(30, 1000))
    background_color = param.String(default="#ffffff")
    border_color = param.String(default="#ddd")
    border_width = param.Integer(default=1, bounds=(0, 10))
    border_radius = param.Integer(default=8, bounds=(0, 50))
    padding = param.Integer(default=10, bounds=(0, 50))

    has_input_handle = param.Boolean(default=True)
    has_output_handle = param.Boolean(default=True)
    input_handle_position = param.Selector(
        default="Top", objects=["Top", "Bottom", "Left", "Right"])
    output_handle_position = param.Selector(
        default="Bottom", objects=["Top", "Bottom", "Left", "Right"])
    is_hidden = param.Boolean(default=False)

    component = param.Parameter(
        allow_refs=True,
        doc="Any Panel component which is shown in the node."
    )

    def __init__(self, component=None, **params):
        if 'node_id' not in params:
            params['node_id'] = f"node_{uuid.uuid4().hex[:8]}"
        if component is not None:
            params['component'] = component
        super().__init__(**params)
        

    def get_node_data(self):
        """Get the JSON-friendly data for a node."""
        return {
            "node_id": self.node_id,
            "width": self.width,
            "height": self.height,
            "background_color": self.background_color,
            "border_color": self.border_color,
            "border_width": self.border_width,
            "border_radius": self.border_radius,
            "padding": self.padding,
            "has_input_handle": self.has_input_handle,
            "has_output_handle": self.has_output_handle,
            "input_handle_position": self.input_handle_position,
            "output_handle_position": self.output_handle_position,
        }

    def get_react_flow_node(self):
        """Get node in React Flow (pure JSON) format."""
        return {
            "id": self.node_id,
            "type": "panelNode",
            "position": self.position,
            "is_hidden": self.is_hidden,
            "data": self.get_node_data(),  # JSON only!
        }


class ReactFlowPane(ReactComponent):
    """React Flow Pane."""

    fit_view = param.Boolean(default=True)
    use_dagre = param.Boolean(default=False, doc="Dagre-Layout")
    dagre_direction = param.Selector(default="LR", objects=["TB", "LR"])
    dagre_nodesep = param.Integer(default=100, bounds=(0, 500))
    dagre_ranksep = param.Integer(default=200, bounds=(0, 800))

    # Panel children only (actual widgets/panes/layouts)
    objects: Children = Children(default=[])

    # Parallel list of node ids (kept in sync with `objects`). 
    node_keys = param.List(
        default=[],
        doc="List[str] of node ids parallel to `objects`"
    )

    # React Flow JSON state
    nodes = param.List(
        default=[],
        doc="List[dict] of React Flow nodes (JSON only)"
    )
    edges = param.List(
        default=[],
        doc="List[dict] of React Flow edges (JSON only)"
    )

    _importmap = {
        "imports": {
            "react": "https://esm.sh/react@18",
            "react-dom": "https://esm.sh/react-dom@18",
            "@xyflow/react": "https://esm.sh/@xyflow/react@12.8.3?external=react,react-dom",
            "dagre": "https://esm.sh/dagre@0.8.5"
        }
    }

    _stylesheets = ["https://esm.sh/@xyflow/react@12.8.3/dist/style.css"]

    _esm = "./reactflow_component.js"

    def _set_nodes(self, nodes):
        self.nodes = list(nodes)

    def _set_edges(self, edges):
        self.edges = list(edges)

    def _add_child(self, key: str, child):
        """Append a child + its key. Always reassign lists."""
        child_viewable = pn.panel(child)  # ensure a proper Viewable instance
        self.objects = list(self.objects) + [child_viewable]
        self.node_keys = list(self.node_keys) + [key]
        return len(self.objects) - 1  # index

    def _remove_child(self, key: str):
        """Remove a child + its key by key. Return the removed Panel object."""
        if key not in self.node_keys:
            raise ValueError(f"Key '{key}' not in node_keys")

        idx = self.node_keys.index(key)
        new_objects = list(self.objects)
        new_keys = list(self.node_keys)

        removed = new_objects.pop(idx)
        new_keys.pop(idx)

        self.objects = new_objects
        self.node_keys = new_keys
        return idx, removed 

    def add_node(self, node: ReactFlowNode):
        """Add a node."""
        if not isinstance(node, ReactFlowNode):
            raise ValueError("Node must be a ReactFlowNode instance")

        _ = self._add_child(node.node_id, node.component)

        react_node = node.get_react_flow_node()

        self._set_nodes(list(self.nodes) + [react_node])
        self._setup_node_events(node)
        return node

    def _setup_node_events(self, panel_node: ReactFlowNode):
        def update_react_node(*events):
            fresh = panel_node.get_react_flow_node()
            updated = []
            for n in self.nodes:
                if n["id"] == panel_node.node_id:
                    updated.append(fresh)
                else:
                    updated.append(n)
            self._set_nodes(updated)

        watchable = [
            'position',
            'width',
            'height',
            'background_color',
            'border_color',
            'border_width',
            'border_radius',
            'padding',
            'has_input_handle',
            'has_output_handle',
            'input_handle_position',
            'output_handle_position'
        ]
        existing = [p for p in watchable if hasattr(panel_node.param, p)]
        if existing:
            panel_node.param.watch(update_react_node, existing)

    def get_node(self, node_id: str) -> Viewable:
        """Return the node by node id."""
        if node_id not in self.node_keys:
            raise ValueError(f"Node ID '{node_id}' not found")
        idx = self.node_keys.index(node_id)
        return self.objects[idx]

    def remove_node(self, node_id: str):
        """Remove a node and any associated edges from the pane."""
        # Remove the Panel component and key from internal lists
        removed_index, removed_component = self._remove_child(node_id)
        
        # Remove node from self.nodes (JSON)
        new_nodes = [n for n in self.nodes if n.get("id") != node_id]
        self._set_nodes(new_nodes)
        
        # Remove edges connected to the node
        new_edges = [
            e for e in self.edges
            if e.get("source") != node_id and e.get("target") != node_id
        ]
        self._set_edges(new_edges)

    def clear_nodes(self):
        """Clear all nodes."""
        self.objects = []     # children (Panel objects)
        self.node_keys = []   # ids parallel to children
        self._set_nodes([])   # JSON

    def clear_edges(self):
        """Clear all edges."""
        self._set_edges([])

    def get_node_ids(self):
        """Get list of all current node IDs."""
        return list(self.node_keys)

    def hide_node_with_subtree(self, node_id: str):
        """Hide the subtree of a node."""
        # Find all nodes in the subtree
        to_hide = set()

        def collect_subtree(nid):
            if nid in to_hide:
                return
            to_hide.add(nid)
            for edge in self.edges:
                if edge.get("source") == nid:
                    collect_subtree(edge.get("target"))

        collect_subtree(node_id)

        # Update nodes to be hidden
        updated_nodes = []
        for n in self.nodes:
            if n["id"] in to_hide:
                n = dict(n)
                n["hidden"] = True
                updated_nodes.append(n)
            else:
                updated_nodes.append(n)
        self._set_nodes(updated_nodes)


# ---- Demo usage --------------------------------------------------------------

rf = ReactFlowPane(sizing_mode="stretch_both", height=500)

# 1) TextInput
text_input = pn.widgets.TextInput(value="Hello World", placeholder="Enter text...")
rf.add_node(ReactFlowNode(
    component=text_input,
    node_id="text1",
    position={"x": 50, "y": 50},
    width=250,
    background_color="#f8f9fa",
    border_color="#007bff"
))

# 2) Button
button = pn.widgets.Button(name="Click Me!", button_type="primary")
rf.add_node(ReactFlowNode(
    component=button,
    node_id="button1",
    position={"x": 350, "y": 50},
    width=200,
    background_color="#fff3cd",
    border_color="#ffc107"
))

# 3) Slider
slider = pn.widgets.FloatSlider(name="Value", start=0, end=100, value=50, step=1)
rf.add_node(ReactFlowNode(
    component=slider,
    node_id="slider1",
    position={"x": 50, "y": 200},
    width=300,
    background_color="#d4edda",
    border_color="#28a745"
))

# 4) HTML pane
html_pane = pn.pane.HTML("""
<div style="text-align: center;">
    <h3 style="color: #dc3545;">Custom HTML</h3>
    <p>This is any HTML content!</p>
    <ul>
        <li>Item 1</li><li>Item 2</li>
    </ul>
</div>
""")
rf.add_node(ReactFlowNode(
    component=html_pane,
    node_id="html1",
    position={"x": 400, "y": 200},
    width=200,
    background_color="#f8d7da",
    border_color="#dc3545"
))

# 5) Markdown
markdown = pn.pane.Markdown("""
## Markdown Node
- **Bold text**
- *Italic text*
- `Code snippet`

> This is a blockquote
""")
rf.add_node(
    ReactFlowNode(
        component=markdown,
        node_id="markdown1",
        position={"x": 200, "y": 350},
        width=250,
        background_color="#e2f3ff",
        border_color="#0dcaf0"
    )
)

# 6) Layout
layout = pn.Column(
    pn.pane.HTML("<h4>Mini Dashboard</h4>"),
    pn.widgets.Select(name="Choose", options=["A", "B", "C"], value="A"),
    pn.widgets.IntSlider(name="Number", start=1, end=10, value=5),
    pn.pane.HTML("<small>This is a layout node!</small>"),
    sizing_mode="stretch_width"
)
rf.add_node(
    ReactFlowNode(
        component=layout,
        node_id="layout1",
        position={"x": 600, "y": 50},
        width=220,
        height=200,
        background_color="#fff",
        border_color="#6c757d",
        border_width=2
    )
)

# Edges (pure JSON)
rf._set_edges([
    {"id": "e1", "source": "text1", "target": "slider1", "label": "text1 -> slider1"},
    {"id": "e2", "source": "button1", "target": "html1"},
    {"id": "e3", "source": "slider1", "target": "markdown1"},
    {"id": "e4", "source": "html1", "target": "layout1"},
    {"id": "e5", "source": "markdown1", "target": "layout1"}
])

# JS -> Python events (read CustomEvent.detail)
def on_nodes_change(event):
    """Handle nodes change events from the React frontend."""
    pass

def on_edges_change(event):
    """Handle edges change events from the React frontend."""
    pass

def on_connect(event):
    """Handle connection events from the React frontend."""
    pass

def on_edge_click(event):
    """Handle edge click events from the React frontend."""
    edge = event.data['detail']['edge']
    print(f"Edge clicked: {edge['id']}, Source: {edge['source']}, Target: {edge['target']}")
    rf.hide_node_with_subtree(edge['target'])

rf.on_event("nodes_change", on_nodes_change)
rf.on_event("edges_change", on_edges_change)
rf.on_event("connect", on_connect)
rf.on_event("edge_click", on_edge_click)

# Add delete button functionality
def create_delete_button_controls():
    """Create controls for deleting nodes."""
    # Create dropdown to select which node to delete
    node_selector = pn.widgets.Select(
        name="Select Node to Delete",
        value=rf.get_node_ids()[0] if rf.get_node_ids() else None,
        options=rf.get_node_ids(),
        width=200
    )
    
    # Create delete button
    delete_button = pn.widgets.Button(
        name="Delete Node",
        button_type="primary",
        width=100
    )
    
    def update_node_options():
        """Update the dropdown options when nodes change."""
        current_ids = rf.get_node_ids()
        node_selector.options = current_ids
        if current_ids and node_selector.value not in current_ids:
            node_selector.value = current_ids[0] if current_ids else None
        elif not current_ids:
            node_selector.value = None
    
    def on_delete_click(event):
        """Handle delete button click."""
        if node_selector.value:
            try:
                node_id = node_selector.value
                rf.remove_node(node_id)
                update_node_options()
            except Exception as e:
                print(f"❌ Error deleting node: {e}")
        else:
            print("⚠️ No node selected for deletion")
    
    # Connect the button click event
    delete_button.on_click(on_delete_click)
    
    # Create the control panel
    controls = pn.Row(
        node_selector,
        delete_button,
        margin=(10, 0)
    )
    
    return controls, update_node_options

# Create delete controls
delete_controls, update_options = create_delete_button_controls()

# Create the main layout with delete controls at the top
main_layout = pn.Column(
    pn.pane.HTML("<h3>React Flow Demo with Delete Functionality</h3>"),
    delete_controls,
    rf,
    sizing_mode="stretch_both"
)

main_layout.servable()
