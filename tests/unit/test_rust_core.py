"""Tests for the Rust-backed standalone config API."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from simple_config_builder import rust_core


class TestRustCore(TestCase):
    """Validate the pure Rust config core through the Python bindings."""

    def test_schema_contains_expected_fields(self):
        """Schema contains expected top-level field names."""
        schema = rust_core.schema()

        self.assertEqual(schema["type"], "object")
        self.assertIn("port", schema["properties"])
        self.assertIn("name", schema["properties"])

    def test_validate_rejects_invalid_port(self):
        """Validation raises ValueError for an out-of-range port."""
        with self.assertRaises(ValueError):
            rust_core.validate(
                {
                    "name": "demo",
                    "host": "127.0.0.1",
                    "port": 0,
                    "enabled": True,
                    "profile": "dev",
                }
            )

    def test_defaults_can_be_overridden_and_written(self):
        """apply_defaults merges overrides and round-trips to YAML."""
        merged = rust_core.apply_defaults({"profile": "prod", "port": 9000})

        self.assertEqual(merged["profile"], "prod")
        self.assertEqual(merged["port"], 9000)

        with TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "standalone.yaml"
            rust_core.write(str(config_path), merged, "yaml")
            loaded = rust_core.load(str(config_path), "yaml")

        self.assertEqual(loaded, merged)
