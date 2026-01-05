"""
Chat API endpoints for user interactions.
"""

import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

from app.services.service_manager import get_service_manager
from app.models.data_models import SourceReference

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""
    question: str = Field(..., min_length=1, description="User's question (cannot be empty)")
    session_id: Optional[str] = None
    
    @field_validator('question')
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Question cannot be empty or whitespace only')
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response model."""
    answer: str
    sources: List[SourceReference]
    confidence_score: float
    processing_time_ms: int
    timestamp: datetime


@router.post("/chat", response_model=ChatResponse)
async def process_chat_query(request: ChatRequest):
    """
    Process user chat queries and return grounded responses.
    
    Args:
        request: ChatRequest containing the user's question
        
    Returns:
        ChatResponse with answer, sources, and metadata
        
    Raises:
        HTTPException: If chat processing fails
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing chat query: '{request.question[:100]}...'")
        
        # Get service manager
        service_manager = await get_service_manager()
        
        # Process the query through the complete pipeline
        query_response = await service_manager.process_chat_query(request.question)
        
        # Convert to API response format
        response = ChatResponse(
            answer=query_response.answer,
            sources=query_response.sources,
            confidence_score=query_response.confidence_score,
            processing_time_ms=query_response.processing_time_ms,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Chat query processed successfully in {query_response.processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Chat query processing failed after {processing_time_ms}ms: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat query: {str(e)}"
        )


@router.get("/debug/service-status")
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


@router.get("/predefined/where-to-start", response_model=ChatResponse)
async def where_to_start():
    """
    Predefined query: "Where do I start?"
    Provides codebase overview and entry points for new developers.
    
    Returns:
        ChatResponse with codebase overview and getting started guidance
        
    Raises:
        HTTPException: If predefined query processing fails
    """
    start_time = time.time()
    
    try:
        logger.info("=== Processing 'Where do I start?' predefined query ===")
        
        # Get service manager
        logger.info("Getting service manager...")
        service_manager = await get_service_manager()
        logger.info(f"Service manager obtained, initialized: {service_manager._initialized}")
        
        # Process the predefined query
        logger.info("Calling service manager to process predefined query...")
        query_response = await service_manager.process_predefined_query("where-to-start")
        
        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Convert to API response format
        response = ChatResponse(
            answer=query_response.answer,
            sources=query_response.sources,
            confidence_score=query_response.confidence_score,
            processing_time_ms=processing_time_ms,
            timestamp=datetime.utcnow()
        )
        
        logger.info(f"Predefined query processed successfully in {processing_time_ms}ms")
        return response
        
    except Exception as e:
        processing_time_ms = int((time.time() - start_time) * 1000)
        logger.error(f"Predefined query processing failed after {processing_time_ms}ms: {str(e)}")
        
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process predefined query: {str(e)}"
        )