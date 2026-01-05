"""
FastAPI main application entry point for AI Codebase Onboarding Assistant.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.config import settings
from app.api import chat, health, ingestion
from app.services.service_manager import service_manager

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting AI Codebase Onboarding Assistant...")
    
    try:
        # Initialize all services
        initialization_success = await service_manager.initialize_services()
        
        if initialization_success:
            logger.info("All services initialized successfully")
        else:
            logger.warning("Some services failed to initialize - application may have limited functionality")
        
        # Application is ready
        logger.info("Application startup completed")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        # Continue startup even if some services fail - allows for graceful degradation
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Codebase Onboarding Assistant...")
    
    try:
        await service_manager.shutdown_services()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during application shutdown: {str(e)}")


# Create FastAPI application instance with lifespan management
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered assistant to help developers understand codebases",
    debug=settings.debug,
    lifespan=lifespan
)

# Configure CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(chat.router, prefix="/api", tags=["chat"])
app.include_router(ingestion.router, prefix="/api", tags=["ingestion"])

# Mount static files for web UI
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web UI."""
    try:
        with open("static/index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h1>AI Codebase Onboarding Assistant</h1><p>Web UI not found. Please ensure static files are available.</p>",
            status_code=200
        )


@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "detailed_health": "/api/health/detailed",
            "system_stats": "/api/health/stats",
            "chat": "/api/chat",
            "predefined_query": "/api/predefined/where-to-start",
            "ingest_repository": "/api/ingest",
            "supported_extensions": "/api/supported-extensions"
        },
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )