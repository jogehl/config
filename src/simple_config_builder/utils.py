"""Utils for the config module."""


def import_modules_from_directory(directory: str):
    """
    Import and check fo @configclass decorator in the given directory.

    Params:
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
                    if (
                        "@configclass" in content
                        or "from config.config import configclass" in content
                        or "import config.config" in content
                    ):
                        # Dynamically import the module
                        try:
                            spec = importlib.util.spec_from_file_location(
                                module_name, module_path
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                        except Exception as e:
                            raise ImportError(
                                f"Error while importing "
                                f"module {module_name}: {e}"
                            )
