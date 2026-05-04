"""
Configclass — declarative, Rust-validated configuration classes.

Subclass :class:`Configclass` and declare fields as annotated class attributes.
Defaults and validation constraints are expressed via :func:`Field`.

Example — defining a nested config
-----------------------------------
>>> from simple_config_builder.config import Configclass, Field

>>> class DatabaseConfig(Configclass):
...     host: str = "localhost"
...     port: int = Field(gt=0, lt=65536, default=5432)

>>> class AppConfig(Configclass):
...     name: str = "my-app"
...     environment: str = "dev"
...     database: DatabaseConfig = Field(default_factory=DatabaseConfig)
...     debug: bool = False

>>> cfg = AppConfig()
>>> cfg.name
'my-app'
>>> cfg.database.port
5432

Field access, mutation and validation:

>>> cfg.name = "production"
>>> cfg.database.port = 3306
>>> cfg.database.port
3306

>>> cfg.database.port = 0  # violates gt=0
Traceback (most recent call last):
    ...
ValueError: ...

Serialization:

>>> d = cfg.model_dump()
>>> d["name"]
'production'
>>> d["database"]["port"]
3306

JSON round-trip:

>>> import json
>>> restored = AppConfig.model_validate_json(cfg.model_dump_json())
>>> restored.name
'production'
"""

from __future__ import annotations

from typing import Any, Type

from simple_config_builder._native import (
    Configclass as _NativeConfigclass,
)
from simple_config_builder._native import Field
from simple_config_builder._native import (
    configure_config_class as _configure_config_class,
)
from simple_config_builder._native import (
    init_config_instance as _init_config_instance,
)
from simple_config_builder._native import model_dump as _model_dump
from simple_config_builder._native import model_dump_json as _model_dump_json
from simple_config_builder._native import (
    model_json_schema as _model_json_schema,
)
from simple_config_builder._native import (
    model_validate_json as _model_validate_json,
)
from simple_config_builder._native import (
    registry_get as _registry_get,
)
from simple_config_builder._native import (
    registry_get_class_attributes as _registry_get_class_attributes,
)
from simple_config_builder._native import (
    registry_get_class_str_from_class as _registry_get_class_str_from_class,
)
from simple_config_builder._native import (
    registry_is_registered as _registry_is_registered,
)
from simple_config_builder._native import (
    registry_list_classes as _registry_list_classes,
)
from simple_config_builder._native import (
    registry_list_subclasses as _registry_list_subclasses,
)
from simple_config_builder._native import (
    registry_register_class as _registry_register_class,
)
from simple_config_builder._native import set_config_attr as _set_config_attr


class Configclass(_NativeConfigclass):
    """
    Base class for all config classes.

    Subclass this and declare fields as type-annotated class attributes.
    Plain Python values are treated as defaults; use :func:`Field` to add
    validation constraints (``gt``, ``lt``) or a ``default_factory``.

    The Rust backend collects field metadata on class definition,
    validates every attribute assignment, and provides serialization.

    Example
    -------
    >>> from simple_config_builder.config import Configclass, Field
    >>> class Config(Configclass):
    ...     name: str = "default"
    ...     workers: int = Field(gt=0, lt=33, default=4)
    >>> cfg = Config()
    >>> cfg.name
    'default'
    >>> cfg.workers
    4
    >>> cfg.workers = 8
    >>> cfg.model_dump()["workers"]
    8
    """

    def __new__(cls, *args, **kwargs):
        """Accept keyword construction before native initialization."""
        return super().__new__(cls)

    def __init_subclass__(cls, **kwargs):
        """
        Register the subclass and configure its fields in the Rust backend.

        Called automatically when a class body is executed. You never need to
        call this directly.
        """
        super().__init_subclass__(**kwargs)
        _configure_config_class(cls)
        ConfigClassRegistry.register(cls)

    def __init__(self, **data):
        """
        Create a config instance, optionally overriding field defaults.

        Parameters
        ----------
        **data:
            Initial field values. Any field not supplied takes its declared
            default. Unknown keys raise ``ValueError``.

        Example
        -------
        >>> from simple_config_builder.config import Configclass
        >>> class Config(Configclass):
        ...     host: str = "localhost"
        ...     port: int = 8080
        >>> Config(host="example.com").host
        'example.com'
        >>> Config().port
        8080
        """
        _init_config_instance(self, data)

    def __setattr__(self, name: str, value: Any):
        """
        Set a field, running Rust-side validation before accepting the value.

        Raises ``ValueError`` if the value violates a ``gt`` / ``lt``
        constraint or has the wrong type.
        """
        if _set_config_attr(self, name, value):
            return
        super().__setattr__(name, value)

    def model_dump(self) -> dict[str, Any]:
        """
        Serialize the config instance to a plain Python dictionary.

        Nested :class:`Configclass` instances are also converted to dicts
        recursively.

        Example
        -------
        >>> from simple_config_builder.config import Configclass
        >>> class Config(Configclass):
        ...     host: str = "localhost"
        ...     port: int = 8080
        >>> Config().model_dump()
        {'_config_class_type': 'simple_config_builder.config.Config', \
'host': 'localhost', 'port': 8080}
        """
        return _model_dump(self)

    def model_dump_json(self) -> str:
        """
        Serialize the config instance to a compact JSON string.

        Example
        -------
        >>> from simple_config_builder.config import Configclass
        >>> import json
        >>> class Config(Configclass):
        ...     name: str = "demo"
        >>> json.loads(Config().model_dump_json())["name"]
        'demo'
        """
        return _model_dump_json(self)

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "Configclass":
        """
        Build a config instance from a plain dictionary, validating all fields.

        Parameters
        ----------
        data:
            Dictionary of field values. Unknown keys raise ``ValueError``.

        Example
        -------
        >>> from simple_config_builder.config import Configclass
        >>> class Config(Configclass):
        ...     host: str = "localhost"
        ...     port: int = 8080
        >>> cfg = Config.model_validate(
        ...     {"host": "db.example.com", "port": 5432}
        ... )
        >>> cfg.host
        'db.example.com'
        """
        instance = cls.__new__(cls)
        _init_config_instance(instance, data)
        return instance

    @classmethod
    def model_validate_json(cls, data: str | bytes) -> "Configclass":
        """
        Build a config instance from a JSON string or bytes.

        All fields are validated.

        Example
        -------
        >>> from simple_config_builder.config import Configclass
        >>> class Config(Configclass):
        ...     host: str = "localhost"
        >>> cfg = Config.model_validate_json('{"host": "prod.example.com"}')
        >>> cfg.host
        'prod.example.com'
        """
        return cls.model_validate(_model_validate_json(data))

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        """
        Return a JSON Schema dict describing this config class.

        The schema reflects field types and ``gt`` / ``lt`` constraints and
        can be used for validation in other tools or for documentation.

        Example
        -------
        >>> from simple_config_builder.config import Configclass, Field
        >>> class Config(Configclass):
        ...     port: int = Field(gt=0, lt=65536, default=8080)
        >>> schema = Config.model_json_schema()
        >>> "port" in schema.get("properties", {})
        True
        """
        return _model_json_schema(cls)


class ConfigClassRegistry:
    """
    Global registry of all :class:`Configclass` subclasses.

    Classes are registered automatically when their class body is executed
    (via :meth:`Configclass.__init_subclass__`). You only need to interact
    with this directly when looking up classes by fully-qualified name, e.g.
    when deserializing config data that embeds a ``_config_class_type`` key.

    Example
    -------
    >>> from simple_config_builder.config import (
    ...     Configclass,
    ...     ConfigClassRegistry,
    ... )
    >>> class MyConfig(Configclass):
    ...     value: int = 1
    >>> ConfigClassRegistry.is_registered(MyConfig)
    True
    >>> any("MyConfig" in c for c in ConfigClassRegistry.list_classes())
    True
    """

    @classmethod
    def get_class_str_from_class(cls, class_to_register: type):
        """
        Return the fully-qualified ``module.ClassName`` string for a class.

        This string is used as the key in the registry and as the
        ``_config_class_type`` value embedded in serialized config files.
        """
        return _registry_get_class_str_from_class(class_to_register)

    @classmethod
    def register[T](cls, class_to_register: type[T]):
        """
        Register a class in the global registry.

        Called automatically by :meth:`Configclass.__init_subclass__`.
        Raises ``ValueError`` if the class is already registered.
        """
        _registry_register_class(class_to_register)

    @classmethod
    def list_classes(cls) -> list[str]:
        """
        Return fully-qualified names.

        Returns all registered :class:`Configclass` subclasses.
        """
        return _registry_list_classes()

    @classmethod
    def is_registered(cls, class_to_register) -> bool:
        """Return ``True`` if the given class is already in the registry."""
        return _registry_is_registered(class_to_register)

    @classmethod
    def get(cls, class_name) -> Type[Configclass]:
        """
        Look up and return a registered class by its fully-qualified name.

        Parameters
        ----------
        class_name:
            A string of the form ``"module.ClassName"``.

        Raises
        ------
        KeyError
            If no class with that name is registered.
        """
        return _registry_get(class_name)

    @classmethod
    def get_class_attributes(cls, class_name: str) -> dict[str, Any]:
        """
        Return the declared fields of a registered class as a dict.

        Keys are field names; values are :class:`FieldInfo` objects from
        the Rust backend.
        """
        return _registry_get_class_attributes(class_name)

    @classmethod
    def list_subclasses(
        cls,
        base_class: str | type[Configclass],
        *,
        include_base: bool = False,
        recursive: bool = False,
    ) -> list[str]:
        """
        Return fully-qualified names of registered subclasses.

        Returns subclasses of ``base_class``.
        ----------
        base_class:
            The class (or its fully-qualified name string) whose subclasses
            to list.
        include_base:
            If ``True``, include ``base_class`` itself in the result.
        recursive:
            If ``True``, include indirect subclasses (grandchildren, etc.).
        """
        return _registry_list_subclasses(
            base_class,
            include_base=include_base,
            recursive=recursive,
        )


__all__ = [
    "Configclass",
    "ConfigClassRegistry",
    "Field",
]
