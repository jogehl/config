"""Placeholder module used to test unreadable source handling."""

from simple_config_builder import Configclass


class UnreadableConfig(Configclass):
    """Config class that should be skipped when source decoding fails."""

    enabled: bool = True