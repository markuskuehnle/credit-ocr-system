"""
Application configuration objects for database and Azure storage settings.
"""

from dataclasses import dataclass


@dataclass
class DatabaseConfig:
    """Database configuration for the DMS mock."""
    host: str = "localhost"
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
    storage: AzureStorageConfig = AzureStorageConfig()


@dataclass
class AppConfig:
    """Top-level application configuration container."""
    database: DatabaseConfig = DatabaseConfig()
    azure: AzureConfig = AzureConfig()


