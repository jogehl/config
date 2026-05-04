"""
config_io — low-level file I/O for config data.

These functions read and write JSON, YAML and TOML files, constructing
:class:`~simple_config_builder.config.Configclass` instances where the data
contains a ``_config_class_type`` key, or returning plain dicts otherwise.

Most users should use :class:`~simple_config_builder.configparser.Configparser`
instead of calling these functions directly.

Key functions
-------------
``parse_config(path, config_type)``
    Read a file and return the data (dict, list, or Configclass instance).

``write_config(path, data, config_type)``
    Serialize ``data`` and write it to ``path``.

``to_dict(obj)``
    Convert any config object (including nested Configclass) to a plain dict.

Example
-------
.. code-block:: python

    import tempfile, os
    from simple_config_builder import Configclass, ConfigTypes
    from simple_config_builder.config_io import write_config, parse_config

    class Config(Configclass):
        host: str = "localhost"
        port: int = 8080

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        path = f.name

    write_config(path, Config(), ConfigTypes.JSON)
    data = parse_config(path, ConfigTypes.JSON)
    # data is a plain dict when no _config_class_type is embedded:
    assert data["host"] == "localhost"
    os.unlink(path)
"""

from typing import Any

from simple_config_builder._native import io_construct_config as construct_config
from simple_config_builder._native import io_parse_config as parse_config
from simple_config_builder._native import io_parse_json as parse_json
from simple_config_builder._native import io_parse_toml as parse_toml
from simple_config_builder._native import io_parse_yaml as parse_yaml
from simple_config_builder._native import io_to_dict as to_dict
from simple_config_builder._native import io_write_config as write_config
from simple_config_builder._native import io_write_json as write_json
from simple_config_builder._native import io_write_toml as write_toml
from simple_config_builder._native import io_write_yaml as write_yaml
from simple_config_builder.config import Configclass
from simple_config_builder.config_types import ConfigTypes

__all__ = [
    "to_dict",
    "parse_config",
    "construct_config",
    "write_config",
    "parse_json",
    "parse_yaml",
    "parse_toml",
    "write_json",
    "write_yaml",
    "write_toml",
    "ConfigTypes",
    "Configclass",
    "Any",
]
