"""
The configparser module.

The module contains the configparser class. The configparser class is used to
parse the configuration file and construct the configuration objects.
It gives the ability to autosave the configuration file when the configuration
objects are updated.
"""

from threading import Timer
from typing import Any

from simple_config_builder.config import Configclass
from simple_config_builder.config_io import parse_config, write_config
from simple_config_builder.config_types import ConfigTypes


class Configparser:
    """
    The Configparser class.

    The Configparser class is used to parse the configuration file and
    construct the configuration objects. It gives the ability to autosave
    the configuration file when the configuration objects are updated.
    """

    config_file: str
    config_type: ConfigTypes | None
    autosave: bool
    autoreload: bool
    config_data: dict | list | Configclass

    def __init__(
        self,
        config_file: str,
        config_type: ConfigTypes | None = None,
        autosave: bool = False,
        autoreload: bool = False,
    ):
        """
        Initialize the configparser.

        Parameters
        ----------
        config_file: The configuration file path.
        config_type: The configuration type. Defaults to None.
        autosave: Autosave the configuration file. Defaults to False.
        autoreload: Autoreload the configuration file. Defaults to False.

        Raises
        ------
        ValueError: If the configuration type is not recognized.
        ValueError: If the configuration type is not supported.
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
            if self.config_type is None:
                raise ValueError("The configuration type is not recognized.")
        if self.config_type is None:
            raise ValueError("The configuration type is not supported.")
        # first read
        self.config_data = parse_config(self.config_file, self.config_type)
        if self.autoreload:
            self._auto_reload_config()
        if self.autosave:
            self._auto_save_config()

    @classmethod
    def from_python(
        cls,
        data: dict | Configclass | list,
        config_file: str,
        config_type: ConfigTypes | None = None,
        autosave: bool = False,
        autoreload: bool = False,
    ) -> "Configparser":
        """
        Create a Configparser instance from Python data.

        Parameters
        ----------
        data: The configuration data as a dictionary, Configclass, or list.
        config_file: The configuration file path.
        config_type: The configuration type.
        autosave: Autosave the configuration file. Defaults to False.
        autoreload: Autoreload the configuration file. Defaults to False.

        Returns
        -------
            A Configparser instance with the given data.
        """
        configparser = cls(
            config_file=config_file,
            config_type=config_type,
            autosave=autosave,
            autoreload=autoreload,
        )
        configparser.config_data = data
        return configparser

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
            if self.config_type is None:
                return
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
            if self.config_type is None:
                return
            new_config_data = parse_config(self.config_file, self.config_type)
            if new_config_data != self.config_data:
                self.config_data = new_config_data

        Timer(1, _reload_config).start()

    def contains(
        self, config_field_type: Any = None, config_field: str | None = None
    ) -> bool:
        """
        Check if the configuration data contains the given field or type.

        The method returns the first occurrence of the field or type in the
        configuration data. Either `config_field_type` or `config_field`
        must be provided, but not both.

        Parameters
        ----------
        config_field_type: The type to check for in the configuration data.
        config_field: The field to check for in the configuration data.

        Returns
        -------
        bool: True if the configuration data contains the field or type.

        Raises
        ------
        ValueError: If neither `config_field_type` nor `config_field` is
                    provided.
        ValueError: If both `config_field_type` and `config_field`
                    are provided.
        """

        def _contains_type(config_data, config_type: Any) -> bool:
            if isinstance(config_data, dict):
                for key, value in config_data.items():
                    if isinstance(value, config_type):
                        return True
                    if _contains_type(value, config_type):
                        return True
            elif isinstance(config_data, list):
                for item in config_data:
                    if isinstance(item, config_type):
                        return True
                    if _contains_type(item, config_type):
                        return True
            elif isinstance(config_data, Configclass):
                if isinstance(config_data, config_type):
                    return True
                for name in type(config_data).model_fields.keys():
                    if _contains_type(getattr(config_data, name), config_type):
                        return True
            elif isinstance(config_data, config_type):
                return True
            return False

        def _contains_field(config_data, field: str) -> bool:
            if isinstance(config_data, dict):
                if field in config_data:
                    return True
                for value in config_data.values():
                    if _contains_field(value, field):
                        return True
            elif isinstance(config_data, list):
                if field in config_data:
                    return True
                for item in config_data:
                    if _contains_field(item, field):
                        return True
            elif isinstance(config_data, Configclass):
                if field in list(type(config_data).model_fields.keys()):
                    return True
                for name in type(config_data).model_fields.keys():
                    if _contains_field(getattr(config_data, name), field):
                        return True
            return False

        if config_field_type is None and config_field is None:
            msg = (
                "Either config_field_type or config_field " "must be provided."
            )
            raise ValueError(msg)
        if config_field_type is not None and config_field is not None:
            msg = (
                "Only one of config_field_type or config_field"
                "can be provided."
            )
            raise ValueError(msg)
        if config_field is not None:
            return _contains_field(self.config_data, config_field)
        if config_field_type is not None:
            return _contains_type(self.config_data, config_field_type)
        return False

    def save(self):
        """Save the configuration data to the configuration file."""
        if self.config_type is None:
            return
        write_config(self.config_file, self.config_data, self.config_type)

    def reload(self):
        """Reload the configuration data from the configuration file."""
        if self.config_type is None:
            return
        self.config_data = parse_config(self.config_file, self.config_type)
