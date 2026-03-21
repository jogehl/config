"""API routes for the GUI backend."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

from simple_config_builder.__about__ import __version__
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.config_io import to_dict, write_config
from simple_config_builder.config_types import ConfigTypes
from simple_config_builder.configparser import Configparser
from simple_config_builder.gui_backend.schema import normalize_json_schema

app = Flask(__name__)

_modules_registered = False


@app.before_request
def _ensure_modules_registered():
    """Re-register configclasses after a Flask debug reload."""
    global _modules_registered  # noqa: PLW0603
    if _modules_registered:
        return
    _modules_registered = True
    config_dir = os.environ.get("SCB_CONFIG_DIR")
    if config_dir and not ConfigClassRegistry.list_classes():
        from simple_config_builder.utils import import_modules_from_directory

        import_modules_from_directory(config_dir)
CORS(app)

CONFIG_EXTENSIONS = {".json", ".yaml", ".yml", ".toml"}


def _error(status: int, detail: str):
    """Return a JSON error response matching the FastAPI format."""
    return jsonify({"detail": detail}), status


def _file_digest(path: Path) -> str:
    """Return SHA256 digest for file contents."""
    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        hasher.update(file_obj.read())
    return hasher.hexdigest()


def _file_metadata(path: Path) -> dict[str, Any]:
    """Return existence, mtime and hash metadata for a file."""
    exists = path.exists()
    return {
        "exists": exists,
        "mtime_ns": path.stat().st_mtime_ns if exists else None,
        "sha256": _file_digest(path) if exists else None,
    }


# ── Static ─────────────────────────────────────────────────────────


@app.get("/favicon.ico")
def favicon():
    """Return the favicon."""
    ico = Path(__file__).parent / "favicon.ico"
    if ico.exists():
        return send_file(ico, mimetype="image/x-icon")
    return "", 204


@app.get("/")
def root():
    """Root endpoint that returns a welcome message."""
    return jsonify({"message": "Welcome to the GUI backend API!"})


# ── Info ───────────────────────────────────────────────────────────


@app.get("/api/v1/version")
def version():
    """Retrieve the current version of the application."""
    return jsonify({"version": __version__})


@app.get("/api/v1/formats")
def formats():
    """List supported output/input config formats."""
    return jsonify({"formats": [fmt.value for fmt in ConfigTypes]})


# ── Config IO ──────────────────────────────────────────────────────


@app.post("/api/v1/load-config")
def load_config():
    """Load the configuration from the given path."""
    body = request.get_json(silent=True) or {}
    config_path = body.get("config_path")
    autoreload = body.get("autoreload", False)
    if not config_path:
        return _error(400, "config_path is required")

    try:
        config = Configparser(config_path, autoreload=autoreload)
        config_data = config.config_data
    except ValueError as exc:
        return _error(400, str(exc))
    except ImportError as exc:
        return _error(422, str(exc))
    except FileNotFoundError as exc:
        return _error(404, str(exc))
    except Exception as exc:
        return _error(500, f"Failed to load config: {exc}")

    path = Path(config_path)
    return jsonify({"config": to_dict(config_data), "metadata": _file_metadata(path)})


@app.post("/api/v1/config-metadata")
def config_metadata():
    """Get file metadata for multi-user change detection in UIs."""
    body = request.get_json(silent=True) or {}
    config_path = body.get("config_path")
    if not config_path:
        return _error(400, "config_path is required")
    return jsonify(_file_metadata(Path(config_path)))


# ── Config classes ─────────────────────────────────────────────────


@app.get("/api/v1/get-config-classes")
def get_config_classes():
    """Retrieve the list of configuration classes."""
    return jsonify({"classes": ConfigClassRegistry.list_classes()})


@app.get("/api/v1/get-config-class/<path:class_name>")
def get_config_class(class_name: str):
    """Retrieve a specific configuration class by name."""
    try:
        config_class = ConfigClassRegistry.get(class_name)
    except ValueError as exc:
        return _error(404, str(exc))
    schema = config_class.model_json_schema()
    return jsonify({
        "schema": schema,
        "normalized_schema": normalize_json_schema(schema),
    })


@app.post("/api/v1/validate-config")
def validate_config():
    """Validate a JSON payload against the selected config class."""
    body = request.get_json(silent=True) or {}
    class_name = body.get("class_name")
    data = body.get("data")
    if not class_name or data is None:
        return _error(400, "class_name and data are required")

    try:
        config_class = ConfigClassRegistry.get(class_name)
        validated = config_class.model_validate(data)
    except ValueError as exc:
        return _error(422, str(exc))
    except Exception as exc:
        return _error(422, str(exc))

    return jsonify({"valid": True, "normalized": validated.model_dump()})


@app.post("/api/v1/save-config")
def save_config():
    """Persist a given config payload to disk."""
    body = request.get_json(silent=True) or {}
    config_path = body.get("config_path")
    config_type_str = body.get("config_type")
    data = body.get("data")
    if not config_path or not config_type_str or data is None:
        return _error(400, "config_path, config_type, and data are required")

    try:
        config_type = ConfigTypes(config_type_str)
    except ValueError:
        return _error(400, f"Unsupported config type: {config_type_str}")

    try:
        write_config(config_path, data, config_type)
    except Exception as exc:
        return _error(500, f"Failed to save config: {exc}")

    path = Path(config_path)
    return jsonify({
        "saved": True,
        "path": config_path,
        "type": config_type.value,
        **_file_metadata(path),
    })


# ── File browser ───────────────────────────────────────────────────


@app.get("/api/v1/browse")
def browse():
    """List files and subdirectories for a server-side file browser."""
    directory = request.args.get("directory", ".")
    base = Path(directory).resolve()
    if not base.exists() or not base.is_dir():
        return _error(400, f"Not a directory: {directory}")

    entries: list[dict[str, str]] = []
    try:
        for child in sorted(
            base.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
        ):
            if child.name.startswith("."):
                continue
            if child.is_dir():
                entries.append({"name": child.name, "type": "directory"})
            elif child.suffix.lower() in CONFIG_EXTENSIONS:
                entries.append({"name": child.name, "type": "file"})
    except PermissionError as exc:
        return _error(403, str(exc))

    return jsonify({
        "path": str(base),
        "parent": str(base.parent) if base.parent != base else None,
        "entries": entries,
    })
