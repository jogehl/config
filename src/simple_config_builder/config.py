"""
Implementation of the configclass functions.

The configclass functions are used to create a class with constraints
on the fields. The constraints are defined using the config_field
decorator. The configclass decorator adds the following functionality:

- Registers the class in the ConfigClassRegistry
- Adds a _config_class_type attribute to the class
- Converts the class to a pyserde class for serialization and deserialization
A class decorated with configclass fulfills the Configclass protocol.

Example:
    ``` python
    from config import configclass, config_field

    @configclass
    class MyClass:
        x:
            int = config_field(gt=0, lt=10)
        y:
            str = config_field(_in=["a", "b", "c"])

    my_class: Configclass = MyClass(x=5, y="a")
    my_class.x = 10  # Raises ValueError
    my_class.y = "d"  # Raises ValueError
    ```
"""

from __future__ import annotations

import dataclasses
import importlib.util
import os

from plum import dispatch
from serde.core import ClassSerializer, ClassDeserializer

from typing import (
    TYPE_CHECKING,
    Type,
    Protocol,
    runtime_checkable,
    dataclass_transform,
    Any,
    cast,
    Union,
)
from collections.abc import Callable

if TYPE_CHECKING:
    from typing import ClassVar
from serde import serde, field as serde_field


@runtime_checkable
class Configclass(Protocol):
    """Configclass for type hinting."""

    _config_class_type: str


class __CallableSerializer(ClassSerializer):
    @dispatch
    def serialize(self, value: Callable) -> dict[str, str]:
        # check if the function is in the python path
        try:
            _ = __import__(value.__module__)
        except Exception:
            # get the file path of the function
            file_path = os.path.abspath(value.__code__.co_filename)
            return {
                "module": value.__module__,
                "function": value.__name__,
                "file_path": file_path,
            }
        return {
            "module": value.__module__,
            "function": value.__name__,
            "file_path": "",
        }


class __CallableDeserializer(ClassDeserializer):
    @dispatch
    def deserialize(
        self, cls: Type[Callable], value: dict[str, str]
    ) -> Callable:
        # get the module and function name
        module_name = value["module"]
        function_name = value["function"]
        file_path = value["file_path"] if "file_path" in value else ""
        # check if the function is in the python path
        if file_path == "":
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                raise ImportError(f"Module {module_name} not found")
            if spec.loader is None:
                raise ImportError(f"Loader for module {module_name} not found")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, function_name)
        else:
            spec = importlib.util.spec_from_file_location(
                module_name, file_path
            )
            if spec is None:
                raise ImportError(f"Module {module_name} not found")
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                raise ImportError(f"Loader for module {module_name} not found")
            spec.loader.exec_module(module)

            if not hasattr(module, function_name):
                raise AttributeError(
                    f"Function {function_name} not "
                    f"found in module {module_name}"
                )

            # get the function
            return getattr(module, function_name)


def config_field(
    *,
    gt=None,
    lt=None,
    default=None,
    default_factory=None,
    _in: list | None = None,
    validators: list[Callable[..., bool]] | None = None,
    serializer: Callable[..., Any] | None = None,
    deserializer: Callable[..., Any] | None = None,
    alias: list[str] | None = None,
) -> Any:
    """
    Create a field with constraints.

    Parameters
    ----------
    gt: The minimum value of the field.
    lt: The maximum value of the field.
    default: The default value of the field.
    default_factory: The default factory of the field.
    _in: A list of valid values for the field.
    validators: A list of validator functions for the field.
    serializer: A serializer function for the field.
    deserializer: A deserializer function for the field.
    alias: An alias for the field.

    Returns
    -------
    A dataclasses.Field object with the constraints.
    """
    return serde_field(
        default=default if default is not None else dataclasses.MISSING,
        default_factory=default_factory
        if default_factory is not None
        else dataclasses.MISSING,
        serializer=serializer,
        deserializer=deserializer,
        alias=alias,
        metadata={"gt": gt, "lt": lt, "_in": _in, "validators": validators},
    )


@dataclass_transform(field_specifiers=(config_field,))
def configclass[T](
    class_to_register: type[T] | None = None, *args, **kwargs
) -> Callable[[type[T]], Configclass | type[T]] | Configclass | type[T]:
    """
    Make a Configclass from a standard class with attributes.

    This decorator adds the following functionality:

    - Registers the class with Config
    - Adds a _config_class_type attribute to the class
    - Convert a to a pyserde class for serialization and deserialization
    - Adds property methods for fields with constraints which
    are defined using the config_field decorator.

    Parameters
    ----------
    class_to_register: The class to register with Config.
    """

    def decorator[C](_cls: type[C]) -> Configclass | type[C]:
        registry = ConfigClassRegistry()
        registry.register(_cls)

        # Add a _config_class_type attribute to the class for serialization
        # Also add the annotation to the class
        setattr(
            _cls,
            "_config_class_type",
            ConfigClassRegistry.get_class_str_from_class(_cls),
        )
        _cls.__annotations__["_config_class_type"] = str

        # Add pyserde decorator
        _cls = serde(
            _cls,
            class_serializer=__CallableSerializer(),
            class_deserializer=__CallableDeserializer(),
        )

        def create_property(name, gt=None, lt=None, _in=None, validators=None):
            def getter(self):
                return getattr(self, f"_{name}")

            def setter(self, value):
                if gt is not None and value < gt:
                    exception_message = f"{name} must be greater than {gt}"
                    raise ValueError(exception_message)
                if lt is not None and value > lt:
                    exception_message = f"{name} must be less than {lt}"
                    raise ValueError(exception_message)
                if _in is not None and value not in _in:
                    exception_message = f"{name} must be in {_in}"
                    raise ValueError(exception_message)
                if validators is not None:
                    for constraint in validators:
                        if not constraint(value):
                            exception_message = (
                                f"{name} does not satisfy the "
                                f"validator {constraint}"
                            )
                            raise ValueError(exception_message)
                setattr(self, f"_{name}", value)

            return property(getter, setter)

        for f in dataclasses.fields(_cls):  # type: ignore
            if (
                "gt" in f.metadata
                or "lt" in f.metadata
                or "_in" in f.metadata
                or "validators" in f.metadata
            ):
                setattr(
                    _cls,
                    f.name,
                    create_property(
                        f.name,
                        f.metadata.get("gt"),
                        f.metadata.get("lt"),
                        f.metadata.get("_in"),
                        f.metadata.get("validators"),
                    ),
                )

        return cast(Union[Configclass, type[C]], _cls)

    if class_to_register is not None:
        return decorator(class_to_register)
    return decorator


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
    def get(cls, class_name) -> type:
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
