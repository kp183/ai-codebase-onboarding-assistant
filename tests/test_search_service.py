"""
Tests for the Azure AI Search service.

This module contains unit tests for the SearchService class,
testing index creation, document storage, and search functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import List

from app.services.search_service import SearchService, SearchResult
from app.models.data_models import CodeChunk, EmbeddedChunk, SourceReference


class TestSearchService:
    """Test cases for SearchService functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Sample test data
        self.sample_chunk = CodeChunk(
            id="test-chunk-1",
            file_path="src/main.py",
            content="def hello_world():\n    print('Hello, World!')",
            start_line=1,
            end_line=2,
            language="python",
            chunk_type="function"
        )
        
        self.sample_embedded_chunk = EmbeddedChunk(
            chunk=self.sample_chunk,
            embedding=[0.1, 0.2, 0.3] * 512,  # 1536 dimensions
            embedding_model="text-embedding-3-small",
            created_at=datetime.utcnow()
        )
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_create_index_success(self, mock_credential, mock_search_client, mock_index_client):
        """Test successful index creation."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        # Test index creation
        result = search_service.create_index()
        
        assert result is True
        mock_index_client_instance.create_index.assert_called_once()
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_store_embeddings_success(self, mock_credential, mock_search_client, mock_index_client):
        """Test successful embedding storage."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Mock successful upload
        mock_result = [Mock(succeeded=True)]
        mock_search_client_instance.upload_documents.return_value = mock_result
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        # Test storing embeddings
        result = search_service.store_embeddings([self.sample_embedded_chunk])
        
        assert result is True
        mock_search_client_instance.upload_documents.assert_called_once()
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_vector_search_success(self, mock_credential, mock_search_client, mock_index_client):
        """Test successful vector search."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Mock search results
        mock_search_result = {
            "id": "test-chunk-1",
            "content": "def hello_world():\n    print('Hello, World!')",
            "file_path": "src/main.py",
            "start_line": 1,
            "end_line": 2,
            "language": "python",
            "chunk_type": "function",
            "@search.score": 0.95
        }
        mock_search_client_instance.search.return_value = [mock_search_result]
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        # Test vector search
        query_embedding = [0.1, 0.2, 0.3] * 512
        results = search_service.vector_search(query_embedding, top_k=5)
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].chunk.id == "test-chunk-1"
        assert results[0].score == 0.95
    
    def test_search_result_to_source_reference(self):
        """Test conversion of search result to source reference."""
        search_result = SearchResult(chunk=self.sample_chunk, score=0.85)
        
        source_ref = search_result.to_source_reference(preview_length=50)
        
        assert isinstance(source_ref, SourceReference)
        assert source_ref.file_path == "src/main.py"
        assert source_ref.start_line == 1
        assert source_ref.end_line == 2
        assert len(source_ref.content_preview) <= 53  # 50 + "..."
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_empty_search_results(self, mock_credential, mock_search_client, mock_index_client):
        """Test handling of empty search results."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Mock empty search results
        mock_search_client_instance.search.return_value = []
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        # Test vector search with no results
        query_embedding = [0.1, 0.2, 0.3] * 512
        results = search_service.vector_search(query_embedding, top_k=5)
        
        assert len(results) == 0
        assert isinstance(results, list)
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_store_empty_embeddings(self, mock_credential, mock_search_client, mock_index_client):
        """Test storing empty list of embeddings."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        result = search_service.store_embeddings([])
        assert result is True
    
    @patch('app.services.search_service.SearchIndexClient')
    @patch('app.services.search_service.SearchClient')
    @patch('app.services.search_service.AzureKeyCredential')
    def test_get_document_count(self, mock_credential, mock_search_client, mock_index_client):
        """Test getting document count from index."""
        # Create mock clients
        mock_index_client_instance = Mock()
        mock_search_client_instance = Mock()
        mock_index_client.return_value = mock_index_client_instance
        mock_search_client.return_value = mock_search_client_instance
        
        # Mock search results with count
        mock_results = Mock()
        mock_results.get_count.return_value = 42
        mock_search_client_instance.search.return_value = mock_results
        
        # Create service instance
        search_service = SearchService(
            search_endpoint="https://test.search.windows.net",
            api_key="test-key",
            index_name="test-index"
        )
        
        count = search_service.get_document_count()
        
        assert count == 42
        mock_search_client_instance.search.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])