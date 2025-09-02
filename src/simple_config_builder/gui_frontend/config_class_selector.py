import panel as pn
import param
from simple_config_builder import ConfigClassRegistry

class ConfigclassSelector(pn.custom.PyComponent):
    config_class_name: param.String = param.String(default="", doc="Name of the config class", constant =True, )
    subclasses: param.List = param.List(default=["simple_config_builder.Configclass"], doc="List of possible config classes")
    change_config_class: pn.widgets.ButtonIcon = pn.widgets.ButtonIcon(description="Change Config Class", icon="replace")
    show_config_class: pn.widgets.Toggle = param.ClassSelector(class_=pn.widgets.Toggle)

    def __init__(self, **params):
        ConfigClassRegistry.register(Test)
        ConfigClassRegistry.register(Child)
        super().__init__(**params)
        self.subclasses = ConfigClassRegistry().get_subclasses(self.config_class_name)
        self.show_config_class = pn.widgets.Toggle(name=self.config_class_name, value=False)


    def __panel__(self):
        return pn.Row(
            self.show_config_class,
            self.change_config_class,
        )




from simple_config_builder import Configclass
class Test(Configclass):
    pass
class Child(Test):
    pass


ConfigclassSelector(
    config_class_name="Test"
).servable()

