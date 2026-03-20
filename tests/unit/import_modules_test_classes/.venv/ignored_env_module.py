"""Module that should never be discovered from a virtual environment dir."""

from simple_config_builder import Configclass


class EnvOnlyConfig(Configclass):
    """Config class under a fake virtual environment directory."""

    enabled: bool = True