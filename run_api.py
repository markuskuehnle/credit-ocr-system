#!/usr/bin/env python3
"""
Entry point script for running the Credit OCR System API.
"""

import os
import sys
import logging
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import uvicorn
from src.api.config import ApiConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run the FastAPI application."""
    # Load API configuration
    config = ApiConfig()
    
    logger.info("Starting Credit OCR System API")
    logger.info(f"Configuration: {config.to_dict()}")
    
    # Check environment variables
    required_env_vars = []
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        sys.exit(1)
    
    # Run the application
    uvicorn.run(
        "src.api.main:app",
        host=config.host,
        port=config.port,
        reload=config.reload and not config.is_production,
        log_level="info" if not config.debug else "debug",
        access_log=True,
    )


if __name__ == "__main__":
    main()
