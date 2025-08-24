from typing import Union, cast
import uuid
from panel import depends
from panel.custom import PyComponent
from panel.viewable import Viewable, Layoutable
from panel.models.reactive_html import DOMEvent
import param

from simple_config_builder.gui_frontend.reactflow_panel.reactflow import ReactFlowPane

class LabeledEdge(param.Parameterized):
    source = param.String()
    target = param.String()
    label = param.String()
    edge_id = param.String(default=None)

    def __init__(self, **params):
        super().__init__(**params)
        if not self.edge_id:
            self.edge_id = f"edge_{uuid.uuid4().hex[:8]}"

    def get_edge_data(self):
        return {
            "source": self.source,
            "target": self.target,
            "id": self.edge_id,
            "label": self.label
        }


class FoldableTreeNode(param.Parameterized):
    title = param.String(default="Foldable Node")
    content = param.ClassSelector(class_=Union[Layoutable, Viewable])
    children_nodes = param.List(item_type=str, default=[])
    is_folded = param.Boolean(default=False)
    input_edge = param.ClassSelector(
        class_=LabeledEdge, 
        default=None, 
        allow_None=True
    )
    node_id = param.String(default=None)

    def __init__(self, **params):
        super().__init__(**params)
        if not self.node_id:
            self.node_id = f"node_{uuid.uuid4().hex[:8]}"

class ReactFlowTree(PyComponent):
    nodes = param.Dict() # Mapping of node_id to ReactFlowNode
    tree_root = param.String(default="root")
    use_dagre = param.Boolean(default=True, doc="Enable tree/Dagre layout")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.react_flow_pane = ReactFlowPane(
            use_dagre=self.use_dagre,
            dagre_direction="LR",
            dagre_nodesep=100,
            dagre_ranksep=200,
            sizing_mode="stretch_both"
        )
        self.react_flow_pane.on_event("edge_click", self._on_edge_click)
        self._update_tree()
    
    def _on_edge_click(self, event):
        edge = cast(DOMEvent, event).data['detail']['edge']
        target_node = edge['target']
        print(f"Edge clicked: {edge['id']}, Target node: {target_node}")
        node = self.nodes.get(target_node)
        self.react_flow_pane.hide_node_with_subtree(target_node)

    def _fold_subtree(self, node):
        node.is_folded = True
        for child_id in node.children_nodes:
            child_node = self.nodes.get(child_id)
            if child_node:
                self._fold_subtree(child_node)


    def _update_tree(self):
        # Update the tree structure based on the current nodes and root
        self.react_flow_pane.clear_nodes()
        self.react_flow_pane.clear_edges()
        self._build_tree(self.tree_root, None)
        
    
    def _build_tree(self, node_id: str, parent_id):
        node = self.nodes.get(node_id)
        if not node:
            return
        # If folded: do not add the node or any edges/children
        if node.is_folded:
            return

        # Add the node itself
        self.react_flow_pane.add_panel_node(
            component=node.content,
            node_id=node.node_id,
            position={"x": 0, "y": 0},
            input_handle_position="Left",
            output_handle_position="Right",
        )

        # Add edge from parent → node (if parent exists)
        if parent_id:
            print(node_id, parent_id)
            edge = LabeledEdge(source=parent_id, target=node_id, label=node.title)
            self.react_flow_pane.edges.append(edge.get_edge_data())

        # Recurse into children
        for child_id in node.children_nodes:
            self._build_tree(child_id, node_id)
        print(self.react_flow_pane.edges, self.react_flow_pane.nodes, self.react_flow_pane.objects)


    def __panel__(self):
        return self.react_flow_pane


# Example usage
import panel as pn
node2 = FoldableTreeNode(content=pn.widgets.Checkbox(), is_folded=False)
node3 = FoldableTreeNode(content=pn.widgets.Button(), is_folded=False)
node1 = FoldableTreeNode(
    content=pn.widgets.TextInput(), node_id="root", children_nodes=[node2.node_id, node3.node_id],
    is_folded=False
)

tree = ReactFlowTree(
    use_dagre=False,
    nodes={
        node1.node_id: node1,
        node2.node_id: node2,
        node3.node_id: node3
}, tree_root="root")
tree.servable()