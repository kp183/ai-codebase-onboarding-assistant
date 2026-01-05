"""
Health check endpoints for system monitoring.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

from app.config import settings
from app.services.service_manager import get_service_manager

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    service: str


class DetailedHealthResponse(BaseModel):
    """Detailed health check response model."""
    status: str
    timestamp: datetime
    version: str
    service: str
    services: Dict[str, Any]
    initialized: bool


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Basic health check endpoint.
    Returns system status and basic information.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        service=settings.app_name
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """
    Detailed health check endpoint that verifies all services.
    
    Returns:
        Comprehensive health status including individual service checks
    """
    try:
        # Get service manager (this will initialize services if needed)
        service_manager = await get_service_manager()
        
        # Get detailed health status
        health_status = await service_manager.get_health_status()
        
        return DetailedHealthResponse(
            status=health_status["overall_status"],
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            service=settings.app_name,
            services=health_status.get("services", {}),
            initialized=health_status.get("initialized", False)
        )
        
    except Exception as e:
        return DetailedHealthResponse(
            status="error",
            timestamp=datetime.utcnow(),
            version=settings.app_version,
            service=settings.app_name,
            services={"error": str(e)},
            initialized=False
        )


@router.get("/health/debug")
async def debug_service_status():
    """Debug endpoint to check service manager status."""
    try:
        service_manager = await get_service_manager()
        return {
            "service_manager_id": id(service_manager),
            "initialized": service_manager._initialized,
            "services_healthy": service_manager._services_healthy,
            "last_health_check": service_manager._last_health_check.isoformat() if service_manager._last_health_check else None
        }
    except Exception as e:
        return {"error": str(e)}


@router.get("/health/stats")
async def system_stats():
    """
    Get system statistics and metrics.
    
    Returns:
        Dictionary containing system statistics and metrics
    """
    try:
        service_manager = await get_service_manager()
        return await service_manager.get_system_stats()
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }