"""Unit tests for the ConfigIO class."""

from unittest import TestCase

from config.config_io import (
    ConfigTypes,
    parse_config,
    write_config,
    write_json,
    write_yaml,
    write_toml,
    parse_json,
    parse_yaml,
    parse_toml,
)
from config.config import config_field, configclass


class TestConfigIOMethods(TestCase):
    """Test config_io methods."""

    def test_parse_json(self):
        """Test parsing a JSON configuration file."""
        config_data = parse_json("tests/unit/config_files/config.json")
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["key"], "value")

    def test_parse_yaml(self):
        """Test parsing a YAML configuration file."""
        config_data = parse_yaml("tests/unit/config_files/config.yaml")
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["key"], "value")

    def test_parse_toml(self):
        """Test parsing a TOML configuration file."""
        config_data = parse_toml("tests/unit/config_files/config.toml")
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["key"], "value")

    def test_write_json(self):
        """Test writing a JSON configuration file."""
        config_data = {"key": "value"}
        write_json("tests/unit/config_files/config.json", config_data)

        with open("tests/unit/config_files/config.json", "r") as f:
            written_data = f.read()

        self.assertEqual(written_data, '{\n    "key": "value"\n}')

    def test_write_yaml(self):
        """Test writing a YAML configuration file."""
        config_data = {"key": "value"}
        write_yaml("tests/unit/config_files/config.yaml", config_data)

        with open("tests/unit/config_files/config.yaml", "r") as f:
            written_data = f.read()

        self.assertEqual(written_data, "key: value\n")

    def test_write_toml(self):
        """Test writing a TOML configuration file."""
        config_data = {"key": "value"}
        write_toml("tests/unit/config_files/config.toml", config_data)

        with open("tests/unit/config_files/config.toml", "r") as f:
            written_data = f.read()

        self.assertEqual(written_data, 'key = "value"\n')

    def test_parse_config(self):
        """Test parsing a configuration file."""
        config_data = parse_config(
            "tests/unit/config_files/config.json", ConfigTypes.JSON
        )
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["key"], "value")

    def test_write_config(self):
        """Test writing a configuration file."""
        config_data = {"key": "value"}
        write_config(
            "tests/unit/config_files/config.json",
            config_data,
            ConfigTypes.JSON,
        )

        with open("tests/unit/config_files/config.json", "r") as f:
            written_data = f.read()

        self.assertEqual(written_data, '{\n    "key": "value"\n}')

    def test_write_config_with_configclass(self):
        """Test writing a configuration file with a ConfigClass."""
        config_data = {"test": _TestClassConfigWithConfigClass()}
        write_config(
            "tests/unit/config_files/config_with_class.json",
            config_data,
            ConfigTypes.JSON,
        )

        with open("tests/unit/config_files/config_with_class.json", "r") as f:
            written_data = f.read()

        import json

        written_data_dct = json.loads(written_data)

        self.assertIsInstance(written_data_dct, dict)
        self.assertEqual(written_data_dct["test"]["key"], "value")

    def test_parse_config_with_configclass(self):
        """Test parsing a configuration file with a ConfigClass."""
        config_data = parse_config(
            "tests/unit/config_files/config_with_class.json", ConfigTypes.JSON
        )
        self.assertIsInstance(config_data, dict)
        print(config_data)
        self.assertEqual(config_data["test"].key, "value")

@configclass
class _TestClassConfigWithConfigClass:
    key: str = config_field(default="value")