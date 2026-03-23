"""Demo config classes for the Simple Config Builder GUI."""

from collections.abc import Callable
from typing import Literal

from simple_config_builder import Configclass, Field


class DatabaseConfig(Configclass):
    """Database connection settings."""

    host: str = Field(default="localhost", min_length=1, max_length=255)
    port: int = Field(default=5432, gt=0, lt=65536)
    name: str = Field(default="mydb", min_length=1, max_length=128)
    user: str = Field(default="admin", min_length=1)
    max_connections: int = Field(default=10, gt=0, le=1000)
    connection_timeout: float = Field(default=5.0, gt=0, le=300)


class LoggingConfig(Configclass):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    output_path: str = Field(default="/var/log/app.log", min_length=1)
    max_file_size_mb: float = Field(default=50.0, gt=0, le=10000)
    backup_count: int = Field(default=5, ge=0, le=100)
    formatter: Callable = print


class CacheConfig(Configclass):
    """Cache layer settings."""

    enabled: bool = Field(default=True)
    backend: Literal["redis", "memcached", "local"] = Field(default="local")
    ttl_seconds: int = Field(default=3600, ge=0, le=86400)
    max_entries: int = Field(default=10000, gt=0, le=1000000)


class ServerConfig(Configclass):
    """Top-level server configuration with nested sub-configs."""

    app_name: str = Field(default="MyApp", min_length=1, max_length=64)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    debug: bool = Field(default=False)
    workers: int = Field(default=4, gt=0, le=32)
    request_timeout: float = Field(default=30.0, gt=0, le=600)
    max_request_size_kb: int = Field(default=1024, gt=0, le=102400)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    health_check: Callable = print
    some_class: Configclass
