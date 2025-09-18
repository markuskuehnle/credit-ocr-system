import os
from typing import Dict, Any


class ApiConfig:
    """Configuration for the FastAPI application."""
    
    def __init__(self):
        self.host: str = os.getenv("API_HOST", "0.0.0.0")
        self.port: int = int(os.getenv("API_PORT", "8000"))
        self.debug: bool = os.getenv("API_DEBUG", "false").lower() == "true"
        self.reload: bool = os.getenv("API_RELOAD", "true").lower() == "true"
        
        # CORS settings
        self.cors_origins: list = self._parse_cors_origins()
        
        # File upload limits
        self.max_file_size: int = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # MB to bytes
        self.allowed_file_types: list = [".pdf"]
        
        # Background task settings
        self.enable_background_processing: bool = os.getenv("ENABLE_BACKGROUND_PROCESSING", "true").lower() == "true"
    
    def _parse_cors_origins(self) -> list:
        """Parse CORS origins from environment variable."""
        origins_str = os.getenv("CORS_ORIGINS", "*")
        if origins_str == "*":
            return ["*"]
        return [origin.strip() for origin in origins_str.split(",") if origin.strip()]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary for logging."""
        return {
            "host": self.host,
            "port": self.port,
            "debug": self.debug,
            "reload": self.reload,
            "cors_origins": self.cors_origins,
            "max_file_size_mb": self.max_file_size // (1024 * 1024),
            "allowed_file_types": self.allowed_file_types,
            "enable_background_processing": self.enable_background_processing,
            "is_production": self.is_production,
        }
