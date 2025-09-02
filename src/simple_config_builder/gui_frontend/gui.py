"""Panel GUI for Simple Config Builder."""

from typing import Union
import panel as pn
import param

from simple_config_builder import Configclass, Configparser, ConfigClassRegistry
from simple_config_builder.gui_frontend.config_class_node import ConfigClassNode
from simple_config_builder.gui_frontend.reactflow_panel.reactflow import ReactFlowPane, ReactFlowNode


def make_simple_config_builder_gui(file_path):
    """Create a SimpleConfigBuilderGUI instance."""
    return SimpleConfigBuilderGUI(file_path=file_path)

class SimpleConfigBuilderGUI(pn.custom.PyComponent):
    """A simple GUI for building configurations using Panel."""

    config_data = param.ClassSelector(class_=Union[Configclass, dict, list])
    file_path = param.Path(check_exists=False)
    graph = param.ClassSelector(class_=ReactFlowPane, default=None, allow_None=True)
    layout = param.ClassSelector(class_=pn.Column, default=pn.Column(
        sizing_mode="stretch_both",

    ))

    def __init__(self, **params):
        super().__init__(**params)
        self.config_parser = Configparser(
            config_file=self.file_path, autosave=True)
        self.config_data = self.config_parser.config_data
    
    @pn.depends("config_data", watch=True, on_init=False)
    def on_config_data_change(self):
        """Is triggered when the config_data changes."""
        # put to configparser
        self.config_parser.config_data = self.config_data

        # update GUI
        if isinstance(self.config_data, Configclass):
            pass
            # self.update_graph()
        else:
            self.layout.clear()
            menu_btn = pn.widgets.MenuButton(
                items=ConfigClassRegistry().list_classes(),
                sizing_mode="stretch_width"
            )
            def _on_menu_button_click(event):
                """Is triggered when the menu button is clicked."""
                selected_class = event.new
                if selected_class:
                    self.layout.clear()
                    self.layout.append(
                        ConfigClassNode(config_class=selected_class).component
                    )
                    self.param.trigger("layout")
            menu_btn.param.watch(_on_menu_button_click, "clicked")
            self.layout.extend([
                pn.pane.Markdown(
                    "# The configuration is empty."
                ),
                pn.pane.Markdown(
                    "# Select a configclass to start editing config:"
                ),
                menu_btn,
                ConfigClassNode(config_class='test_config_io._TestClassConfigWithConfigClass').component

            ])


    def __panel__(self):
        """Overwrite of panel __panel__ method."""
        return self.layout