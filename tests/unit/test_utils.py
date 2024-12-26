"""Tests for the utils module."""

from unittest import TestCase

from config.utils import import_modules_from_directory
from config.config import ConfigClassRegistry


class UtilsTest(TestCase):
    """Test the utils module."""

    def test_import_modules_from_directory(self):
        """Test the import_modules_from_directory function."""
        # get current directory
        import os

        current_directory = os.path.dirname(os.path.realpath(__file__))
        current_directory = os.path.join(
            current_directory, "import_modules_test_classes"
        )
        import_modules_from_directory(current_directory)

        self.assertIn("example.Example", ConfigClassRegistry.list_classes())
        self.assertIn("example.Example2", ConfigClassRegistry.list_classes())