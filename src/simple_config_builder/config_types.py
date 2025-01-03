"""The module defines the configuration types using an enumeration."""

from enum import Enum


class ConfigTypes(Enum):
    """
    The enumeration of the configuration types.

    The enumeration defines the configuration types that are supported by the
    configuration manager. The configuration types are used to determine the
    format of the configuration file.
    """

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
