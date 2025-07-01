"""
Implementation of the Configclass and the Registry.

The Configclass are used to create a class with constraints
on the fields. The constraints are defined using the Field from pydantic.
The Configclass adds the following functionality:

- Registers the class in the ConfigClassRegistry
- Adds a _config_class_type attribute to the class
- Converts the class to a pyserde class for serialization and deserialization
A class decorated with configclass fulfills the Configclass protocol.

Example:
    ``` python
    from simple_config_builder import Configclass, Field

    class MyClass(Configclass):
        x:
            int = Field(gt=0, lt=10)
        y:
            Literal["a", "b", "c"] = Field(default="a")

    my_class: Configclass = MyClass(x=5, y="a")
    my_class.x = 10  # Raises ValueError
    my_class.y = "d"  # Raises ValueError
    ```
"""

from __future__ import annotations

import importlib.util

from pydantic import (
    BaseModel,
    PrivateAttr,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)
from pydantic import Field

from typing import (
    TYPE_CHECKING,
    Any,
    Type,
)

if TYPE_CHECKING:
    from typing import ClassVar
from pydantic import ConfigDict


class Configclass(BaseModel):
    """Configclass base class."""

    _config_class_type: str = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        # Set _config_class_type to the path and class name of the class
        self._config_class_type = (
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    def _callable_serialization(self, value: Any) -> dict[str, Any]:
        """
        Serialize a callable to a dictionary.

        Parameters
        ----------
        value: The callable to serialize.

        Returns
        -------
        A dictionary with the type, module, name and file path of the callable.
        """
        try:
            importlib.import_module(value.__module__)
            file_path = ""
        except ImportError:
            file_path = value.__code__.co_filename
        return {
            "type": "callable",
            "module": value.__module__,
            "name": value.__name__,
            "file_path": file_path,
        }

    @classmethod
    def _callable_deserialization(cls, value: dict[str, Any]) -> Any:
        """
        Deserialize a callable from a dictionary.

        Parameters
        ----------
        value: The dictionary to deserialize.

        Returns
        -------
        The callable represented by the dictionary.
        """
        module = value["module"]
        name = value["name"]
        file_path = value.get("file_path", "")
        if file_path:
            spec = importlib.util.spec_from_file_location(name, file_path)
            if spec is None:
                msg = f"Could not find spec for module {name} at {file_path}"
                raise ImportError(msg)
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                msg = f"Could not load module {name} at {file_path}"
                raise ImportError(msg)
            spec.loader.exec_module(module)
        else:
            module = importlib.import_module(module)
        return getattr(module, name)

    @model_serializer(mode="wrap")
    def _wrap_ser(self, handler: SerializerFunctionWrapHandler):
        """Serialize the Configclass instance."""
        # use standard pydantic serialization exclude callables
        # and add the _config_class_type attribute

        data: dict[str, Any] = {}

        data["_config_class_type"] = self._config_class_type

        # Serialize callables to their string representation
        for key, field_info in type(self).model_fields.items():
            value = getattr(self, key)
            if callable(value):
                data[key] = self._callable_serialization(value)
            elif isinstance(value, list):
                # If the value is a list, serialize each callable in the list
                data[key] = [
                    self._callable_serialization(item)
                    if callable(item)
                    else item
                    for item in value
                ]
            elif isinstance(value, dict):
                # If the value is a dict, serialize each callable in the dict
                data[key] = {
                    sub_key: self._callable_serialization(sub_value)
                    if callable(sub_value)
                    else sub_value
                    for sub_key, sub_value in value.items()
                }
            else:
                # Otherwise, use the standard serialization
                data[key] = value

        return data

    @model_validator(
        mode="before",
    )
    @classmethod
    def _wrap_val(cls, data: dict[str, Any], info) -> dict[str, Any]:
        for key, value in data.items():
            if (
                isinstance(value, dict)
                and "type" in value
                and value["type"] == "callable"
            ):
                data[key] = cls._callable_deserialization(value)
            # check for list of Callable
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if (
                        isinstance(item, dict)
                        and "type" in item
                        and item["type"] == "callable"
                    ):
                        data[key][i] = cls._callable_deserialization(item)
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    if (
                        isinstance(sub_value, dict)
                        and "type" in sub_value
                        and sub_value["type"] == "callable"
                    ):
                        data[key][sub_key] = cls._callable_deserialization(
                            sub_value
                        )
        return data

    def __init_subclass__(cls, **kwargs):
        """
        Initialize the subclass and register it in the ConfigClassRegistry.

        This method is called when a class is defined that
        inherits from Configclass.
        It registers the class in the ConfigClassRegistry.
        """
        ConfigClassRegistry.register(cls)
        return super().__init_subclass__(**kwargs)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        """Get the JSON schema for the Configclass."""
        # Check for Callable fields and convert them to a string representation
        for key, field_info in cls.model_fields.items():
            print(core_schema)
            if field_info.annotation == "Callable":
                # Convert Callable to a string representation
                core_schema = core_schema.copy()
                print(core_schema)
                core_schema["type"] = "string"
                core_schema["description"] = (
                    "A callable function, represented as a string."
                )
                core_schema["example"] = "module_name.function_name"

        return super().__get_pydantic_json_schema__(core_schema, handler)

    model_config = ConfigDict(
        validate_assignment=True,
    )


class ConfigClassRegistry:
    """Registry to hold all registered classes."""

    __registry: ClassVar = {}  # Class variable to hold the registry

    @classmethod
    def get_class_str_from_class(cls, class_to_register: type):
        """
        Get the class string from a class.

        The class string is the module and class name of the
        class separated by a dot.

        Example:
            ```
            class_to_register = MyClass
            get_class_str_from_class(class_to_register)
            # Returns: "mymodule.MyClass"
            ```


        Parameters
        ----------
        class_to_register: The class to get the class string from.
        """
        return f"{class_to_register.__module__}.{class_to_register.__name__}"

    @classmethod
    def register[T](cls, class_to_register: type[T]):
        """
        Register a class in the global registry.

        Parameters
        ----------
        class_to_register: The class to register.

        Raises
        ------
        ValueError: If the class is already registered.
        """
        if class_to_register not in cls.__registry:
            class_str = cls.get_class_str_from_class(class_to_register)
            cls.__registry[class_str] = class_to_register
        else:
            exception_msg = (
                f"{cls.get_class_str_from_class(class_to_register)} "
                f"is already registered."
            )
            raise ValueError(exception_msg)

    @classmethod
    def list_classes(cls) -> list[str]:
        """
        List all registered classes.

        Returns
        -------
        A list of class strings of all registered classes.
        """
        return list(cls.__registry.keys())

    @classmethod
    def is_registered(cls, class_to_register) -> bool:
        """
        Check if a class is already registered.

        Parameters
        ----------
        class_to_register: The class to check.
        """
        return (
            cls.get_class_str_from_class(class_to_register) in cls.__registry
        )

    @classmethod
    def get(cls, class_name) -> Type[Configclass]:
        """
        Get a class from the registry by name.

        Parameters
        ----------
        class_name: The name of the class to get.

        Raises
        ------
        ValueError: If the class is not registered.

        Returns
        -------
        The class if it is registered.
        """
        for class_to_register in cls.__registry:
            if class_to_register == class_name:
                return cls.__registry[class_to_register]
        raise ValueError(f"{class_name} is not registered.")

    @classmethod
    def get_class_attributes(cls, class_name: str) -> dict[str, Any]:
        """
        Get the attributes of a class by name.

        Parameters
        ----------
        class_name: The name of the class to get attributes from.

        Returns
        -------
        A dictionary of attributes of the class.
        """
        config_class = cls.get(class_name)
        if config_class is None:
            raise ValueError(f"{class_name} is not registered.")
        fields = {
            key: value.annotation
            for key, value in config_class.model_fields.items()
        }
        return fields


__all__ = [
    "Configclass",
    "ConfigClassRegistry",
    "Field",
]
