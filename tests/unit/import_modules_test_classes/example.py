"""Test class for the import_modules_from_directory function."""

from simple_config_builder import Configclass


class Example(Configclass):
    """Example config class."""

    value: int
    name: str


class Example2(Configclass):
    """Example config class."""

    value: int
    name: str
