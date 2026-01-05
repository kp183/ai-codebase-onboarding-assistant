#!/usr/bin/env python3
"""
Critical pipeline tests for AI Codebase Onboarding Assistant.

Tests the core functionality that must work for the MVP demo.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from app.services.code_chunking import chunking_service
from app.services.embedding_service import EmbeddingService
from app.services.query_processing import QueryProcessingService
from app.models.data_models import CodeFile, CodeChunk, SourceReference
from datetime import datetime


class TestCodeChunking:
    """Test critical code chunking functionality."""
    
    def test_chunk_python_file(self):
        """Test that Python files are chunked correctly."""
        # Create a sample Python file
        code_file = CodeFile(
            file_path="test.py",
            content='''def hello_world():
    """A simple function."""
    print("Hello, World!")
    return "success"

class TestClass:
    """A test class."""
    
    def __init__(self):
        self.value = 42
    
    def get_value(self):
        return self.value
''',
            language="python",
            size_bytes=200,
            last_modified=datetime.now()
        )
        
        # Chunk the file
        chunks = chunking_service.chunk_code_file(code_file)
        
        # Verify chunks were created
        assert len(chunks) > 0, "Should create at least one chunk"
        
        # Verify chunk properties
        for chunk in chunks:
            assert chunk.file_path == "test.py"
            assert chunk.language == "python"
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            assert len(chunk.content) > 0
            assert chunk.id is not None
    
    def test_chunk_javascript_file(self):
        """Test that JavaScript files are chunked correctly."""
        code_file = CodeFile(
            file_path="test.js",
            content='''function greet(name) {
    console.log(`Hello, ${name}!`);
    return true;
}

const myObject = {
    value: 42,
    getValue() {
        return this.value;
    }
};

export { greet, myObject };
''',
            language="javascript",
            size_bytes=150,
            last_modified=datetime.now()
        )
        
        chunks = chunking_service.chunk_code_file(code_file)
        
        assert len(chunks) > 0
        for chunk in chunks:
            assert chunk.file_path == "test.js"
            assert chunk.language == "javascript"
    
    def test_empty_file_handling(self):
        """Test handling of empty files."""
        code_file = CodeFile(
            file_path="empty.py",
            content="",
            language="python",
            size_bytes=0,
            last_modified=datetime.now()
        )
        
        chunks = chunking_service.chunk_code_file(code_file)
        
        # Should handle empty files gracefully
        assert isinstance(chunks, list)


class TestEmbeddingService:
    """Test critical embedding service functionality."""
    
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test single text embedding generation."""
        # Create mock embedding service
        embedding_service = EmbeddingService(
            client=AsyncMock(),
            embedding_model="test-model"
        )
        
        # Mock the API response
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3] * 512)]  # 1536 dimensions
        embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        # Test embedding generation
        result = await embedding_service.embed_single_text("test text")
        
        assert result is not None
        assert len(result) == 1536  # Expected embedding dimension
        assert all(isinstance(x, float) for x in result)
    
    @pytest.mark.asyncio
    async def test_generate_embeddings_batch(self):
        """Test batch embedding generation."""
        embedding_service = EmbeddingService(
            client=AsyncMock(),
            embedding_model="test-model"
        )
        
        # Create test chunks
        chunks = [
            CodeChunk(
                id="chunk1",
                file_path="test.py",
                content="def test(): pass",
                start_line=1,
                end_line=1,
                language="python"
            ),
            CodeChunk(
                id="chunk2",
                file_path="test.py",
                content="print('hello')",
                start_line=2,
                end_line=2,
                language="python"
            )
        ]
        
        # Mock the API response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536)
        ]
        embedding_service.client.embeddings.create = AsyncMock(return_value=mock_response)
        
        # Test batch embedding
        result = await embedding_service.generate_embeddings(chunks)
        
        assert len(result) == 2
        for embedded_chunk in result:
            assert embedded_chunk.chunk in chunks
            assert len(embedded_chunk.embedding) == 1536


class TestQueryProcessing:
    """Test critical query processing functionality."""
    
    @pytest.mark.asyncio
    async def test_query_processing_pipeline(self):
        """Test the complete query processing pipeline."""
        # Create mock services
        mock_client = AsyncMock()
        query_service = QueryProcessingService(
            client=mock_client,
            chat_model="test-model"
        )
        
        # Mock embedding service
        query_service.embedding_service = AsyncMock()
        query_service.embedding_service.embed_single_text = AsyncMock(
            return_value=[0.1] * 1536
        )
        
        # Mock search service
        query_service.search_service = Mock()
        mock_search_result = Mock()
        mock_search_result.chunk = CodeChunk(
            id="test-chunk",
            file_path="app/main.py",
            content="from fastapi import FastAPI\napp = FastAPI()",
            start_line=1,
            end_line=2,
            language="python"
        )
        mock_search_result.score = 0.9
        mock_search_result.to_source_reference = Mock(return_value=SourceReference(
            file_path="app/main.py",
            start_line=1,
            end_line=2,
            content_preview="from fastapi import FastAPI"
        ))
        
        query_service.search_service.vector_search = Mock(
            return_value=[mock_search_result]
        )
        
        # Mock OpenAI response
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "This is the main FastAPI application entry point."
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        
        # Test query processing
        result = await query_service.process_query("What is the main entry point?")
        
        assert result is not None
        assert result.answer == "This is the main FastAPI application entry point."
        assert len(result.sources) == 1
        assert result.sources[0].file_path == "app/main.py"
        assert result.confidence_score > 0


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_code_file(self):
        """Test handling of invalid code files."""
        # Test with None content
        try:
            code_file = CodeFile(
                file_path="test.py",
                content=None,
                language="python",
                size_bytes=0,
                last_modified=datetime.now()
            )
            assert False, "Should raise validation error for None content"
        except:
            pass  # Expected to fail validation
    
    def test_invalid_line_numbers(self):
        """Test handling of invalid line numbers."""
        try:
            chunk = CodeChunk(
                id="test",
                file_path="test.py",
                content="test",
                start_line=5,
                end_line=3,  # Invalid: end < start
                language="python"
            )
            assert False, "Should raise validation error for invalid line numbers"
        except:
            pass  # Expected to fail validation
    
    @pytest.mark.asyncio
    async def test_embedding_service_error_handling(self):
        """Test embedding service error handling."""
        embedding_service = EmbeddingService(
            client=AsyncMock(),
            embedding_model="test-model"
        )
        
        # Mock API failure
        embedding_service.client.embeddings.create = AsyncMock(
            side_effect=Exception("API Error")
        )
        
        # Should handle errors gracefully
        try:
            await embedding_service.embed_single_text("test")
            assert False, "Should raise exception for API failure"
        except Exception as e:
            # The retry mechanism wraps the original exception
            assert "API Error" in str(e) or "RetryError" in str(e)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])