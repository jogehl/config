"""
The configparser module.

The module contains the configparser class. The configparser class is used to
parse the configuration file and construct the configuration objects.
It gives the ability to autosave the configuration file when the configuration
objects are updated.
"""

from threading import Timer

from config.config_io import parse_config, write_config
from config.config_types import ConfigTypes


class Configparser:
    """
    The Configparser class.

    The Configparser class is used to parse the configuration file and
    construct the configuration objects. It gives the ability to autosave
    the configuration file when the configuration objects are updated.
    """

    def __init__(
        self,
        config_file: str,
        config_type: ConfigTypes | None=None,
        autosave: bool = False,
        autoreload: bool = False,
    ):
        """Initialize the configparser."""
        self.config_file = config_file
        self.config_type = config_type
        self.autosave = autosave
        self.autoreload = autoreload
        if self.autoreload and self.autosave:
            raise ValueError(
                "Autoreload and autosave cannot be enabled at the same time."
            )

        if self.config_type is None:
            self.config_type = self._get_config_type()
        # first read
        self.config_data = parse_config(self.config_file, self.config_type)
        if self.autoreload:
            self._auto_reload_config()
        if self.autosave:
            self._auto_save_config()

    def _get_config_type(self) -> ConfigTypes:
        """Get the configuration type from the configuration file."""
        if self.config_file.endswith(".json"):
            return ConfigTypes.JSON
        if self.config_file.endswith(".yaml"):
            return ConfigTypes.YAML
        if self.config_file.endswith(".toml"):
            return ConfigTypes.TOML
        raise ValueError("The configuration type is not supported.")

    def _auto_save_config(self):
        """Autosave the configuration file."""
        self._old_config_data = self.config_data

        def _save_config():
            if self._old_config_data != self.config_data:
                write_config(
                    self.config_file, self.config_data, self.config_type
                )
                self._old_config_data = self.config_data

        Timer(1, _save_config).start()

    def _auto_reload_config(self):
        """Autoreload the configuration file."""
        # Check for changes in the configuration file 
        def _reload_config():
            new_config_data = parse_config(self.config_file, self.config_type)
            if new_config_data != self.config_data:
                self.config_data = new_config_data
       

        Timer(1, _reload_config).start()