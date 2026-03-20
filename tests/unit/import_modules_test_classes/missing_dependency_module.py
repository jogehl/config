"""Test module with an intentionally missing dependency."""

import dependency_that_does_not_exist_for_config_tests

from simple_config_builder import Configclass


class MissingDependencyConfig(Configclass):
    """Config class that should be skipped during discovery."""

    enabled: bool = True