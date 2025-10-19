"""API routes for the GUI backend."""

import uuid
from fastapi import APIRouter, Request
from fastapi import FastAPI
from fastapi import Response
from fastapi.responses import FileResponse

from simple_config_builder.__about__ import __version__
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.configparser import Configparser

api_router_v1 = APIRouter(prefix="/api/v1")


@api_router_v1.get("/version")
async def version():
    """Retrieve the current version of the application."""
    return {"version": __version__}


@api_router_v1.get("/get-config-classes")
async def get_config_classes(request: Request):
    """Retrieve the list of configuration classes."""
    from simple_config_builder import Configclass
    from collections.abc import Callable

    class N(Configclass):
        func1: Callable

    classes = ConfigClassRegistry.list_classes()
    return {"classes": classes}


@api_router_v1.get("/get-config-class/{class_name}")
async def get_config_class(class_name: str, request: Request):
    """Retrieve a specific configuration class by name."""
    config_class = ConfigClassRegistry.get(class_name)
    schema = config_class.model_json_schema()
    # Store the class in session data
    return schema
