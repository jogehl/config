"""API routes for the GUI backend."""

import uuid
from fastapi import APIRouter, Request
from fastapi import FastAPI
from fastapi import Response
from fastapi.responses import FileResponse

from simple_config_builder.__about__ import __version__
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.configparser import Configparser
from simple_config_builder.gui_backend.session_data import SessionData

app = FastAPI()
api_router_v1 = APIRouter(prefix="/api/v1")

session_data = SessionData()


@app.middleware("http")
async def check_for_session_data(request, call_next):
    """Middleware to check for session data."""
    # get the cookied session key
    session_key = request.cookies.get("session_key")
    # log the session_key to the console
    if session_key is not None:
        request.state.session_key = session_key
        session_data[session_key] = {}
    else:
        # redirect to /session if no session key is found
        if request.url.path != "/api/v1/session":
            return Response(
                status_code=302, headers={"Location": "/api/v1/session"}
            )
    response = await call_next(request)
    return response


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """Return the favicon."""
    return FileResponse("src/simple_config_builder/gui_backend/favicon.ico")


# define the API routes here
@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to the GUI backend API!"}


@api_router_v1.get("/version")
async def version():
    """Retrieve the current version of the application."""
    return {"version": __version__}


@api_router_v1.get("/session")
async def new_session_data(response: Response):
    """Create a new session and set a session cookie."""
    session_key = str(uuid.uuid4())
    session_data[session_key] = {}
    response.set_cookie("session_key", session_key)
    return {"session_key": session_key}


# post request which gets the path to the configuration file
@api_router_v1.post("/load-config")
async def load_config(config_path: str, request: Request):
    """Load the configuration from the given path."""
    try:
        config = Configparser(config_path, autoreload=True)
    except ValueError as e:
        return {"error": str(e)}
    session_data[request.state.session_key]["config"] = config
    return {"config": config}


@api_router_v1.get("/get-config-classes")
async def get_config_classes(request: Request):
    """Retrieve the list of configuration classes."""
    classes = ConfigClassRegistry.list_classes()
    return {"classes": classes}


app.include_router(api_router_v1)
