"""
Application configuration objects for database, Redis, and Azure storage settings.
"""

import os
from dataclasses import dataclass, field


@dataclass
class DatabaseConfig:
    """Database configuration for the DMS mock."""
    host: str = "postgres"
    port: int = 5432
    name: str = "dms_meta"
    user: str = "dms"
    password: str = "dms"


@dataclass
class AzureStorageConfig:
    """Azure storage configuration for Azurite emulation."""
    account_name: str = "devstoreaccount1"
    # Default Azurite key
    account_key: str = (
        "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/"
        "K1SZFPTOtr/KBHBeksoGMGw=="
    )
    container_name: str = "documents"


@dataclass
class AzureConfig:
    """Azure configuration grouping for storage."""
    storage: AzureStorageConfig = field(default_factory=AzureStorageConfig)


@dataclass
class RedisConfig:
    """Redis configuration for Celery broker and result backend."""
    host: str = "redis"
    port: int = 6379
    db: int = 0
    broker_url: str = "redis://redis:6379/0"
    result_backend: str = "redis://redis:6379/0"
    task_serializer: str = "json"
    accept_content: list = field(default_factory=lambda: ["json"]) 
    result_serializer: str = "json"
    timezone: str = "UTC"
    enable_utc: bool = True


@dataclass
class AppConfig:
    """Top-level application configuration container."""
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    azure: AzureConfig = field(default_factory=AzureConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)

    def __post_init__(self) -> None:
        """Load environment-aware defaults for local vs Docker execution."""
        is_in_docker: bool = bool(
            os.environ.get("IN_DOCKER", "").strip() == "1" or os.path.exists("/.dockerenv")
        )

        # Allow explicit overrides first
        database_host_env: str = os.environ.get("DATABASE_HOST", "")
        redis_host_env: str = os.environ.get("REDIS_HOST", "")

        # Fallback based on environment
        default_db_host: str = "postgres" if is_in_docker else "localhost"
        default_redis_host: str = "redis" if is_in_docker else "localhost"

        # Apply resolved hosts
        self.database.host = database_host_env or default_db_host
        self.redis.host = redis_host_env or default_redis_host

        # Rebuild Redis URLs from host/port/db so they stay consistent
        self.redis.broker_url = f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"
        self.redis.result_backend = f"redis://{self.redis.host}:{self.redis.port}/{self.redis.db}"


