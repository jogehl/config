"""Tests for the utils module."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import warnings

from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.utils import import_modules_from_directory


class UtilsTest(TestCase):
    """Test the utils module."""

    def test_import_modules_from_directory(self):
        """Test the import_modules_from_directory function."""
        import os

        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )
        import_modules_from_directory(current_directory)

        self.assertIn("example.Example", ConfigClassRegistry.list_classes())
        self.assertIn("example.Example2", ConfigClassRegistry.list_classes())

    def test_ignored_directories_are_not_imported(self):
        """Ignored dirs such as node_modules must not be imported."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good_module.py").write_text(
                "from simple_config_builder import Configclass\n"
                "class Good(Configclass):\n"
                "    value: int = 1\n"
            )
            (root / "node_modules").mkdir()
            (root / "node_modules" / "bad_module.py").write_text(
                "from simple_config_builder import Configclass\n"
                "class Bad(Configclass):\n"
                "    value: int = 1\n"
            )

            import_modules_from_directory(str(root))

            classes = ConfigClassRegistry.list_classes()
            self.assertIn("good_module.Good", classes)
            self.assertNotIn("bad_module.Bad", classes)

    def test_missing_dependency_warns_and_continues(self):
        """Missing imports in candidate modules should warn, not crash."""
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken_module.py").write_text(
                "import missing_dependency_for_test\n"
                "from simple_config_builder import Configclass\n"
                "class Broken(Configclass):\n"
                "    value: int = 1\n"
            )
            (root / "ok_module.py").write_text(
                "from simple_config_builder import Configclass\n"
                "class Ok(Configclass):\n"
                "    value: int = 1\n"
            )

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                import_modules_from_directory(str(root))

            warning_messages = [str(w.message) for w in caught]
            self.assertTrue(
                any("missing dependency" in msg for msg in warning_messages)
            )
            self.assertIn("ok_module.Ok", ConfigClassRegistry.list_classes())
