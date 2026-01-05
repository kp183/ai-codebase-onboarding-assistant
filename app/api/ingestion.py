"""
API endpoints for repository ingestion functionality.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
import logging

from app.services.service_manager import get_service_manager
from app.models.data_models import IngestionResult

logger = logging.getLogger(__name__)

router = APIRouter()


class IngestionRequest(BaseModel):
    """Request model for repository ingestion."""
    repository_url: HttpUrl


@router.post("/ingest", response_model=IngestionResult)
async def ingest_repository(request: IngestionRequest):
    """
    Ingest a GitHub repository and process its code files through the complete pipeline.
    
    This endpoint orchestrates the full pipeline:
    1. Repository ingestion and file extraction
    2. Code chunking into semantic segments
    3. Embedding generation using Azure OpenAI
    4. Storage in Azure AI Search index
    
    Args:
        request: IngestionRequest containing the repository URL
        
    Returns:
        IngestionResult with success status, file count, and processing details
        
    Raises:
        HTTPException: If ingestion pipeline fails
    """
    try:
        logger.info(f"Starting repository ingestion pipeline for: {request.repository_url}")
        
        # Get service manager
        service_manager = await get_service_manager()
        
        # Process through complete ingestion pipeline
        result = await service_manager.process_repository_ingestion(str(request.repository_url))
        
        if result.success:
            logger.info(f"Repository ingestion pipeline completed successfully: {result.message}")
        else:
            logger.warning(f"Repository ingestion pipeline failed: {result.message}")
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error during repository ingestion pipeline: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during repository ingestion pipeline"
        )


@router.get("/supported-extensions")
async def get_supported_extensions():
    """
    Get the list of supported file extensions for code processing.
    
    Returns:
        Dictionary containing supported file extensions and their languages
    """
    from app.services.repository_ingestion import repository_service
    
    return {
        "supported_extensions": list(repository_service.SUPPORTED_EXTENSIONS),
        "max_file_size_bytes": repository_service.MAX_FILE_SIZE,
        "description": "File extensions supported for code processing"
    }