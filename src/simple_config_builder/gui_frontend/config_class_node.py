from __future__ import annotations
from typing import Type, Union, get_args, get_origin
import click
import param
import panel as pn

from simple_config_builder.config import _ConfigField, ConfigClassRegistry, Configclass
from simple_config_builder.gui_frontend.reactflow_panel.reactflow import ReactFlowNode

ConfigclassDict = dict[str, Configclass]
ConfigclassList = list[str, Configclass]

def _is_simple_list_type(typ):
    origin = get_origin(typ)
    if typ is list:
        return True
    if origin is list:
        if get_args(typ) in [str, int, float, bool, list, dict, None]:
            return True
    return False

def _is_simple_dict_type(typ):
    origin = get_origin(typ)
    if typ is dict:
        return True
    if origin is dict:
        if get_args(typ) in [str, int, float, bool, list, dict, None]:
            return True
    return False

class ConfigClassNode(ReactFlowNode):
    """Node representation for a Configclass in the React Flow diagram."""

    config_class: str = param.ClassSelector(class_=str, allow_None=False)
    children_toggle_state: dict[str, bool] = param.Dict(default={})
    on_children_toggle_changed: param.Callable = param.Action(lambda event, field_name: click.echo(f"Toggle state changed for {field_name}: {event.new}"))
    fields: dict[str, _ConfigField]
    values: dict[str, str|int|float|bool|list|dict|None] = param.Dict(
        default={}
    )

    def __init__(self,**params):
        super().__init__(**params)

    @pn.depends("config_class", on_init=True, watch=True)
    def _on_config_class_change(self):
        self.fields = ConfigClassRegistry().get_class_attributes(self.config_class)
        self._build_panel_layout()

    @pn.depends("values", on_init=False, watch=True)
    def _on_values_change(self):
        self._build_panel_layout()

    def _build_panel_layout(self):
        click.echo("Building panel layout")
        reset_button = pn.widgets.Button(name="Reset", button_type="warning")
        def _reset_to_defaults(_):
            self.values = {field.name: field.default for field in self.fields.values()}
            self.param.trigger("values")
        reset_button.param.watch(_reset_to_defaults, "clicks")
        self.component = pn.Column(
            pn.Row(
                pn.pane.Markdown(f"### {self.config_class}"),
                pn.layout.Spacer(sizing_mode="stretch_width"),
                reset_button,
            ),
            *[self.field_to_panel_component(field) for field in self.fields.values()]
        )


    def field_to_panel_component(self,field: _ConfigField, value: str|int|float|bool|list|dict|Configclass|None=None) -> pn.viewable.Viewable:
        """Convert a config field to a Panel widget."""
        print(field.typ)
        value = value if value is not None else field.default
        pn_value = pn.widgets.StaticText(value="This type is not recognized")
        match field.typ:
            case typ if typ is str:
                pn_value = pn.widgets.TextInput(value=value or "")
                # bind pn_value update to save to self.values
                pn_value.param.watch(lambda event: self.values.update({field.name: event.new}), "value")
            case typ if typ is int:
                pn_value = pn.widgets.IntInput(value=value or 0)
                pn_value.param.watch(lambda event: self.values.update({field.name: event.new}), "value")
            case typ if typ is float:
                pn_value = pn.widgets.FloatInput(value=value or 0.0)
                pn_value.param.watch(lambda event: self.values.update({field.name: event.new}), "value")
            case typ if typ is bool:
                pn_value = pn.widgets.Toggle(name="✓" if value else "✗", value=value or False, button_type='success', width=20)
                def _toggle(event):
                    pn_value.button_type = 'danger' if event.new is False else 'success'
                    pn_value.name = "✓" if event.new else "✗"
                    self.values.update({field.name: event.new})
                pn_value.param.watch(_toggle, "value")
            case typ if _is_simple_list_type(typ) or _is_simple_dict_type(typ):
                pn_value = pn.widgets.JSONEditor(value=value or [])
                pn_value.param.watch(lambda event: self.values.update({field.name: event.new}), "value")
            case typ if typ is dict:
                pn_value = pn.widgets.JSONEditor(value=value or {})
                pn_value.param.watch(lambda event: self.values.update({field.name: event.new}), "value")
            case typ if issubclass(typ, Configclass): # type:ignore
                if self.children_toggle_state.get(field.name, False):
                    pn_value = pn.widgets.Toggle(
                        name="Hide", value=True, button_type="success"
                    )
                else:
                    pn_value = pn.widgets.Toggle(
                        name="Show", value=False, button_type="danger"
                    )

                def _toggle(event):
                    self.children_toggle_state[field.name] = event.new
                    pn_value.button_type = "success" if event.new else "danger"
                    pn_value.name = "Hide" if event.new else "Show"
                pn_value.param.watch(
                    _toggle, "value"
                )
            case typ if typ is dict[str, Configclass]:
                pn_value = self._build_dict_of_configclass(field.name)
            case typ if typ is list[Configclass]:
                pn_value = self._build_list_of_configclass(field.name)
            case _:
                pass
        return pn.Row(
            pn.pane.Markdown(f"**{field.name}**"),
            pn_value,
            pn.pane.Markdown(f"*Default:* `{field.default}`"),
        )
    
    def _build_dict_of_configlass(self,field_name):
        pass
    def _build_list_of_configclass(self, field_name)
    
