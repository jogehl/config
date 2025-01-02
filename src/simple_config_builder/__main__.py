"""File to run the config module as a script."""

import sys

if __name__ == "__main__":
    from simple_config_builder.cli import config

    sys.exit(config())
