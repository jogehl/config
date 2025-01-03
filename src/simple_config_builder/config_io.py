"""
The module contains the IO functions.

The IO functions are used to read and write the configuration file.
"""

from typing import Any

from serde import to_dict
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.config_types import ConfigTypes


def parse_config(config_file: str, config_type: ConfigTypes) -> dict:
    """
    Parse the configuration file.

    Params:
        config_file: The configuration file path.
        config_type: The configuration file type.

    Returns
    -------
        The configuration dictionary.
    """
    config_data_dct = {}
    match config_type:
        case ConfigTypes.JSON:
            config_data_dct = parse_json(config_file)
        case ConfigTypes.YAML:
            config_data_dct = parse_yaml(config_file)
        case ConfigTypes.TOML:
            config_data_dct = parse_toml(config_file)
        case _:
            raise ValueError("The configuration type is not supported.")
    return construct_config(config_data_dct)


def construct_config(config_data: Any):
    """Construct the configuration objects."""
    # If the configuration data is not a dictionary,
    if not isinstance(config_data, dict):
        return config_data

    # Recursively construct the configuration objects
    # from the configuration dictionary.
    for key, value in config_data.items():
        if isinstance(value, dict):
            config_data[key] = construct_config(value)
        if isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    value[i] = construct_config(item)
        if isinstance(value, tuple):
            value = list(value)
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    value[i] = construct_config(item)
            config_data[key] = tuple(value)
    if "_config_class_type" in config_data:
        config_class_type = config_data["_config_class_type"]
        config_class = ConfigClassRegistry.get(config_class_type)
        return config_class(**config_data)
    return config_data


def parse_json(config_file: str):
    """
    Parse the JSON configuration file.

    Params:
        config_file: The configuration file path.

    Returns
    -------
        The parsed json data.
    """
    import json

    with open(config_file, "r") as f:
        return json.load(f)


def parse_yaml(config_file: str):
    """
    Parse the YAML configuration file.

    Params:
        config_file: The configuration file path.

    Returns
    -------
        The parsed yaml data.
    """
    with open(config_file, "r") as f:
        import yaml

        return yaml.load(f, Loader=yaml.FullLoader)


def parse_toml(config_file: str):
    """
    Parse the TOML configuration file.

    Params:
        config_file: The configuration file path.

    Returns
    -------
        The parsed toml data.
    """
    import toml

    with open(config_file, "r") as f:
        return toml.load(f)


def write_config(
    config_file: str, config_data: dict, config_type: ConfigTypes
):
    """
    Write the configuration file.

    Params:
        config_file: The configuration file path.
        config_data: The configuration data.
        config_type: The configuration file type.
    """
    # try to make the data to a dictionary
    config_data = to_dict(config_data)
    match config_type:
        case ConfigTypes.JSON:
            write_json(config_file, config_data)
        case ConfigTypes.YAML:
            write_yaml(config_file, config_data)
        case ConfigTypes.TOML:
            write_toml(config_file, config_data)
        case _:
            raise ValueError("The configuration type is not supported.")


def write_json(config_file: str, config_data: dict):
    """
    Write the JSON configuration file.

    Params:
        config_file: The configuration file path.
        config_data: The configuration data.
    """
    import json

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=4)


def write_yaml(config_file: str, config_data: dict):
    """
    Write the YAML configuration file.

    Params:
        config_file: The configuration file path.
        config_data: The configuration data.
    """
    import yaml

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)


def write_toml(config_file: str, config_data: dict):
    """
    Write the TOML configuration file.

    Params:
        config_file: The configuration file path.
        config_data: The configuration data.
    """
    import toml

    with open(config_file, "w") as f:
        toml.dump(config_data, f)
