"""
basic_configclass.py — Python Configclass API example.

Run with:
    hatch run python examples/python/basic_configclass.py
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from simple_config_builder import Configclass, Configparser, ConfigTypes, Field


# ── Define config classes ────────────────────────────────────────────────────

class DatabaseConfig(Configclass):
    host: str = "localhost"
    port: int = Field(gt=0, lt=65536, default=5432)
    max_connections: int = Field(gt=0, lt=257, default=10)


class AppConfig(Configclass):
    name: str = "my-app"
    environment: str = "dev"
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    debug: bool = False


# ── 1. Instantiate and inspect ───────────────────────────────────────────────

config = AppConfig()
print("Default config:")
print(json.dumps(config.model_dump(), indent=2))

# ── 2. Access and mutate fields ──────────────────────────────────────────────

config.name = "production-app"
config.environment = "prod"
config.database.port = 3306
print("\nMutated config:")
print(json.dumps(config.model_dump(), indent=2))

# ── 3. Validation error ───────────────────────────────────────────────────────

try:
    config.database.port = 99999  # exceeds lt=65536
except Exception as exc:
    print(f"\nCaught expected validation error: {exc}")

# ── 4. JSON Schema ────────────────────────────────────────────────────────────

schema = AppConfig.model_json_schema()
print("\nJSON Schema fields:", list(schema.get("properties", {}).keys()))

# ── 5. Serialize / deserialize via JSON string ───────────────────────────────

json_str = config.model_dump_json()
restored = AppConfig.model_validate_json(json_str)
assert restored.name == config.name
print(f"\nRound-trip via JSON OK (name={restored.name!r})")

# ── 6. Configparser — load and save a YAML file ───────────────────────────────

with tempfile.TemporaryDirectory() as tmpdir:
    cfg_path = Path(tmpdir) / "app.yaml"

    # Write the current config to disk.
    from simple_config_builder.config_io import write_config
    write_config(str(cfg_path), config, ConfigTypes.YAML)
    print(f"\nWrote config to {cfg_path}")

    # Parse it back using Configparser.
    parser = Configparser(str(cfg_path), ConfigTypes.YAML)
    loaded: AppConfig = parser.config_data  # type: ignore[assignment]
    print("Re-loaded via Configparser:")
    print(json.dumps(loaded.model_dump(), indent=2))
