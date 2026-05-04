"""
Configparser — file-backed config loader with optional autosave / autoreload.

:class:`Configparser` reads a JSON, YAML or TOML file, constructs the
corresponding :class:`~simple_config_builder.config.Configclass` objects, and
optionally writes changes back or polls for external changes.

Typical workflow
----------------
Write a config file once, then use ``Configparser`` throughout the application:

.. code-block:: python

    from simple_config_builder import Configclass, Configparser, ConfigTypes, Field

    class ServerConfig(Configclass):
        host: str = "localhost"
        port: int = Field(gt=0, lt=65536, default=8080)

    # Parse an existing file (format inferred from extension):
    parser = Configparser("server.yaml")
    cfg: ServerConfig = parser.config_data

    # Mutate and save:
    cfg.port = 443
    parser.save()

    # Create from Python data and write to disk:
    parser2 = Configparser.from_python(
        ServerConfig(host="prod.example.com"),
        "prod.yaml",
        ConfigTypes.YAML,
    )
    parser2.save()
"""

from threading import Timer
from typing import Any

from simple_config_builder.config import Configclass
from simple_config_builder.config_io import parse_config, write_config
from simple_config_builder.config_types import ConfigTypes


class Configparser:
    """Load, save and optionally watch a config file.

    The file format is detected from the file extension (``.json``, ``.yaml``,
    ``.toml``) unless you supply ``config_type`` explicitly.

    Parameters
    ----------
    config_file:
        Path to the configuration file.
    config_type:
        Format override. If ``None`` the extension is used.
    autosave:
        When ``True``, any change to :attr:`config_data` is written back to
        disk approximately one second later. Cannot be combined with
        ``autoreload``.
    autoreload:
        When ``True``, the file is re-read every second and :attr:`config_data`
        is updated if the file has changed. Cannot be combined with
        ``autosave``.

    Raises
    ------
    ValueError
        If the format cannot be determined, or if both ``autosave`` and
        ``autoreload`` are requested.
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
        """Load the config file and initialise the parser.

        Parameters
        ----------
        config_file:
            Path to the configuration file. The format is inferred from
            the extension (``.json``, ``.yaml``, ``.toml``) unless
            ``config_type`` is given.
        config_type:
            Explicit format override. Pass one of :class:`ConfigTypes`.
        autosave:
            Automatically persist changes to :attr:`config_data` after
            roughly one second. Mutually exclusive with ``autoreload``.
        autoreload:
            Poll the file every second and refresh :attr:`config_data` if
            the file has changed on disk. Mutually exclusive with
            ``autosave``.

        Raises
        ------
        ValueError
            If the format cannot be determined from the extension, or if
            both ``autosave`` and ``autoreload`` are ``True``.
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
        """Create a :class:`Configparser` pre-populated with in-memory data.

        The file is read first (to satisfy the constructor), then
        :attr:`config_data` is replaced with ``data``.  Use :meth:`save`
        afterwards to write ``data`` to disk.

        Parameters
        ----------
        data:
            Config data to store — a :class:`Configclass` instance, a plain
            ``dict`` or a ``list``.
        config_file:
            Destination file path.
        config_type:
            Format override; inferred from the extension when ``None``.
        autosave:
            Enable autosave after creation.
        autoreload:
            Enable autoreload after creation.

        Returns
        -------
        Configparser
            A parser whose :attr:`config_data` is ``data``.
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
        """Infer the config format from the file extension.

        Returns
        -------
        ConfigTypes
            The detected format.

        Raises
        ------
        ValueError
            If the extension is not ``.json``, ``.yaml`` or ``.toml``.
        """
        if self.config_file.endswith(".json"):
            return ConfigTypes.JSON
        if self.config_file.endswith(".yaml"):
            return ConfigTypes.YAML
        if self.config_file.endswith(".toml"):
            return ConfigTypes.TOML
        raise ValueError("The configuration type is not supported.")

    def _auto_save_config(self):
        """Schedule a background timer that writes :attr:`config_data` when it changes."""
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
        """Schedule a background timer that refreshes :attr:`config_data` when the file changes."""

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
        """Check whether :attr:`config_data` contains a given field name or type.

        Searches recursively through nested :class:`Configclass` objects,
        dicts and lists.  Exactly one of ``config_field_type`` or
        ``config_field`` must be supplied.

        Parameters
        ----------
        config_field_type:
            A Python type to search for (e.g. ``DatabaseConfig``).
        config_field:
            A field name string to search for (e.g. ``"host"``).

        Returns
        -------
        bool
            ``True`` if the field name or an instance of the type is found
            anywhere in the config tree.

        Raises
        ------
        ValueError
            If neither or both arguments are supplied.
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
                for name in type(config_data).__config_fields__.keys():
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
                if field in list(type(config_data).__config_fields__.keys()):
                    return True
                for name in type(config_data).__config_fields__.keys():
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
        """Write :attr:`config_data` to :attr:`config_file` immediately."""
        if self.config_type is None:
            return
        write_config(self.config_file, self.config_data, self.config_type)

    def reload(self):
        """Re-read :attr:`config_file` and update :attr:`config_data` in place."""
        if self.config_type is None:
            return
        self.config_data = parse_config(self.config_file, self.config_type)
