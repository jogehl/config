"""GUI backend configuration module."""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from simple_config_builder.api.routes import api_router_v1
from simple_config_builder.configparser import Configparser


def make_api(config_file_path: str) -> FastAPI:
    """Create and return the FastAPI app instance."""
    config_parser = Configparser(
        config_file_path,
        autosave=True,
    )
    from fastapi import FastAPI
    app = FastAPI()
    app.state.config_parser = config_parser
    app.include_router(api_router_v1)

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Return the favicon."""
        return FileResponse("src/simple_config_builder/api/favicon.ico")

    return app
