"""Module contains the main entry point for the config CLI."""
import click

from config.__about__ import __version__


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]}, 
    invoke_without_command=True)
@click.version_option(version=__version__)
def config():
    """Run the main entry point for the config CLI."""
    click.echo("Hello world!")
