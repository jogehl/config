"""API routes for the GUI backend."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from simple_config_builder.__about__ import __version__
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.config_io import write_config
from simple_config_builder.config_types import ConfigTypes
from simple_config_builder.configparser import Configparser
from simple_config_builder.gui_backend.schema import normalize_json_schema

app = FastAPI()
api_router_v1 = APIRouter(prefix="/api/v1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LoadConfigRequest(BaseModel):
    """Request body for loading a configuration."""

    config_path: str
    autoreload: bool = False


class ValidateConfigRequest(BaseModel):
    """Request body for validating config payloads."""

    class_name: str
    data: dict[str, Any]


class SaveConfigRequest(BaseModel):
    """Request body for persisting a config payload."""

    config_path: str
    config_type: ConfigTypes
    data: dict[str, Any] | list[Any]


class ConfigMetadataRequest(BaseModel):
    """Request body for config metadata lookup."""

    config_path: str


def _file_digest(path: Path) -> str:
    """Return SHA256 digest for file contents."""
    hasher = hashlib.sha256()
    with path.open("rb") as file_obj:
        hasher.update(file_obj.read())
    return hasher.hexdigest()


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return the favicon."""
    return FileResponse("src/simple_config_builder/gui_backend/favicon.ico")


@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to the GUI backend API!"}


@api_router_v1.get("/version")
async def version():
    """Retrieve the current version of the application."""
    return {"version": __version__}


@api_router_v1.get("/formats")
async def formats():
    """List supported output/input config formats."""
    return {"formats": [fmt.value for fmt in ConfigTypes]}


@api_router_v1.post("/load-config")
async def load_config(
    body: LoadConfigRequest | None = None, config_path: str | None = None
):
    """Load the configuration from the given path (body preferred)."""
    resolved_path = body.config_path if body is not None else config_path
    autoreload = body.autoreload if body is not None else False
    if resolved_path is None:
        raise HTTPException(status_code=400, detail="config_path is required")

    try:
        config = Configparser(resolved_path, autoreload=autoreload)
        config_data = config.config_data
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    path = Path(resolved_path)
    metadata = {
        "exists": path.exists(),
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": _file_digest(path) if path.exists() else None,
    }
    return {"config": config_data, "metadata": metadata}


@api_router_v1.post("/config-metadata")
async def config_metadata(body: ConfigMetadataRequest):
    """Get file metadata for multi-user change detection in UIs."""
    path = Path(body.config_path)
    return {
        "exists": path.exists(),
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": _file_digest(path) if path.exists() else None,
    }


@api_router_v1.get("/get-config-classes")
async def get_config_classes():
    """Retrieve the list of configuration classes."""
    classes = ConfigClassRegistry.list_classes()
    return {"classes": classes}


@api_router_v1.get("/get-config-class/{class_name}")
async def get_config_class(class_name: str):
    """Retrieve a specific configuration class by name."""
    config_class = ConfigClassRegistry.get(class_name)
    schema = config_class.model_json_schema()
    return {"schema": schema, "normalized_schema": normalize_json_schema(schema)}


@api_router_v1.post("/validate-config")
async def validate_config(body: ValidateConfigRequest):
    """Validate a JSON payload against the selected config class."""
    config_class = ConfigClassRegistry.get(body.class_name)
    validated = config_class.model_validate(body.data)
    return {"valid": True, "normalized": validated.model_dump()}


@api_router_v1.post("/save-config")
async def save_config(body: SaveConfigRequest):
    """Persist a given config payload to disk."""
    write_config(body.config_path, body.data, body.config_type)
    path = Path(body.config_path)
    return {
        "saved": True,
        "path": body.config_path,
        "type": body.config_type.value,
        "mtime_ns": path.stat().st_mtime_ns if path.exists() else None,
        "sha256": _file_digest(path) if path.exists() else None,
    }


app.include_router(api_router_v1)
