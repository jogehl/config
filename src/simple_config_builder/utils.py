"""Utility helpers for discovering and importing Configclass modules."""


def import_modules_from_directory(directory: str):
    """Recursively import all Python files in ``directory`` that contain Configclass subclasses.

    Walking the directory tree, this function imports any ``.py`` file
    (excluding ``__init__.py``) whose source contains the string
    ``"Configclass"``.  Importing the module causes every
    :class:`~simple_config_builder.config.Configclass` subclass defined in
    that file to be registered in
    :class:`~simple_config_builder.config.ConfigClassRegistry`.

    Parameters
    ----------
    directory:
        Absolute or relative path to the directory to scan.

    Raises
    ------
    ImportError
        If a matching file cannot be loaded (syntax error, missing
        dependency, etc.).

    Note
    ----
    This function has a side effect: it registers all discovered
    :class:`~simple_config_builder.config.Configclass` subclasses globally.
    Call it once at application startup before any config parsing.
    """
    # Iterate over all files and subdirectories in the given directory
    import os
    import importlib.util

    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            # Check if the file is a Python file
            if filename.endswith(".py") and filename != "__init__.py":
                # Get the module name (without .py extension)
                module_name = filename[:-3]

                # Create the full module path
                module_path = os.path.join(dirpath, filename)

                with open(module_path, "r") as file:
                    content = file.read()
                    if "Configclass" in content:
                        # Dynamically import the module
                        try:
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
                            spec.loader.exec_module(module)
                        except Exception as e:
                            raise ImportError(
                                f"Error while importing "
                                f"module {module_name}: {e}"
                            )
