"""
Embedding service for generating vector embeddings using Azure OpenAI.

This service handles the generation of vector embeddings for code chunks using
Azure OpenAI's text-embedding-3-small model, with batch processing and retry logic.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional
from openai import AsyncAzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.models.data_models import CodeChunk, EmbeddedChunk

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating vector embeddings using Azure OpenAI.
    
    Handles batch processing, retry logic, and metadata preservation
    for code chunk embeddings.
    """
    
    def __init__(self, client=None, embedding_model=None, batch_size=100):
        """
        Initialize the embedding service with Azure OpenAI client.
        
        Args:
            client: Optional Azure OpenAI client (for testing)
            embedding_model: Optional model name override
            batch_size: Optional batch size override
        """
        if client is not None:
            self.client = client
            self.embedding_model = embedding_model or "text-embedding-3-small"
        else:
            # Import settings only when needed to avoid config issues in tests
            from app.config import settings
            self.client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_embedding_api_key,
                api_version=settings.azure_openai_embedding_api_version,
                azure_endpoint=settings.azure_openai_embedding_endpoint
            )
            self.embedding_model = settings.azure_openai_embedding_deployment
        
        self.batch_size = batch_size
        
    async def generate_embeddings(self, chunks: List[CodeChunk]) -> List[EmbeddedChunk]:
        """
        Generate embeddings for a list of code chunks.
        
        Args:
            chunks: List of code chunks to embed
            
        Returns:
            List of embedded chunks with vector embeddings
            
        Raises:
            Exception: If embedding generation fails after retries
        """
        if not chunks:
            return []
            
        logger.info(f"Generating embeddings for {len(chunks)} code chunks")
        
        embedded_chunks = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            logger.debug(f"Processing batch {i//self.batch_size + 1} with {len(batch)} chunks")
            
            try:
                batch_embeddings = await self._batch_embed([chunk.content for chunk in batch])
                
                # Create EmbeddedChunk objects with metadata
                for chunk, embedding in zip(batch, batch_embeddings):
                    embedded_chunk = EmbeddedChunk(
                        chunk=chunk,
                        embedding=embedding,
                        embedding_model=self.embedding_model,
                        created_at=datetime.utcnow()
                    )
                    embedded_chunks.append(embedded_chunk)
                    
            except Exception as e:
                logger.error(f"Failed to process batch {i//self.batch_size + 1}: {str(e)}")
                raise
                
        logger.info(f"Successfully generated {len(embedded_chunks)} embeddings")
        return embedded_chunks
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((Exception,))
    )
    async def _batch_embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts with retry logic.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
            
        Raises:
            Exception: If API call fails after retries
        """
        try:
            logger.debug(f"Calling Azure OpenAI embedding API for {len(texts)} texts")
            
            response = await self.client.embeddings.create(
                input=texts,
                model=self.embedding_model
            )
            
            # Extract embeddings from response
            embeddings = [data.embedding for data in response.data]
            
            logger.debug(f"Successfully received {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.warning(f"Embedding API call failed: {str(e)}")
            raise
    
    async def embed_single_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector
            
        Raises:
            Exception: If embedding generation fails
        """
        embeddings = await self._batch_embed([text])
        return embeddings[0]
    
    async def close(self):
        """Close the Azure OpenAI client connection."""
        if hasattr(self.client, 'close'):
            await self.client.close()


# Global embedding service instance - initialized lazily
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service