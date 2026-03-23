from simple_config_builder import Configclass, Field

class TestConfigClass(Configclass):
    """A test configclass for testing purposes."""

    a: int = Field(default=1, description="An integer field.")
    b: str = Field(default="default_value", description="A string field.")