"""The module defines the configuration types using an enumeration."""

from enum import Enum


class ConfigTypes(Enum):
    """The enumeration of the configuration types."""

    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
