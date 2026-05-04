"""
simple_config_builder — schema-validated configuration for Python and Rust.

Define your config schema once as a Python class; validation, serialization
and JSON Schema generation are all handled by the Rust backend.

Quick start
-----------
>>> from simple_config_builder import Configclass, Field
>>> class ServerConfig(Configclass):
...     host: str = "localhost"
...     port: int = Field(gt=0, lt=65536, default=8080)
...     debug: bool = False
>>> cfg = ServerConfig()
>>> cfg.host
'localhost'
>>> cfg.port
8080
>>> cfg.port = 443
>>> cfg.port
443

Validation is enforced on every assignment:

>>> cfg.port = 99999
Traceback (most recent call last):
    ...
ValueError: ...

Serialize to a plain dict or JSON string at any time:

>>> isinstance(cfg.model_dump(), dict)
True
>>> import json
...
... data = json.loads(cfg.model_dump_json())
>>> data["port"]
443
"""

import simple_config_builder.rust_core as rust_core

from simple_config_builder.config import (
    ConfigClassRegistry,
    Configclass,
    Field,
)
from simple_config_builder.configparser import Configparser
from simple_config_builder.config_types import ConfigTypes

__all__ = [
    "Field",
    "ConfigClassRegistry",
    "Configclass",
    "Configparser",
    "ConfigTypes",
    "rust_core",
]
