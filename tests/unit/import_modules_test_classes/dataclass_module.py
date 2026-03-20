"""Test module mixing Configclass and dataclass declarations."""

from dataclasses import dataclass

from simple_config_builder import Configclass


class DataclassBackedConfig(Configclass):
    """Config class used to validate dynamic import behavior."""

    enabled: bool = True


@dataclass
class PlainDataclass:
    """Regular dataclass that should not break module import."""

    value: int = 1