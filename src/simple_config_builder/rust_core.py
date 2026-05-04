"""Python bridge to the pure-Rust configuration core.

The functions here call into the compiled ``_native`` extension, which runs the
`simple_config_builder_core` Rust crate directly.  This is the lower-level
alternative to :class:`~simple_config_builder.config.Configclass`; it works
with plain dicts rather than typed Python classes.

Example
-------
>>> from simple_config_builder import rust_core
>>> d = rust_core.defaults()
>>> isinstance(d, dict)
True
>>> validated = rust_core.validate(rust_core.defaults())
>>> validated == d
True
"""

from __future__ import annotations

from typing import Any, Literal

from simple_config_builder._native import rust_core_apply_defaults
from simple_config_builder._native import rust_core_defaults
from simple_config_builder._native import rust_core_load
from simple_config_builder._native import rust_core_schema
from simple_config_builder._native import rust_core_validate
from simple_config_builder._native import rust_core_write

ConfigFormat = Literal["json", "yaml", "toml"]


def schema() -> dict[str, Any]:
    """Return the JSON Schema produced by the Rust core type.

    The schema is generated at compile time via ``schemars`` and reflects
    every field declared in the Rust struct, including range constraints.

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> s = rust_core.schema()
    >>> 'properties' in s
    True
    """
    return rust_core_schema()


def defaults() -> dict[str, Any]:
    """Return the Rust core default configuration as a plain dict.

    Each key corresponds to a field in the Rust struct and carries the
    value declared as ``default`` in the Rust source.

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> d = rust_core.defaults()
    >>> isinstance(d, dict)
    True
    >>> len(d) > 0
    True
    """
    return rust_core_defaults()


def validate(data: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize ``data`` against the Rust core type.

    Passes ``data`` through the Rust-side ``garde`` validator.  Missing keys
    default to the Rust default value; extra keys raise an error.

    Parameters
    ----------
    data:
        A dict whose keys match the Rust struct fields.

    Returns
    -------
    dict
        The same data after validation and normalization.

    Raises
    ------
    ValueError
        If validation fails (e.g. a value out of range).

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> result = rust_core.validate(rust_core.defaults())
    >>> result == rust_core.defaults()
    True
    """
    return rust_core_validate(data)


def load(path: str, format: ConfigFormat) -> dict[str, Any]:
    """Load and validate a config file using the Rust core.

    Parameters
    ----------
    path:
        Path to the file on disk.
    format:
        One of ``"json"``, ``"yaml"``, ``"toml"``.

    Returns
    -------
    dict
        The validated configuration as a plain Python dict.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    ValueError
        If the file cannot be deserialized or fails validation.

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> import tempfile, os, json
    >>> cfg = rust_core.defaults()
    >>> with tempfile.NamedTemporaryFile(
    ...     mode="w", suffix=".json", delete=False
    ... ) as f:
    ...     json.dump(cfg, f)
    ...     path = f.name
    >>> loaded = rust_core.load(path, "json")  # doctest: +SKIP
    >>> os.unlink(path)
    """
    return rust_core_load(path, format)


def write(path: str, data: dict[str, Any], format: ConfigFormat) -> None:
    """Validate ``data`` and write it to a file using the Rust core.

    Parameters
    ----------
    path:
        Destination file path. The file is created or overwritten.
    data:
        Configuration dict to serialize. Must pass Rust-side validation.
    format:
        One of ``"json"``, ``"yaml"``, ``"toml"``.

    Raises
    ------
    OSError
        If the file cannot be written.
    ValueError
        If ``data`` fails validation.

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> import tempfile, os
    >>> with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
    ...     path = f.name
    >>> rust_core.write(path, rust_core.defaults(), "json")  # doctest: +SKIP
    >>> os.unlink(path)
    """
    rust_core_write(path, data, format)


def apply_defaults(overrides: dict[str, Any]) -> dict[str, Any]:
    """Merge ``overrides`` onto the Rust defaults and validate the result.

    Any key present in ``overrides`` replaces the corresponding default;
    all other fields keep their Rust-declared defaults.

    Parameters
    ----------
    overrides:
        A (possibly partial) dict of field values to apply on top of
        :func:`defaults`.

    Returns
    -------
    dict
        Complete, validated configuration with overrides applied.

    Example
    -------
    >>> from simple_config_builder import rust_core
    >>> d = rust_core.defaults()
    >>> first_key = next(iter(d))
    >>> override_val = d[first_key]  # use the default value as-is
    >>> result = rust_core.apply_defaults({first_key: override_val})
    >>> result[first_key] == override_val
    True
    """
    return rust_core_apply_defaults(overrides)


__all__ = [
    "ConfigFormat",
    "apply_defaults",
    "defaults",
    "load",
    "schema",
    "validate",
    "write",
]