"""Utils for the config module."""


def import_modules_from_directory(directory: str):
    """
    Import and check fo Configclass subclasses in the given directory.

    Parameters
    ----------
    directory: str
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
