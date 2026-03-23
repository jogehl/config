"""Utils for the config module."""

from __future__ import annotations

import tokenize
import warnings


IGNORED_DIRECTORY_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "env",
    "node_modules",
    "site-packages",
    "venv",
}


def import_modules_from_directory(directory: str):
    """
    Import and check fo Configclass subclasses in the given directory.

    Parameters
    ----------
    directory: str
    """
    # Iterate over all files and subdirectories in the given directory
    import sys
    import os
    import importlib.util

    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIRECTORY_NAMES
        ]
        for filename in filenames:
            # Check if the file is a Python file
            if filename.endswith(".py") and filename != "__init__.py":
                # Get the module name (without .py extension)
                module_name = filename[:-3]

                # Create the full module path
                module_path = os.path.join(dirpath, filename)

                try:
                    with tokenize.open(module_path) as file:
                        content = file.read()
                except (SyntaxError, UnicodeDecodeError) as e:
                    warnings.warn(
                        f"Skipping module {module_name}: unreadable source: {e}",
                        stacklevel=2,
                    )
                    continue

                if "Configclass" in content:
                    # Dynamically import the module
                    try:
                        # Use a path-based name to avoid shadowing stdlib or
                        # already-loaded modules with the same bare filename.
                        if (
                            module_name in sys.stdlib_module_names
                            or module_name in sys.modules
                        ):
                            rel_path = os.path.relpath(module_path, directory)
                            module_name = (
                                rel_path[:-3]
                                .replace(os.sep, ".")
                                .replace("/", ".")
                            )
                        spec = importlib.util.spec_from_file_location(
                            module_name, module_path
                        )
                        if spec is None:
                            raise ImportError(
                                f"Error while importing "
                                f"module {module_name}: "
                                f"spec is None"
                            )
                        module = importlib.util.module_from_spec(spec)
                        if spec.loader is None:
                            raise ImportError(
                                f"Error while importing "
                                f"module {module_name}: "
                                f"loader is None"
                            )
                        sys.modules[module_name] = module
                        spec.loader.exec_module(module)
                    except ModuleNotFoundError as e:
                        sys.modules.pop(module_name, None)
                        warnings.warn(
                            f"Skipping module {module_name}: missing "
                            f"dependency {e.name!r}",
                            stacklevel=2,
                        )
                        continue
                    except Exception as e:
                        sys.modules.pop(module_name, None)
                        raise ImportError(
                            f"Error while importing "
                            f"module {module_name}: {e}"
                        )
