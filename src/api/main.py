"""
Main FastAPI application for credit OCR system.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .routes import router
from .models import ErrorResponse
from .config import ApiConfig
from ..storage.storage import get_storage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Credit OCR System API")
    
    # Initialize storage containers
    try:
        storage_client = get_storage()
        storage_client.ensure_all_containers_ready()
        logger.info("Storage containers initialized")
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Credit OCR System API")


# Load configuration
api_config = ApiConfig()

# Create FastAPI application
app = FastAPI(
    title="Credit OCR System API",
    description="API for processing credit documents with OCR and LLM extraction",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    debug=api_config.debug
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["documents"])

# Setup templates for simple frontend
templates = Jinja2Templates(directory="src/api/templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main upload page."""
    return templates.TemplateResponse(request, "index.html")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "detail": f"Path: {request.url.path}"
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc):
    """Handle 500 errors."""
    from fastapi.responses import JSONResponse
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error", 
            "message": "An internal server error occurred",
            "detail": str(exc) if api_config.debug else None
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
