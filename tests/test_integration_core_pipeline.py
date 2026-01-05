"""
Integration tests for the core pipeline components.

This module tests the integration between ingestion, chunking, embedding,
and search services to ensure the complete pipeline works correctly.
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.repository_ingestion import RepositoryIngestionService
from app.services.code_chunking import CodeChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.search_service import SearchService
from app.models.data_models import CodeFile


class TestCoreIntegration:
    """Integration tests for core pipeline components."""
    
    @pytest.fixture
    def sample_code_files(self):
        """Create sample code files for testing."""
        return {
            "main.py": '''def main():
    """Entry point."""
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
            "utils.py": '''class Helper:
    """Utility class."""
    
    def process(self, data):
        """Process data."""
        return data.upper()

def format_text(text):
    """Format text."""
    return text.strip()
'''
        }
    
    @pytest.mark.asyncio
    async def test_ingestion_to_chunking_integration(self, sample_code_files):
        """Test integration between ingestion and chunking services."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create sample files
            for filename, content in sample_code_files.items():
                file_path = Path(temp_dir) / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Test ingestion
            ingestion_service = RepositoryIngestionService()
            code_files = await ingestion_service.fetch_code_files(temp_dir)
            
            assert len(code_files) == 2
            
            # Test chunking integration
            chunking_service = CodeChunkingService()
            all_chunks = []
            
            for code_file in code_files:
                chunks = chunking_service.chunk_code_file(code_file)
                all_chunks.extend(chunks)
            
            # Verify integration
            assert len(all_chunks) > 0
            
            # Check that chunks reference the correct files
            chunk_files = {chunk.file_path for chunk in all_chunks}
            expected_files = {"main.py", "utils.py"}
            assert chunk_files == expected_files
            
            # Verify chunk content comes from original files
            for chunk in all_chunks:
                original_file = next(cf for cf in code_files if cf.file_path == chunk.file_path)
                assert chunk.content in original_file.content or original_file.content in chunk.content
    
    @pytest.mark.asyncio
    async def test_chunking_to_embedding_integration(self, sample_code_files):
        """Test integration between chunking and embedding services."""
        # Create a sample code file
        code_file = CodeFile(
            file_path="test.py",
            content=sample_code_files["utils.py"],
            language="python",
            size_bytes=len(sample_code_files["utils.py"]),
            last_modified=datetime.now()
        )
        
        # Test chunking
        chunking_service = CodeChunkingService()
        chunks = chunking_service.chunk_code_file(code_file)
        
        assert len(chunks) > 0
        
        # Mock embedding service
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2] * 768) for _ in chunks]  # 1536 dimensions
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        
        embedding_service = EmbeddingService(
            client=mock_client,
            embedding_model="text-embedding-3-small"
        )
        
        # Test embedding integration
        embedded_chunks = await embedding_service.generate_embeddings(chunks)
        
        # Verify integration
        assert len(embedded_chunks) == len(chunks)
        
        for i, embedded_chunk in enumerate(embedded_chunks):
            assert embedded_chunk.chunk == chunks[i]
            assert len(embedded_chunk.embedding) == 1536
            assert embedded_chunk.embedding_model == "text-embedding-3-small"
    
    @pytest.mark.asyncio
    async def test_embedding_to_search_integration(self):
        """Test integration between embedding and search services."""
        # Create sample embedded chunks
        from app.models.data_models import CodeChunk, EmbeddedChunk
        
        chunk = CodeChunk(
            id="test-chunk",
            file_path="test.py",
            content="def test(): pass",
            start_line=1,
            end_line=1,
            language="python"
        )
        
        embedded_chunk = EmbeddedChunk(
            chunk=chunk,
            embedding=[0.1] * 1536,
            embedding_model="text-embedding-3-small",
            created_at=datetime.now()
        )
        
        # Mock search service
        mock_search_client = MagicMock()
        mock_index_client = MagicMock()
        
        # Mock successful upload
        mock_upload_result = [MagicMock(succeeded=True)]
        mock_search_client.upload_documents.return_value = mock_upload_result
        
        # Mock search results
        mock_search_result = {
            "id": "test-chunk",
            "content": "def test(): pass",
            "file_path": "test.py",
            "start_line": 1,
            "end_line": 1,
            "language": "python",
            "chunk_type": "other",
            "@search.score": 0.95
        }
        mock_search_client.search.return_value = [mock_search_result]
        
        with patch('app.services.search_service.SearchClient', return_value=mock_search_client), \
             patch('app.services.search_service.SearchIndexClient', return_value=mock_index_client), \
             patch('app.services.search_service.AzureKeyCredential'):
            
            search_service = SearchService(
                search_endpoint="https://test.search.windows.net",
                api_key="test-key",
                index_name="test-index"
            )
            
            # Test storage
            storage_success = search_service.store_embeddings([embedded_chunk])
            assert storage_success is True
            
            # Test search
            query_embedding = [0.2] * 1536
            results = search_service.vector_search(query_embedding, top_k=1)
            
            assert len(results) == 1
            assert results[0].chunk.id == "test-chunk"
            assert results[0].score == 0.95
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, sample_code_files):
        """Test the complete pipeline integration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Step 1: Create files and ingest
            for filename, content in sample_code_files.items():
                file_path = Path(temp_dir) / filename
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            ingestion_service = RepositoryIngestionService()
            code_files = await ingestion_service.fetch_code_files(temp_dir)
            
            # Step 2: Chunk files
            chunking_service = CodeChunkingService()
            all_chunks = []
            for code_file in code_files:
                chunks = chunking_service.chunk_code_file(code_file)
                all_chunks.extend(chunks)
            
            # Step 3: Generate embeddings (mocked)
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1] * 1536) for _ in all_chunks]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            
            embedding_service = EmbeddingService(client=mock_client, embedding_model="test")
            embedded_chunks = await embedding_service.generate_embeddings(all_chunks)
            
            # Step 4: Store and search (mocked)
            mock_search_client = MagicMock()
            mock_index_client = MagicMock()
            
            mock_search_client.upload_documents.return_value = [MagicMock(succeeded=True) for _ in embedded_chunks]
            
            # Mock search results
            mock_search_results = []
            for i, embedded_chunk in enumerate(embedded_chunks[:3]):  # Return top 3
                result = {
                    "id": embedded_chunk.chunk.id,
                    "content": embedded_chunk.chunk.content,
                    "file_path": embedded_chunk.chunk.file_path,
                    "start_line": embedded_chunk.chunk.start_line,
                    "end_line": embedded_chunk.chunk.end_line,
                    "language": embedded_chunk.chunk.language,
                    "chunk_type": embedded_chunk.chunk.chunk_type,
                    "@search.score": 0.9 - (i * 0.1)
                }
                mock_search_results.append(result)
            
            mock_search_client.search.return_value = mock_search_results
            
            with patch('app.services.search_service.SearchClient', return_value=mock_search_client), \
                 patch('app.services.search_service.SearchIndexClient', return_value=mock_index_client), \
                 patch('app.services.search_service.AzureKeyCredential'):
                
                search_service = SearchService(
                    search_endpoint="https://test.search.windows.net",
                    api_key="test-key",
                    index_name="test-index"
                )
                
                # Store embeddings
                storage_success = search_service.store_embeddings(embedded_chunks)
                assert storage_success is True
                
                # Perform search
                query_embedding = [0.5] * 1536
                search_results = search_service.vector_search(query_embedding, top_k=3)
                
                # Verify end-to-end integration
                assert len(search_results) <= 3
                assert len(search_results) > 0
                
                # Verify that search results contain chunks from original files
                result_files = {result.chunk.file_path for result in search_results}
                expected_files = {"main.py", "utils.py"}
                assert result_files.issubset(expected_files)
                
                # Verify source reference conversion works
                for result in search_results:
                    source_ref = result.to_source_reference()
                    assert source_ref.file_path in expected_files
                    assert source_ref.start_line >= 1
                    assert len(source_ref.content_preview) > 0
    
    def test_data_consistency_through_pipeline(self):
        """Test that data remains consistent through the pipeline."""
        # Create a code file with known content
        original_content = '''def calculate(a, b):
    """Calculate sum of two numbers."""
    return a + b

class Calculator:
    """Simple calculator."""
    pass
'''
        
        code_file = CodeFile(
            file_path="calculator.py",
            content=original_content,
            language="python",
            size_bytes=len(original_content),
            last_modified=datetime.now()
        )
        
        # Test chunking preserves file reference
        chunking_service = CodeChunkingService()
        chunks = chunking_service.chunk_code_file(code_file)
        
        for chunk in chunks:
            assert chunk.file_path == "calculator.py"
            assert chunk.language == "python"
            assert chunk.content in original_content or original_content in chunk.content
            
        # Test that chunk IDs are unique
        chunk_ids = [chunk.id for chunk in chunks]
        assert len(chunk_ids) == len(set(chunk_ids)), "Chunk IDs should be unique"
        
        # Test that line numbers are consistent
        for chunk in chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            
            # Line numbers should make sense for the content
            lines_in_chunk = chunk.content.count('\n')
            expected_lines = chunk.end_line - chunk.start_line
            # Allow some flexibility due to different chunking strategies
            assert abs(lines_in_chunk - expected_lines) <= 2
    
    @pytest.mark.asyncio
    async def test_error_propagation_through_pipeline(self):
        """Test that errors are properly handled through the pipeline."""
        # Test with invalid file path
        ingestion_service = RepositoryIngestionService()
        code_files = await ingestion_service.fetch_code_files("/nonexistent/path")
        assert len(code_files) == 0  # Should handle gracefully
        
        # Test chunking with empty content
        empty_file = CodeFile(
            file_path="empty.py",
            content="",
            language="python",
            size_bytes=0,
            last_modified=datetime.now()
        )
        
        chunking_service = CodeChunkingService()
        chunks = chunking_service.chunk_code_file(empty_file)
        assert isinstance(chunks, list)  # Should return empty list, not error
        
        # Test embedding with empty chunk list
        mock_client = MagicMock()
        embedding_service = EmbeddingService(client=mock_client, embedding_model="test")
        embeddings = await embedding_service.generate_embeddings([])
        assert len(embeddings) == 0  # Should handle empty list gracefully