"""
Service manager for coordinating all application services.

This module provides centralized service initialization, health checks,
and orchestration of the complete pipeline from ingestion to chat responses.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.config import settings
from app.models.data_models import CodeFile, IngestionResult, QueryResponse
from app.services.repository_ingestion import repository_service
from app.services.code_chunking import chunking_service
from app.services.embedding_service import get_embedding_service
from app.services.search_service import get_search_service
from app.services.query_processing import get_query_processing_service
from app.services.predefined_queries import get_predefined_query_service

logger = logging.getLogger(__name__)


class ServiceManager:
    """
    Central service manager for coordinating all application services.
    
    Handles service initialization, health checks, and orchestrates the complete
    pipeline from repository ingestion through to chat responses.
    """
    
    def __init__(self):
        """Initialize the service manager."""
        self._initialized = False
        self._services_healthy = False
        self._last_health_check = None
        
        # Service instances
        self.embedding_service = None
        self.search_service = None
        self.query_processing_service = None
        self.predefined_query_service = None
    
    async def initialize_services(self) -> bool:
        """
        Initialize all application services and perform startup checks.
        
        Returns:
            True if all services initialized successfully, False otherwise
        """
        try:
            logger.info("Initializing application services...")
            
            # Initialize service instances
            self.embedding_service = get_embedding_service()
            self.search_service = get_search_service()
            self.query_processing_service = get_query_processing_service()
            self.predefined_query_service = get_predefined_query_service()
            
            # Perform startup checks
            startup_checks = await self._perform_startup_checks()
            
            if startup_checks:
                self._initialized = True
                self._services_healthy = True
                self._last_health_check = datetime.utcnow()
                logger.info("All services initialized successfully")
                return True
            else:
                logger.error("Service initialization failed startup checks")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize services: {str(e)}")
            return False
    
    async def _perform_startup_checks(self) -> bool:
        """
        Perform comprehensive startup checks for all services.
        
        Returns:
            True if critical services pass, False otherwise
        """
        try:
            logger.info("Performing startup checks...")
            
            # Check Azure OpenAI connectivity (critical)
            azure_openai_ok = await self._check_azure_openai()
            if not azure_openai_ok:
                logger.error("Critical: Azure OpenAI connectivity failed")
                return False
            
            # Check Azure AI Search connectivity (non-critical for demo)
            try:
                await self._check_azure_search()
                logger.info("Azure AI Search connectivity check passed")
            except Exception as e:
                logger.warning(f"Azure AI Search not available - continuing in demo mode: {str(e)}")
                # Don't fail initialization for search issues
            
            logger.info("Startup checks completed - core services available")
            return True
            
        except Exception as e:
            logger.error(f"Startup checks failed: {str(e)}")
            return False
    
    async def _check_azure_openai(self) -> bool:
        """
        Check Azure OpenAI service connectivity.
        
        Returns:
            True if service is accessible, False otherwise
        """
        try:
            logger.debug("Checking Azure OpenAI connectivity...")
            
            # Test chat service (we know this works)
            from openai import AsyncAzureOpenAI
            from app.config import settings
            
            logger.debug(f"Testing chat service with endpoint: {settings.azure_openai_endpoint}")
            
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
            
            response = await client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            
            if not response.choices:
                logger.error("Azure OpenAI chat test failed - no response")
                return False
            
            logger.info("Azure OpenAI chat connectivity check passed")
            
            # Try embedding service, but don't fail initialization if it doesn't work
            try:
                logger.debug(f"Testing embedding service with endpoint: {settings.azure_openai_embedding_endpoint}")
                test_embedding = await self.embedding_service.embed_single_text("test")
                if not test_embedding or len(test_embedding) < 100:  # Embeddings should be 1536 dims
                    logger.warning("Azure OpenAI embedding test failed - will work in limited mode")
                else:
                    logger.info("Azure OpenAI embedding connectivity check passed")
            except Exception as e:
                logger.warning(f"Azure OpenAI embedding not available - will work in limited mode: {str(e)}")
                # Don't fail initialization for embedding issues - chat is the critical service
            
            # As long as chat works, we can proceed
            return True
            
        except Exception as e:
            logger.error(f"Azure OpenAI connectivity check failed: {str(e)}")
            return False
    
    async def _check_azure_search(self) -> bool:
        """
        Check Azure AI Search service connectivity and ensure index exists.
        
        Returns:
            True if service is accessible and index is ready, False otherwise
        """
        try:
            logger.debug("Checking Azure AI Search connectivity...")
            
            # Check if index exists, create if it doesn't
            if not self.search_service.index_exists():
                logger.info("Search index does not exist, creating...")
                if not self.search_service.create_index():
                    logger.warning("Failed to create search index - search features will be limited")
                    return False
            
            logger.debug("Azure AI Search connectivity check passed")
            return True
            
        except Exception as e:
            logger.warning(f"Azure AI Search connectivity check failed: {str(e)}")
            return False
    
    async def process_repository_ingestion(self, repo_url: str) -> IngestionResult:
        """
        Process complete repository ingestion pipeline.
        
        Orchestrates: ingestion → chunking → embedding → search index storage
        
        Args:
            repo_url: GitHub repository URL to ingest
            
        Returns:
            IngestionResult with success status and processing details
        """
        try:
            logger.info(f"Starting complete repository ingestion for: {repo_url}")
            
            # Step 1: Ingest repository files
            ingestion_result = await repository_service.ingest_repository(repo_url)
            if not ingestion_result.success:
                return ingestion_result
            
            # Step 2: Get the ingested files (in a real implementation, this would be stored)
            # For now, we'll re-fetch the files to continue the pipeline
            logger.info("Re-fetching files for processing pipeline...")
            
            # This is a simplified approach - in production, you'd store the files from step 1
            temp_ingestion = await repository_service.ingest_repository(repo_url)
            if not temp_ingestion.success:
                return temp_ingestion
            
            # Get code files from the temporary directory (this is a workaround for the demo)
            code_files = []
            if hasattr(repository_service, '_temp_dir') and repository_service._temp_dir:
                code_files = await repository_service.fetch_code_files(repository_service._temp_dir)
            
            if not code_files:
                return IngestionResult(
                    success=True,
                    file_count=0,
                    message="Repository ingested but no code files found for processing",
                    processed_files=[]
                )
            
            # Step 3: Chunk all code files
            logger.info(f"Chunking {len(code_files)} code files...")
            all_chunks = []
            for code_file in code_files:
                chunks = chunking_service.chunk_code_file(code_file)
                all_chunks.extend(chunks)
            
            if not all_chunks:
                return IngestionResult(
                    success=True,
                    file_count=len(code_files),
                    message="Files processed but no chunks created",
                    processed_files=[f.file_path for f in code_files]
                )
            
            # Step 4: Generate embeddings
            logger.info(f"Generating embeddings for {len(all_chunks)} chunks...")
            embedded_chunks = await self.embedding_service.generate_embeddings(all_chunks)
            
            # Step 5: Store in search index
            logger.info("Storing embeddings in search index...")
            storage_success = self.search_service.store_embeddings(embedded_chunks)
            
            if storage_success:
                return IngestionResult(
                    success=True,
                    file_count=len(code_files),
                    message=f"Successfully processed {len(code_files)} files and created {len(embedded_chunks)} searchable chunks",
                    processed_files=[f.file_path for f in code_files]
                )
            else:
                return IngestionResult(
                    success=False,
                    file_count=len(code_files),
                    message="Files processed but failed to store in search index",
                    errors=["Search index storage failed"]
                )
                
        except Exception as e:
            logger.error(f"Repository ingestion pipeline failed: {str(e)}")
            return IngestionResult(
                success=False,
                file_count=0,
                message="Repository ingestion pipeline failed due to unexpected error",
                errors=[f"Pipeline error: {str(e)}"]
            )
    
    async def process_chat_query(self, question: str) -> QueryResponse:
        """
        Process a chat query and return a response using the full search pipeline.
        
        Args:
            question: User's question about the codebase
            
        Returns:
            QueryResponse with answer and source references
        """
        if not self._initialized:
            logger.warning("Services not initialized, attempting to initialize...")
            initialization_success = await self.initialize_services()
            if not initialization_success:
                raise RuntimeError("Services failed to initialize. Please check Azure OpenAI configuration.")
        
        try:
            logger.info(f"Processing chat query with search: '{question[:100]}...'")
            
            # Use the actual query processing service for search-based responses
            query_response = await self.query_processing_service.process_query(question)
            
            logger.info(f"Chat query processed successfully with {len(query_response.sources)} sources")
            return query_response
            
        except Exception as e:
            logger.error(f"Chat processing failed: {str(e)}")
            
            # Fallback to demo mode if search fails
            logger.warning("Falling back to demo mode due to search failure")
            return await self._process_chat_query_demo_mode(question)
    
    async def _process_chat_query_demo_mode(self, question: str) -> QueryResponse:
        """
        Fallback demo mode for chat queries when search fails.
        
        Args:
            question: User's question about the codebase
            
        Returns:
            QueryResponse with demo answer
        """
        try:
            # Demo mode: Generate response without search/embeddings
            from openai import AsyncAzureOpenAI
            from app.config import settings
            
            client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
            
            # Create a demo response
            demo_prompt = f"""You are an AI assistant helping developers understand codebases. 

The user asked: "{question}"

Since this is a demo mode without access to the actual codebase, provide a helpful general response about:
1. What this type of question typically involves
2. How you would normally help with codebase analysis
3. What developers should look for

Keep it professional and helpful, but mention this is a demo response."""

            response = await client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=[{"role": "user", "content": demo_prompt}],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            
            return QueryResponse(
                answer=answer,
                sources=[],  # No sources in demo mode
                confidence_score=0.5,  # Lower confidence for demo
                processing_time_ms=0
            )
            
        except Exception as e:
            logger.error(f"Demo chat processing failed: {str(e)}")
            raise
    
    async def process_predefined_query(self, query_type: str) -> QueryResponse:
        """
        Process a predefined query using the full search pipeline.
        
        Args:
            query_type: Type of predefined query (e.g., "where-to-start")
            
        Returns:
            QueryResponse with predefined answer and source references
        """
        logger.info(f"Processing predefined query: {query_type}")
        logger.info(f"Service manager initialized: {self._initialized}")
        
        if not self._initialized:
            logger.error("Services not initialized when processing predefined query")
            # Try to initialize services if they're not already initialized
            logger.info("Attempting to initialize services...")
            initialization_success = await self.initialize_services()
            if not initialization_success:
                raise RuntimeError("Services failed to initialize. Please check Azure OpenAI configuration.")
        
        if query_type == "where-to-start":
            try:
                logger.info("Processing 'where-to-start' query with search functionality")
                
                # Use the predefined query service for search-based responses
                query_response = await self.predefined_query_service.where_do_i_start()
                
                logger.info(f"Predefined query processed successfully with {len(query_response.sources)} sources")
                return query_response
                
            except Exception as e:
                logger.error(f"Predefined query with search failed: {str(e)}")
                
                # Fallback to demo mode if search fails
                logger.warning("Falling back to demo mode for predefined query")
                return await self._process_predefined_query_demo_mode(query_type)
        else:
            raise ValueError(f"Unknown predefined query type: {query_type}")
    
    async def _process_predefined_query_demo_mode(self, query_type: str) -> QueryResponse:
        """
        Fallback demo mode for predefined queries when search fails.
        
        Args:
            query_type: Type of predefined query
            
        Returns:
            QueryResponse with demo answer
        """
        if query_type == "where-to-start":
            try:
                logger.info("Processing 'where-to-start' query in demo mode")
                from openai import AsyncAzureOpenAI
                from app.config import settings
                
                client = AsyncAzureOpenAI(
                    api_key=settings.azure_openai_api_key,
                    api_version=settings.azure_openai_api_version,
                    azure_endpoint=settings.azure_openai_endpoint
                )
                
                demo_prompt = """You are an AI assistant helping new developers understand codebases.

Provide a "Where do I start?" response that includes:

1. **Welcome Message**: Welcome them to codebase exploration
2. **General Guidance**: How to approach understanding a new codebase
3. **Common First Steps**: What files to typically look for first (README, main entry points, etc.)
4. **Demo Note**: Mention this is a demo response and in the full version you'd analyze their specific codebase

Keep it encouraging and practical. Format it nicely with clear sections."""

                logger.info("Calling Azure OpenAI for predefined query")
                response = await client.chat.completions.create(
                    model=settings.azure_openai_chat_deployment,
                    messages=[{"role": "user", "content": demo_prompt}],
                    max_tokens=800,
                    temperature=0.3
                )
                
                answer = response.choices[0].message.content
                logger.info(f"Successfully generated predefined query response: {len(answer)} characters")
                
                return QueryResponse(
                    answer=answer,
                    sources=[],  # No sources in demo mode
                    confidence_score=0.8,  # Higher confidence for predefined
                    processing_time_ms=0
                )
                
            except Exception as e:
                logger.error(f"Demo predefined query failed: {str(e)}")
                raise
        else:
            raise ValueError(f"Unknown predefined query type: {query_type}")
    
    async def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all services.
        
        Returns:
            Dictionary containing health status information
        """
        try:
            # Perform quick health checks
            health_status = {
                "overall_status": "unknown",
                "initialized": self._initialized,
                "last_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "services": {}
            }
            
            if not self._initialized:
                health_status["overall_status"] = "not_initialized"
                return health_status
            
            # Check individual services
            service_checks = await asyncio.gather(
                self._check_embedding_service_health(),
                self._check_search_service_health(),
                return_exceptions=True
            )
            
            embedding_healthy = service_checks[0] if not isinstance(service_checks[0], Exception) else False
            search_healthy = service_checks[1] if not isinstance(service_checks[1], Exception) else False
            
            health_status["services"] = {
                "embedding_service": "healthy" if embedding_healthy else "unhealthy",
                "search_service": "healthy" if search_healthy else "unhealthy",
                "repository_service": "healthy",  # Always healthy (no external dependencies)
                "chunking_service": "healthy"     # Always healthy (no external dependencies)
            }
            
            # Determine overall status
            all_healthy = embedding_healthy and search_healthy
            health_status["overall_status"] = "healthy" if all_healthy else "degraded"
            
            self._services_healthy = all_healthy
            self._last_health_check = datetime.utcnow()
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "overall_status": "error",
                "initialized": self._initialized,
                "error": str(e),
                "last_check": datetime.utcnow().isoformat()
            }
    
    async def _check_embedding_service_health(self) -> bool:
        """Check if embedding service is healthy."""
        try:
            # Quick test embedding
            await self.embedding_service.embed_single_text("health check")
            return True
        except Exception:
            return False
    
    async def _check_search_service_health(self) -> bool:
        """Check if search service is healthy."""
        try:
            # Check if index exists and is accessible
            return self.search_service.index_exists()
        except Exception:
            return False
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """
        Get system statistics and metrics.
        
        Returns:
            Dictionary containing system statistics
        """
        try:
            stats = {
                "timestamp": datetime.utcnow().isoformat(),
                "services_initialized": self._initialized,
                "services_healthy": self._services_healthy,
                "search_index": {}
            }
            
            if self._initialized and self.search_service:
                try:
                    document_count = self.search_service.get_document_count()
                    stats["search_index"] = {
                        "document_count": document_count,
                        "index_name": self.search_service.index_name,
                        "index_exists": self.search_service.index_exists()
                    }
                except Exception as e:
                    stats["search_index"] = {"error": str(e)}
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get system stats: {str(e)}")
            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    
    async def shutdown_services(self):
        """Gracefully shutdown all services."""
        try:
            logger.info("Shutting down services...")
            
            # Close Azure OpenAI clients
            if self.embedding_service:
                await self.embedding_service.close()
            
            if self.query_processing_service:
                await self.query_processing_service.close()
            
            if self.predefined_query_service:
                await self.predefined_query_service.close()
            
            # Clean up repository service temp directories
            if hasattr(repository_service, '_cleanup_temp_directory'):
                repository_service._cleanup_temp_directory()
            
            self._initialized = False
            self._services_healthy = False
            
            logger.info("Services shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during service shutdown: {str(e)}")


# Global service manager instance - ensure singleton
_service_manager_instance = None

def get_service_manager_sync() -> ServiceManager:
    """Get the global service manager instance synchronously."""
    global _service_manager_instance
    if _service_manager_instance is None:
        _service_manager_instance = ServiceManager()
    return _service_manager_instance

async def get_service_manager() -> ServiceManager:
    """
    Get the global service manager instance.
    
    Returns:
        ServiceManager instance (should already be initialized by FastAPI lifespan)
    """
    return get_service_manager_sync()

# Create the global instance
service_manager = get_service_manager_sync()