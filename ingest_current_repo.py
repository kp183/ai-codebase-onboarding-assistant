#!/usr/bin/env python3
"""
Script to ingest the current repository for demo testing.
"""

import asyncio
import httpx
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_repository():
    """Ingest the current repository."""
    
    # Create a fake GitHub URL for the current directory
    # The ingestion service should handle local paths
    current_path = Path.cwd()
    
    # Use a GitHub-like URL format that the service can handle
    repo_url = f"https://github.com/demo/ai-codebase-onboarding"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            logger.info(f"Starting repository ingestion...")
            
            response = await client.post(
                "http://127.0.0.1:8001/api/ingest",
                json={"repository_url": repo_url}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Ingestion successful!")
                logger.info(f"   Files processed: {result.get('files_processed', 'N/A')}")
                logger.info(f"   Chunks created: {result.get('chunks_created', 'N/A')}")
                logger.info(f"   Message: {result.get('message', 'N/A')}")
                return True
            else:
                logger.error(f"❌ Ingestion failed with status {response.status_code}")
                logger.error(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ingestion failed with error: {str(e)}")
            return False

if __name__ == "__main__":
    success = asyncio.run(ingest_repository())
    if success:
        print("\n🎉 Repository ingested successfully! You can now test the chat functionality.")
    else:
        print("\n❌ Repository ingestion failed. Please check the logs above.")