"""Test implementation of a config class decorator and a registry."""

from __future__ import annotations

import dataclasses
import importlib.util
import os
from plum import dispatch
from typing import TYPE_CHECKING, Type
from collections.abc import Callable

if TYPE_CHECKING:
    from typing import ClassVar
from serde import serde, field as serde_field

class __CallableSerializer:
    @dispatch
    def serialize(self, obj: Callable) -> dict[str, str]:
        # check if the function is in the python path
        try:
            _ = __import__(obj.__module__)
        except Exception:
            # get the file path of the function
            file_path = os.path.abspath(obj.__code__.co_filename)
            return {
                "module": obj.__module__,
                "function": obj.__name__,
                "file_path": file_path
            }
        return {
            "module": obj.__module__,
            "function": obj.__name__,
            "file_path": ""
        }


class __CallableDeserializer:
    @dispatch
    def deserialize(
            self,
            cls: Type[Callable],
            obj: dict[str, str]) -> Callable:
        # get the module and function name
        module_name = obj["module"]
        function_name = obj["function"]
        file_path = obj["file_path"] if "file_path" in obj else ""
        # check if the function is in the python path
        if file_path == "":
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                raise ImportError(f"Module {module_name} not found")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, function_name)
        else:
            spec = (importlib.util.spec_from_file_location
                    (module_name, file_path))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if not hasattr(module, function_name):
                raise AttributeError(
                    f"Function {function_name} not "
                    f"found in module {module_name}")

            # get the function
            return getattr(module, function_name)

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
    def register(cls, class_to_register: type):
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


def configclass(class_to_register: type = None, *_args, **_kwargs):
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

    def decorator(class_to_register):
        registry = ConfigClassRegistry()
        registry.register(class_to_register)

        # Add a _config_class_type attribute to the class for serialization
        # Also add the annotation to the class
        setattr(
            class_to_register,
            "_config_class_type",
            ConfigClassRegistry.get_class_str_from_class(class_to_register),
        )
        class_to_register.__annotations__["_config_class_type"] = str

        # Add pyserde decorator
        class_to_register = serde(
            class_to_register,
        class_serializer=__CallableSerializer(),
        class_deserializer=__CallableDeserializer()
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

        for f in dataclasses.fields(class_to_register):
            if (
                "gt" in f.metadata
                or "lt" in f.metadata
                or "_in" in f.metadata
                or "validators" in f.metadata
            ):
                setattr(
                    class_to_register,
                    f.name,
                    create_property(
                        f.name,
                        f.metadata.get("gt"),
                        f.metadata.get("lt"),
                        f.metadata.get("_in"),
                        f.metadata.get("validators"),
                    ),
                )

        # manipulate docstring so that metadata is included

        return class_to_register

    if class_to_register is not None:
        return decorator(class_to_register)
    return decorator


def config_field(
    *,
    gt=None,
    lt=None,
    default=None,
    default_factory=None,
    _in: list | None = None,
    validators: list[Callable[..., bool]] | None = None,
    serializer: Callable[..., any] | None = None,
    deserializer: Callable[..., any] | None = None,
    alias: str | None = None,
) -> dataclasses.Field:
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
