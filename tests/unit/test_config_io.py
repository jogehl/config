"""Unit tests for the ConfigIO class."""

from unittest import TestCase

from simple_config_builder.config_io import (
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
from simple_config_builder.config import config_field, configclass


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

    def test_write_config_with_configclass_json(self):
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

    def test_parse_config_with_configclass_json(self):
        """Test parsing a configuration file with a ConfigClass."""
        config_data = parse_config(
            "tests/unit/config_files/config_with_class.json", ConfigTypes.JSON
        )
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["test"].key, "value")

        self.assertIsInstance(
            config_data["test"].sub_key, _TestClassConfigInnerWithConfigClass
        )
        self.assertEqual(config_data["test"].sub_key.key, "value")

    def test_write_config_with_configclass_yaml(self):
        """Test writing a configuration file with a ConfigClass."""
        config_data = {"test": _TestClassConfigWithConfigClass()}
        write_config(
            "tests/unit/config_files/config_with_class.yaml",
            config_data,
            ConfigTypes.YAML,
        )

        import yaml

        with open("tests/unit/config_files/config_with_class.yaml", "r") as f:
            written_data = f.read()

        written_data_dct = yaml.safe_load(written_data)

        self.assertIsInstance(written_data_dct, dict)
        self.assertEqual(written_data_dct["test"]["key"], "value")

    def test_parse_config_with_configclass_yaml(self):
        """Test parsing a configuration file with a ConfigClass."""
        config_data = parse_config(
            "tests/unit/config_files/config_with_class.yaml", ConfigTypes.YAML
        )
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["test"].key, "value")

        self.assertIsInstance(
            config_data["test"].sub_key, _TestClassConfigInnerWithConfigClass
        )
        self.assertEqual(config_data["test"].sub_key.key, "value")

    def test_write_config_with_configclass_toml(self):
        """Test writing a configuration file with a ConfigClass."""
        config_data = {"test": _TestClassConfigWithConfigClass()}
        write_config(
            "tests/unit/config_files/config_with_class.toml",
            config_data,
            ConfigTypes.TOML,
        )

        import toml

        with open("tests/unit/config_files/config_with_class.toml", "r") as f:
            written_data = f.read()

        written_data_dct = toml.loads(written_data)

        self.assertIsInstance(written_data_dct, dict)
        self.assertEqual(written_data_dct["test"]["key"], "value")

    def test_parse_config_with_configclass_toml(self):
        """Test parsing a configuration file with a ConfigClass."""
        config_data = parse_config(
            "tests/unit/config_files/config_with_class.toml", ConfigTypes.TOML
        )
        self.assertIsInstance(config_data, dict)
        self.assertEqual(config_data["test"].key, "value")

        self.assertIsInstance(
            config_data["test"].sub_key, _TestClassConfigInnerWithConfigClass
        )
        self.assertEqual(config_data["test"].sub_key.key, "value")


@configclass
class _TestClassConfigInnerWithConfigClass:
    key: str = config_field(default="value")


@configclass
class _TestClassConfigWithConfigClass:
    key: str = config_field(default="value")
    list_key: list = config_field(default_factory=lambda: ["value1", "value2"])
    int_key: int = config_field(default=1)
    float_key: float = config_field(default=1.0)
    bool_key: bool = config_field(default=True)
    dict_key: dict = config_field(default_factory=lambda: {"key": "value"})
    list_dict_key: list = config_field(
        default_factory=lambda: [{"key": "value"}]
    )
    sub_key: _TestClassConfigInnerWithConfigClass = config_field(
        default_factory=lambda: _TestClassConfigInnerWithConfigClass()
    )
    sub_list_key: list[_TestClassConfigInnerWithConfigClass] = config_field(
        default_factory=lambda: [
            _TestClassConfigInnerWithConfigClass(),
            _TestClassConfigInnerWithConfigClass(),
        ]
    )
