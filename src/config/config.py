"""Test implementation of a config class decorator and a registry."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import ClassVar

from serde import serde


class ConfigClassRegistry:
    """Registry to hold all registered classes."""
    
    __registry: ClassVar = []  # Class variable to hold the registry

    @classmethod
    def register(cls, class_to_register):
        """Register a class in the global registry."""
        if class_to_register not in cls.__registry:
            cls.__registry.append(class_to_register)
        else:
            exception_msg = f"{class_to_register} is already registered."
            raise ValueError(exception_msg)

    @classmethod
    def list_classes(cls):
        """List all registered classes."""
        return cls.__registry

    @classmethod
    def is_registered(cls, class_to_register):
        """Check if a class is already registered."""
        return class_to_register in cls.__registry


def configclass(class_to_register=None,*_args, **_kwargs):
    """Decorate a class to register it in the global registry."""
    def decorator(class_to_register):
        registry = ConfigClassRegistry()
        registry.register(class_to_register)

        # Add pyserde decorator
        class_to_register = serde(class_to_register)

        def create_property(name, gt=None, lt=None, 
                            _in=None, constraints=None):
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
                if constraints is not None:
                    for constraint in constraints:
                        if not constraint(value):
                            exception_message = (
                                f"{name} does not satisfy the "
                                f"constraint {constraint}"
                            )
                            raise ValueError(exception_message)
                setattr(self, f"_{name}", value)

            return property(getter, setter)

        for f in dataclasses.fields(class_to_register):
            if "gt" in f.metadata or "lt" in f.metadata:
                setattr(
                    class_to_register

    ,
                    f.name,
                    create_property(
                        f.name,
                        f.metadata.get("gt"),
                        f.metadata.get("lt"),
                        f.metadata.get("_in"),
                        f.metadata.get("constraints"),
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
    _in: list | None = None,
    constraints: list[Callable[..., bool]] | None = None,
):
    """Create a field with constraints."""
    return dataclasses.field(
        default=default,
        metadata={"gt": gt, "lt": lt, "_in": _in, "constraints": constraints},
    )
