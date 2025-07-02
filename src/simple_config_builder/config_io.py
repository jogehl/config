"""
The module contains the IO functions.

The IO functions are used to read and write the configuration file.
"""

from typing import Any

import importlib
import os

from pydantic import BaseModel

from simple_config_builder.config import ConfigClassRegistry, Configclass
from simple_config_builder.config_types import ConfigTypes


def to_dict(obj: Any) -> dict | list | tuple:
    """
    Convert an object to a dictionary.

    Parameters
    ----------
    obj: The object to convert.

    Returns
    -------
    The converted dictionary.
    """
    if isinstance(obj, BaseModel):
        # If the object is a Pydantic model, convert it to a dictionary
        return obj.model_dump()
    if isinstance(obj, dict):
        return {key: to_dict(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(to_dict(item) for item in obj)
    return obj


def parse_config(
    config_file: str, config_type: ConfigTypes
) -> dict | list | Configclass:
    """
    Parse the configuration file.

    Parameters
    ----------
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
        if not isinstance(config_class_type, str):
            raise ValueError(
                "The _config_class_type must be a "
                "string representing the class type."
            )

        # cut of the class name if it is a full path
        if "." in config_class_type:
            config_class_module = config_class_type.rsplit(".", 1)[0]
        try:
            importlib.import_module(config_class_module)
        except ImportError:
            raise ImportError(
                f"Could not import the module '{config_class_module}'. "
                "Please make sure the module is installed and available "
                "in the Python path."
            )
        try:
            config_class = ConfigClassRegistry.get(config_class_type)
        except ValueError:
            raise ValueError(
                f"Please make sure the class '{config_class_type}' "
                f"is in the module '{config_class_module}'."
            )
        del config_data["_config_class_type"]

        # Log the expected fields of the config class
        expected_fields = set(config_class.__pydantic_fields__.keys())

        # Log the actual keys in the config data
        actual_keys = set(config_data.keys())

        # Check for mismatched keys
        mismatched_keys = actual_keys - expected_fields
        if mismatched_keys:
            raise ValueError(
                f"Mismatched keys in config data: {mismatched_keys}. "
                f"Expected fields: {expected_fields}"
            )
        # Filter config_data to include only expected fields
        filtered_config_data = {
            key: value
            for key, value in config_data.items()
            if key in expected_fields
        }

        # Pass filtered_config_data as a single dictionary argument
        return config_class.model_validate(filtered_config_data)
    return config_data


def parse_json(config_file: str):
    """
    Parse the JSON configuration file.

    If there is currently no configuration file,
    it will return an empty dictionary.

    Parameters
    ----------
    config_file: The configuration file path.

    Returns
    -------
    The parsed json data.
    """
    if not os.path.exists(config_file):
        return {}
    import json

    with open(config_file, "r") as f:
        return json.load(f)


def parse_yaml(config_file: str):
    """
    Parse the YAML configuration file.

    If there is currently no configuration file,
    it will return an empty dictionary.

    Parameters
    ----------
    config_file: The configuration file path.

    Returns
    -------
    The parsed yaml data.
    """
    if not os.path.exists(config_file):
        return {}
    with open(config_file, "r") as f:
        import yaml

        return yaml.load(f, Loader=yaml.FullLoader)


def parse_toml(config_file: str):
    """
    Parse the TOML configuration file.

    Parameters
    ----------
    config_file: The configuration file path.

    Returns
    -------
    The parsed toml data.
    """
    if not os.path.exists(config_file):
        return {}
    import toml

    with open(config_file, "r") as f:
        return toml.load(f)


def write_config(config_file: str, data: dict, config_type: ConfigTypes):
    """
    Write the configuration file.

    Parameters
    ----------
    config_file: The configuration file path.
    data: The configuration data.
    config_type: The configuration file type.
    """
    # try to make the data to a dictionary
    config_data = to_dict(data)
    match config_type:
        case ConfigTypes.JSON:
            write_json(config_file, config_data)
        case ConfigTypes.YAML:
            write_yaml(config_file, config_data)
        case ConfigTypes.TOML:
            write_toml(config_file, config_data)
        case _:
            raise ValueError("The configuration type is not supported.")


def write_json(config_file: str, config_data: dict | list | tuple):
    """
    Write the JSON configuration file.

    Parameters
    ----------
    config_file: The configuration file path.
    config_data: The configuration data.
    """
    import json

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=4)


def write_yaml(config_file: str, config_data: dict | list | tuple):
    """
    Write the YAML configuration file.

    Parameters
    ----------
    config_file: The configuration file path.
    config_data: The configuration data.
    """
    import yaml

    with open(config_file, "w") as f:
        yaml.dump(config_data, f)


def write_toml(config_file: str, config_data: dict | list | tuple):
    """
    Write the TOML configuration file.

    Parameters
    ----------
    config_file: The configuration file path.
    config_data: The configuration data.
    """
    import toml

    with open(config_file, "w") as f:
        toml.dump(config_data, f)


__all__ = ["to_dict", "parse_config", "write_config"]
