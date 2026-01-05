#!/usr/bin/env python3
"""
Script to ingest the current local repository for demo testing.
This bypasses the GitHub URL validation and directly processes local files.
"""

import asyncio
import logging
from pathlib import Path
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.service_manager import get_service_manager
from app.models.data_models import IngestionResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def ingest_local_repository():
    """Ingest the current local repository directly."""
    
    try:
        # Get the current directory
        current_path = Path.cwd()
        logger.info(f"Processing local repository: {current_path}")
        
        # Get service manager and ensure it's initialized
        service_manager = await get_service_manager()
        
        if not service_manager._initialized:
            logger.info("Service manager not initialized, initializing now...")
            success = await service_manager.initialize_services()
            if not success:
                logger.error("Failed to initialize services")
                return False
        
        # Import repository service directly
        from app.services.repository_ingestion import repository_service
        
        # Extract code files from current directory
        logger.info("Extracting code files...")
        code_files = await repository_service.fetch_code_files(str(current_path))
        
        if not code_files:
            logger.warning("No supported code files found in the current directory")
            return False
        
        logger.info(f"Found {len(code_files)} code files")
        
        # Process files through chunking service
        logger.info("Processing files through chunking service...")
        from app.services.code_chunking import chunking_service
        all_chunks = []
        
        for code_file in code_files:
            try:
                chunks = chunking_service.chunk_code_file(code_file)
                all_chunks.extend(chunks)
                logger.info(f"  {code_file.file_path}: {len(chunks)} chunks")
            except Exception as e:
                logger.warning(f"  Failed to chunk {code_file.file_path}: {e}")
        
        if not all_chunks:
            logger.warning("No chunks created from code files")
            return False
        
        logger.info(f"Created {len(all_chunks)} total chunks")
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embedding_service = service_manager.embedding_service
        embedded_chunks = await embedding_service.generate_embeddings(all_chunks)
        
        if not embedded_chunks:
            logger.warning("No embeddings generated")
            return False
        
        logger.info(f"Generated {len(embedded_chunks)} embeddings")
        
        # Store in search index
        logger.info("Storing in search index...")
        search_service = service_manager.search_service
        
        # Ensure index exists
        if not search_service.index_exists():
            search_service.create_index()
        
        # Store embeddings
        success = search_service.store_embeddings(embedded_chunks)
        
        if success:
            logger.info("✅ Successfully stored embeddings in search index")
            logger.info(f"📊 Summary:")
            logger.info(f"   Files processed: {len(code_files)}")
            logger.info(f"   Chunks created: {len(all_chunks)}")
            logger.info(f"   Embeddings stored: {len(embedded_chunks)}")
            return True
        else:
            logger.error("❌ Failed to store embeddings in search index")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error during local repository ingestion: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(ingest_local_repository())
    if success:
        print("\n🎉 Local repository ingested successfully!")
        print("   You can now test the chat functionality with 'Where do I start?' and custom questions.")
    else:
        print("\n❌ Local repository ingestion failed. Please check the logs above.")
        sys.exit(1)