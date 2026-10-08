"""
Embedding service for Azure OpenAI or optional local FastEmbed vectors.

This service handles code chunk embeddings with batch processing and retry logic.
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
            self.local_mode = False
        else:
            # Import settings only when needed to avoid config issues in tests
            from app.config import settings
            self.embedding_model = settings.azure_openai_embedding_deployment
            self.local_mode = settings.demo_mode
            self.local_model = None
            self.use_local_embeddings = settings.demo_mode and settings.local_embeddings
            if self.use_local_embeddings:
                try:
                    from fastembed import TextEmbedding
                except ImportError as exc:
                    raise RuntimeError(
                        "LOCAL_EMBEDDINGS=true requires the optional dependencies in requirements-local.txt"
                    ) from exc
                self.embedding_model = settings.local_embedding_model
                self.local_model = TextEmbedding(model_name=self.embedding_model, threads=2)
            elif settings.demo_mode:
                self.embedding_model = "bm25-only"
            self.client = None if settings.demo_mode else AsyncAzureOpenAI(
                api_key=settings.azure_openai_embedding_api_key,
                api_version=settings.azure_openai_embedding_api_version,
                azure_endpoint=settings.azure_openai_embedding_endpoint
            )
        
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

        embedding_texts = [self._chunk_embedding_text(chunk) for chunk in chunks]
        if self.local_mode:
            vectors = (
                await asyncio.to_thread(self._embed_local, embedding_texts)
                if self.use_local_embeddings
                else [[] for _ in chunks]
            )
            return [
                EmbeddedChunk(
                    chunk=chunk,
                    embedding=vector,
                    embedding_model=self.embedding_model,
                    created_at=datetime.utcnow(),
                )
                for chunk, vector in zip(chunks, vectors)
            ]
            
        logger.info(f"Generating embeddings for {len(chunks)} code chunks")
        
        embedded_chunks = []
        
        # Process chunks in batches
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            logger.debug(f"Processing batch {i//self.batch_size + 1} with {len(batch)} chunks")
            
            try:
                batch_embeddings = await self._batch_embed(
                    [self._chunk_embedding_text(chunk) for chunk in batch]
                )
                
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
        if self.local_mode:
            if not self.use_local_embeddings:
                return [[] for _ in texts]
            return await asyncio.to_thread(self._embed_local, texts)
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
        if self.local_mode and not self.use_local_embeddings:
            return []
        embeddings = await self._batch_embed([text])
        return embeddings[0]

    @staticmethod
    def _chunk_embedding_text(chunk: CodeChunk) -> str:
        return f"File path: {chunk.file_path}\n{chunk.content}"

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Run the optional local FastEmbed model with no remote inference API."""
        return [
            vector.tolist()
            for vector in self.local_model.embed(texts, batch_size=32, parallel=None)
        ]
    
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
