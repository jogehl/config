"""Module contains the main entry point for the config CLI."""

import click

from simple_config_builder.__about__ import __version__
from simple_config_builder.config import ConfigClassRegistry
from simple_config_builder.utils import import_modules_from_directory


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    invoke_without_command=True,
)
@click.version_option(version=__version__)
def config():
    """Run the main entry point for the config CLI."""
    click.echo("Hello to the config CLI!")


@config.command()
@click.option(
    "--host",
    "-h",
    default="localhost",
    help="The host to run the GUI backend server on.",
)
@click.option(
    "--port",
    "-p",
    default=8000,
    help="The port to run the GUI backend server on.",
)
@click.option(
    "--directory",
    "-d",
    default=".",
    help="The directory to search for configclasses.",
)
def start(host, port, directory):
    """Start the config CLI."""
    click.echo(
        "Registering all configclasses in current directory and subfolders..."
    )
    # Register all configclasses in the current directory and subfolders
    # iterate over all files in the current directory and subfolders
    # and import them to register the configclasses
    click.echo("Starting the config CLI-GUI...")
    import_modules_from_directory(directory)

    click.echo(
        f"These are the registered configclasses: "
        f"{ConfigClassRegistry.list_classes()}"
    )

    # Start the GUI backend server here
    import uvicorn
    from simple_config.gui_backend.api import app

    uvicorn.run(app, host=host, port=port)
