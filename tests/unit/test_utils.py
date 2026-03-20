"""Tests for the utils module."""

import os
import tokenize
import warnings
from unittest import TestCase
from unittest.mock import patch

from simple_config_builder.utils import import_modules_from_directory
from simple_config_builder.config import ConfigClassRegistry


class UtilsTest(TestCase):
    """Test the utils module."""

    def test_import_modules_from_directory(self):
        """Test the import_modules_from_directory function."""
        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )
        import_modules_from_directory(current_directory)

        self.assertIn("example.Example", ConfigClassRegistry.list_classes())
        self.assertIn("example.Example2", ConfigClassRegistry.list_classes())

    def test_import_module_with_dataclass(self):
        """Test dynamic import of modules that also declare dataclasses."""
        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )
        import_modules_from_directory(current_directory)

        self.assertIn(
            "dataclass_module.DataclassBackedConfig",
            ConfigClassRegistry.list_classes(),
        )

    def test_skip_module_with_missing_dependency(self):
        """Test discovery skips modules with missing dependencies."""
        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            import_modules_from_directory(current_directory)

        self.assertNotIn(
            "missing_dependency_module.MissingDependencyConfig",
            ConfigClassRegistry.list_classes(),
        )
        self.assertTrue(
            any(
                "Skipping module missing_dependency_module" in str(w.message)
                for w in caught_warnings
            )
        )

    def test_skip_module_with_unreadable_source(self):
        """Test discovery skips modules whose source cannot be decoded."""
        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )
        real_tokenize_open = tokenize.open

        def fake_tokenize_open(path):
            if path.endswith("unreadable_module.py"):
                raise UnicodeDecodeError("utf-8", b"\xa4", 0, 1, "invalid")
            return real_tokenize_open(path)

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            with patch("tokenize.open", side_effect=fake_tokenize_open):
                import_modules_from_directory(current_directory)

        self.assertNotIn(
            "unreadable_module.UnreadableConfig",
            ConfigClassRegistry.list_classes(),
        )
        self.assertTrue(
            any(
                "Skipping module unreadable_module: unreadable source"
                in str(w.message)
                for w in caught_warnings
            )
        )

    def test_skip_virtual_environment_directories(self):
        """Test discovery does not descend into environment directories."""
        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            import_modules_from_directory(current_directory)

        self.assertNotIn(
            ".venv.ignored_env_module.EnvOnlyConfig",
            ConfigClassRegistry.list_classes(),
        )
        self.assertFalse(
            any(
                "ignored_env_module" in str(w.message)
                for w in caught_warnings
            )
        )
