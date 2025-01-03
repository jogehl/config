"""
The configparser module.

The module contains the configparser class. The configparser class is used to
parse the configuration file and construct the configuration objects.
It gives the ability to autosave the configuration file when the configuration
objects are updated.
"""

from threading import Timer

from simple_config_builder.config_io import parse_config, write_config
from simple_config_builder.config_types import ConfigTypes


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
        config_type: ConfigTypes | None = None,
        autosave: bool = False,
        autoreload: bool = False,
    ):
        """
        Initialize the configparser.

        Params:
            config_file: The configuration file path.
            config_type: The configuration type. Defaults to None.
            autosave: Autosave the configuration file. Defaults to False.
            autoreload: Autoreload the configuration file. Defaults to False.
        """
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
        """
        Get the configuration type from the configuration file.

        Returns
        -------
            The configuration type.
        """
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

    def __setitem__(self, key, value):
        """
        Set the value for the given key in the configuration data.

        Params:
            key: The key in the configuration data.
            value: The value to set for the key.
        """
        self.config_data[key] = value

    def __getitem__(self, key):
        """
        Get the value for the given key in the configuration data.

        Params:
            key: The key in the configuration data.

        Returns
        -------
            The value for the key.
        """
        return self.config_data[key]

    def __delitem__(self, key):
        """Delete the key from the configuration data."""
        del self.config_data[key]

    def save(self):
        """Save the configuration data to the configuration file."""
        write_config(self.config_file, self.config_data, self.config_type)

    def reload(self):
        """Reload the configuration data from the configuration file."""
        self.config_data = parse_config(self.config_file, self.config_type)
