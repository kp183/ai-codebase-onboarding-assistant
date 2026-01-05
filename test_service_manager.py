#!/usr/bin/env python3
"""
Test script to directly test the service manager functionality.
"""

import asyncio
import logging
from app.services.service_manager import get_service_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_service_manager():
    """Test the service manager directly."""
    try:
        logger.info("=== Testing Service Manager Directly ===")
        
        # Get service manager
        logger.info("Getting service manager...")
        service_manager = await get_service_manager()
        logger.info(f"Service manager obtained, initialized: {service_manager._initialized}")
        
        # Test predefined query
        logger.info("Testing predefined query...")
        response = await service_manager.process_predefined_query("where-to-start")
        
        logger.info(f"Success! Response length: {len(response.answer)} characters")
        logger.info(f"Response preview: {response.answer[:200]}...")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_service_manager())
    if success:
        print("✅ Service manager test PASSED")
    else:
        print("❌ Service manager test FAILED")