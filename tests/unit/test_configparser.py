"""Test for configparser Class."""

from unittest import TestCase

from simple_config_builder.configparser import Configparser, ConfigTypes


class TestConfigparser(TestCase):
    """Test Configparser class."""

    def test_configparser(self):
        """Test Configparser class."""
        config = Configparser("tests/unit/config_files/configparser.json")
        self.assertEqual(
            config.config_file, "tests/unit/config_files/configparser.json"
        )
        self.assertEqual(config.config_type, ConfigTypes.JSON)
        self.assertFalse(config.autosave)
        self.assertFalse(config.autoreload)
        self.assertEqual(config.config_data, {"key": "value"})

        # Test init with config_type
        config = Configparser(
            "tests/unit/config_files/configparser.json", ConfigTypes.JSON
        )
        self.assertEqual(
            config.config_file, "tests/unit/config_files/configparser.json"
        )
        self.assertEqual(config.config_type, ConfigTypes.JSON)
        self.assertFalse(config.autosave)
        self.assertFalse(config.autoreload)
        self.assertEqual(config.config_data, {"key": "value"})

    def test_auto_save_config(self):
        """Test auto save config."""
        # make the mock file
        with open("tests/unit/config_files/config_auto_save.json", "w") as f:
            f.write('{"key": "value"}')
        config = Configparser(
            "tests/unit/config_files/config_auto_save.json", autosave=True
        )
        self.assertEqual(
            config.config_file, "tests/unit/config_files/config_auto_save.json"
        )
        self.assertEqual(config.config_type, ConfigTypes.JSON)
        self.assertTrue(config.autosave)
        self.assertFalse(config.autoreload)
        self.assertEqual(config.config_data, {"key": "value"})

        # Test autosave
        self.assertEqual(config._old_config_data, {"key": "value"})
        config.config_data = {"key": "value2"}
        # sleep for 2 second
        import time

        time.sleep(2)
        self.assertEqual(config._old_config_data, {"key": "value2"})
        self.assertEqual(config.config_data, {"key": "value2"})
        # check if the file is updated
        with open("tests/unit/config_files/config_auto_save.json", "r") as f:
            written_data = f.read()
        import json

        self.assertEqual(json.loads(written_data), {"key": "value2"})

    def test_auto_reload_config(self):
        """Test auto reload config."""
        # make the mock file
        with open("tests/unit/config_files/config_auto_reload.json", "w") as f:
            f.write('{"key": "value"}')
        config = Configparser(
            "tests/unit/config_files/config_auto_reload.json", autoreload=True
        )
        self.assertEqual(
            config.config_file,
            "tests/unit/config_files/config_auto_reload.json",
        )
        self.assertEqual(config.config_type, ConfigTypes.JSON)
        self.assertFalse(config.autosave)
        self.assertTrue(config.autoreload)
        self.assertEqual(config.config_data, {"key": "value"})

        # Test autoreload
        with open("tests/unit/config_files/config_auto_reload.json", "w") as f:
            f.write('{"key": "value2"}')
        # sleep for 2 second
        import time

        time.sleep(2)
        self.assertEqual(config.config_data, {"key": "value2"})

    def test_get_item(self):
        """Test get item."""
        config = Configparser("tests/unit/config_files/configparser.json")
        self.assertEqual(config["key"], "value")
        self.assertEqual(config.config_data, {"key": "value"})

    def test_set_item(self):
        """Test set item."""
        config = Configparser("tests/unit/config_files/configparser.json")
        config["key"] = "value2"
        self.assertEqual(config.config_data, {"key": "value2"})
        self.assertEqual(config["key"], "value2")
        self.assertEqual(config.config_data, {"key": "value2"})

    def test_del_item(self):
        """Test del item."""
        config = Configparser("tests/unit/config_files/configparser.json")
        del config["key"]
        self.assertEqual(config.config_data, {})
        # catch the exception
        with self.assertRaises(KeyError):
            _ = config["key"]
        self.assertEqual(config.config_data, {})
