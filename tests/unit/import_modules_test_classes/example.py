"""Test class for the import_modules_from_directory function."""

from simple_config_builder.config import configclass


@configclass
class Example:
    """Example config class."""

    value: int
    name: str


@configclass
class Example2:
    """Example config class."""

    value: int
    name: str
