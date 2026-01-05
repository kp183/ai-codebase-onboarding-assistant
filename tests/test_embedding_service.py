"""
Tests for the embedding service.

This module tests the EmbeddingService functionality including
embedding generation, batch processing, and error handling.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from app.models.data_models import CodeChunk, EmbeddedChunk
from app.services.embedding_service import EmbeddingService


class TestEmbeddingService:
    """Test cases for EmbeddingService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create service with mock client to avoid config issues
        mock_client = MagicMock()
        self.service = EmbeddingService(
            client=mock_client, 
            embedding_model="text-embedding-3-small",
            batch_size=100
        )
    
    @pytest.fixture
    def sample_code_chunks(self):
        """Create sample code chunks for testing."""
        return [
            CodeChunk(
                id="chunk_1",
                file_path="test.py",
                content="def hello_world():\n    return 'Hello, World!'",
                start_line=1,
                end_line=2,
                language="python",
                chunk_type="function"
            ),
            CodeChunk(
                id="chunk_2", 
                file_path="test.py",
                content="class Calculator:\n    def add(self, a, b):\n        return a + b",
                start_line=4,
                end_line=6,
                language="python",
                chunk_type="class"
            )
        ]
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_success(self, sample_code_chunks):
        """Test successful embedding generation."""
        # Mock the Azure OpenAI client response
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6])
        ]
        
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await self.service.generate_embeddings(sample_code_chunks)
            
            # Verify results
            assert len(result) == 2
            assert all(isinstance(item, EmbeddedChunk) for item in result)
            
            # Check first embedded chunk
            first_embedded = result[0]
            assert first_embedded.chunk == sample_code_chunks[0]
            assert first_embedded.embedding == [0.1, 0.2, 0.3]
            assert first_embedded.embedding_model == "text-embedding-3-small"
            assert isinstance(first_embedded.created_at, datetime)
            
            # Verify API was called correctly
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['model'] == "text-embedding-3-small"
            assert len(call_args[1]['input']) == 2
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_empty_list(self):
        """Test handling of empty chunk list."""
        result = await self.service.generate_embeddings([])
        assert result == []
    
    @pytest.mark.asyncio
    async def test_batch_processing(self):
        """Test that large lists are processed in batches."""
        # Create more chunks than batch size
        chunks = []
        for i in range(150):  # More than default batch size of 100
            chunks.append(CodeChunk(
                id=f"chunk_{i}",
                file_path="test.py",
                content=f"def function_{i}(): pass",
                start_line=i*2+1,
                end_line=i*2+2,
                language="python"
            ))
        
        # Mock responses for multiple batches
        mock_response_1 = MagicMock()
        mock_response_1.data = [MagicMock(embedding=[0.1, 0.2]) for _ in range(100)]
        
        mock_response_2 = MagicMock()
        mock_response_2.data = [MagicMock(embedding=[0.3, 0.4]) for _ in range(50)]
        
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [mock_response_1, mock_response_2]
            
            result = await self.service.generate_embeddings(chunks)
            
            # Should process all chunks
            assert len(result) == 150
            
            # Should make two API calls (two batches)
            assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding a single text string."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.7, 0.8, 0.9])]
        
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await self.service.embed_single_text("test text")
            
            assert result == [0.7, 0.8, 0.9]
            mock_create.assert_called_once_with(
                input=["test text"],
                model="text-embedding-3-small"
            )
    
    @pytest.mark.asyncio
    async def test_retry_logic_on_failure(self, sample_code_chunks):
        """Test that retry logic works on API failures."""
        # Mock first call to fail, second to succeed
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2, 0.3]),
            MagicMock(embedding=[0.4, 0.5, 0.6])
        ]
        
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = [Exception("API Error"), mock_response]
            
            result = await self.service.generate_embeddings(sample_code_chunks)
            
            # Should succeed after retry
            assert len(result) == 2
            assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, sample_code_chunks):
        """Test behavior when all retries are exhausted."""
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("Persistent API Error")
            
            with pytest.raises(Exception):  # Accept any exception type from retry wrapper
                await self.service.generate_embeddings(sample_code_chunks)
            
            # Should retry 3 times (initial + 2 retries)
            assert mock_create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, sample_code_chunks):
        """Test that chunk metadata is preserved in embedded chunks."""
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=[0.1, 0.2]),
            MagicMock(embedding=[0.3, 0.4])
        ]
        
        with patch.object(self.service.client.embeddings, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await self.service.generate_embeddings(sample_code_chunks)
            
            # Check that all original chunk data is preserved
            for i, embedded_chunk in enumerate(result):
                original_chunk = sample_code_chunks[i]
                assert embedded_chunk.chunk.id == original_chunk.id
                assert embedded_chunk.chunk.file_path == original_chunk.file_path
                assert embedded_chunk.chunk.content == original_chunk.content
                assert embedded_chunk.chunk.start_line == original_chunk.start_line
                assert embedded_chunk.chunk.end_line == original_chunk.end_line
                assert embedded_chunk.chunk.language == original_chunk.language
                assert embedded_chunk.chunk.chunk_type == original_chunk.chunk_type
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client connection."""
        # Mock the client close method
        with patch.object(self.service.client, 'close', new_callable=AsyncMock) as mock_close:
            await self.service.close()
            mock_close.assert_called_once()
    
    def test_service_initialization(self):
        """Test that service initializes with correct configuration."""
        mock_client = MagicMock()
        service = EmbeddingService(
            client=mock_client,
            embedding_model="test-model",
            batch_size=50
        )
        
        assert service.embedding_model == "test-model"
        assert service.batch_size == 50
        assert service.client is mock_client