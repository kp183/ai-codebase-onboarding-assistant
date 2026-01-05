"""
Azure AI Search service for vector similarity search and index management.

This service handles the creation and management of Azure AI Search indexes,
storing embeddings with metadata, and performing vector similarity searches
for code chunk retrieval.
"""

import logging
from typing import List, Optional, Dict, Any
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.models import VectorizedQuery
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

from app.models.data_models import EmbeddedChunk, CodeChunk, SourceReference

logger = logging.getLogger(__name__)


class SearchResult:
    """Represents a search result with relevance score and metadata."""
    
    def __init__(self, chunk: CodeChunk, score: float):
        self.chunk = chunk
        self.score = score
        
    def to_source_reference(self, preview_length: int = 200) -> SourceReference:
        """Convert search result to source reference with content preview."""
        content_preview = self.chunk.content[:preview_length]
        if len(self.chunk.content) > preview_length:
            content_preview += "..."
            
        return SourceReference(
            file_path=self.chunk.file_path,
            start_line=self.chunk.start_line,
            end_line=self.chunk.end_line,
            content_preview=content_preview
        )


class SearchService:
    """
    Service for managing Azure AI Search operations.
    
    Handles index creation, document storage, and vector similarity search
    for code chunk retrieval with metadata preservation.
    """
    
    def __init__(self, search_endpoint: str = None, api_key: str = None, index_name: str = None):
        """
        Initialize the search service with Azure AI Search credentials.
        
        Args:
            search_endpoint: Optional Azure Search endpoint override
            api_key: Optional API key override
            index_name: Optional index name override
        """
        if search_endpoint and api_key and index_name:
            self.search_endpoint = search_endpoint
            self.api_key = api_key
            self.index_name = index_name
        else:
            # Import settings only when needed to avoid config issues in tests
            from app.config import settings
            self.search_endpoint = settings.azure_search_endpoint
            self.api_key = settings.azure_search_api_key
            self.index_name = settings.azure_search_index_name
        
        # Initialize clients
        credential = AzureKeyCredential(self.api_key)
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=credential
        )
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=self.index_name,
            credential=credential
        )
        
    def create_index(self) -> bool:
        """
        Create the Azure AI Search index with vector fields and metadata.
        
        Returns:
            True if index was created or already exists, False otherwise
            
        Raises:
            Exception: If index creation fails
        """
        try:
            logger.info(f"Creating Azure AI Search index: {self.index_name}")
            
            # Define the search fields
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SimpleField(name="file_path", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="start_line", type=SearchFieldDataType.Int32),
                SimpleField(name="end_line", type=SearchFieldDataType.Int32),
                SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="chunk_type", type=SearchFieldDataType.String, filterable=True),
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    vector_search_dimensions=1536,
                    vector_search_profile_name="default-vector-profile"
                )
            ]
            
            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="default-hnsw-algorithm")
                ],
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-hnsw-algorithm"
                    )
                ]
            )
            
            # Configure semantic search for better relevance
            semantic_config = SemanticConfiguration(
                name="default-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            
            # Create the index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            self.index_client.create_index(index)
            logger.info(f"Successfully created index: {self.index_name}")
            return True
            
        except ResourceExistsError:
            logger.info(f"Index {self.index_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {self.index_name}: {str(e)}")
            raise
    
    def store_embeddings(self, embedded_chunks: List[EmbeddedChunk]) -> bool:
        """
        Store embeddings and metadata in the Azure AI Search index.
        
        Args:
            embedded_chunks: List of embedded chunks to store
            
        Returns:
            True if storage was successful, False otherwise
            
        Raises:
            Exception: If storage operation fails
        """
        if not embedded_chunks:
            logger.warning("No embedded chunks provided for storage")
            return True
            
        try:
            logger.info(f"Storing {len(embedded_chunks)} embedded chunks in search index")
            
            # Convert embedded chunks to search documents
            documents = []
            for embedded_chunk in embedded_chunks:
                chunk = embedded_chunk.chunk
                document = {
                    "id": chunk.id,
                    "content": chunk.content,
                    "file_path": chunk.file_path,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "content_vector": embedded_chunk.embedding
                }
                documents.append(document)
            
            # Upload documents to the index
            result = self.search_client.upload_documents(documents)
            
            # Check for any failures
            failed_count = sum(1 for r in result if not r.succeeded)
            if failed_count > 0:
                logger.warning(f"{failed_count} documents failed to upload")
                
            success_count = len(result) - failed_count
            logger.info(f"Successfully stored {success_count} embedded chunks")
            
            return failed_count == 0
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {str(e)}")
            raise
    
    def delete_index(self) -> bool:
        """
        Delete the Azure AI Search index.
        
        Returns:
            True if deletion was successful or index didn't exist, False otherwise
        """
        try:
            logger.info(f"Deleting Azure AI Search index: {self.index_name}")
            self.index_client.delete_index(self.index_name)
            logger.info(f"Successfully deleted index: {self.index_name}")
            return True
        except ResourceNotFoundError:
            logger.info(f"Index {self.index_name} does not exist")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {self.index_name}: {str(e)}")
            return False
    
    def vector_search(self, query_embedding: List[float], top_k: int = 5, 
                     filters: Optional[str] = None) -> List[SearchResult]:
        """
        Perform vector similarity search against stored embeddings.
        
        Args:
            query_embedding: Vector embedding of the search query
            top_k: Number of top results to return (default: 5)
            filters: Optional OData filter expression
            
        Returns:
            List of search results ranked by relevance score
            
        Raises:
            Exception: If search operation fails
        """
        try:
            logger.debug(f"Performing vector search with top_k={top_k}")
            
            # Create vectorized query
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            # Perform the search
            search_results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filters,
                top=top_k,
                select=["id", "content", "file_path", "start_line", "end_line", 
                       "language", "chunk_type"]
            )
            
            # Convert results to SearchResult objects
            results = []
            for result in search_results:
                # Reconstruct CodeChunk from search result
                chunk = CodeChunk(
                    id=result["id"],
                    file_path=result["file_path"],
                    content=result["content"],
                    start_line=result["start_line"],
                    end_line=result["end_line"],
                    language=result["language"],
                    chunk_type=result["chunk_type"],
                    metadata={}
                )
                
                # Get relevance score
                score = result.get("@search.score", 0.0)
                
                search_result = SearchResult(chunk=chunk, score=score)
                results.append(search_result)
            
            logger.debug(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise
    
    def search_by_text(self, query_text: str, top_k: int = 5, 
                      filters: Optional[str] = None) -> List[SearchResult]:
        """
        Perform text-based search against stored content.
        
        Args:
            query_text: Text query to search for
            top_k: Number of top results to return (default: 5)
            filters: Optional OData filter expression
            
        Returns:
            List of search results ranked by relevance score
            
        Raises:
            Exception: If search operation fails
        """
        try:
            logger.debug(f"Performing text search for: '{query_text}' with top_k={top_k}")
            
            # Perform the search
            search_results = self.search_client.search(
                search_text=query_text,
                filter=filters,
                top=top_k,
                select=["id", "content", "file_path", "start_line", "end_line", 
                       "language", "chunk_type"]
            )
            
            # Convert results to SearchResult objects
            results = []
            for result in search_results:
                # Reconstruct CodeChunk from search result
                chunk = CodeChunk(
                    id=result["id"],
                    file_path=result["file_path"],
                    content=result["content"],
                    start_line=result["start_line"],
                    end_line=result["end_line"],
                    language=result["language"],
                    chunk_type=result["chunk_type"],
                    metadata={}
                )
                
                # Get relevance score
                score = result.get("@search.score", 0.0)
                
                search_result = SearchResult(chunk=chunk, score=score)
                results.append(search_result)
            
            logger.debug(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Text search failed: {str(e)}")
            raise
    
    def hybrid_search(self, query_text: str, query_embedding: List[float], 
                     top_k: int = 5, filters: Optional[str] = None) -> List[SearchResult]:
        """
        Perform hybrid search combining text and vector similarity.
        
        Args:
            query_text: Text query to search for
            query_embedding: Vector embedding of the search query
            top_k: Number of top results to return (default: 5)
            filters: Optional OData filter expression
            
        Returns:
            List of search results ranked by combined relevance score
            
        Raises:
            Exception: If search operation fails
        """
        try:
            logger.debug(f"Performing hybrid search for: '{query_text}' with top_k={top_k}")
            
            # Create vectorized query
            vector_query = VectorizedQuery(
                vector=query_embedding,
                k_nearest_neighbors=top_k,
                fields="content_vector"
            )
            
            # Perform the hybrid search
            search_results = self.search_client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=filters,
                top=top_k,
                select=["id", "content", "file_path", "start_line", "end_line", 
                       "language", "chunk_type"]
            )
            
            # Convert results to SearchResult objects
            results = []
            for result in search_results:
                # Reconstruct CodeChunk from search result
                chunk = CodeChunk(
                    id=result["id"],
                    file_path=result["file_path"],
                    content=result["content"],
                    start_line=result["start_line"],
                    end_line=result["end_line"],
                    language=result["language"],
                    chunk_type=result["chunk_type"],
                    metadata={}
                )
                
                # Get relevance score
                score = result.get("@search.score", 0.0)
                
                search_result = SearchResult(chunk=chunk, score=score)
                results.append(search_result)
            
            logger.debug(f"Found {len(results)} search results")
            return results
            
        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            raise
    
    def get_document_count(self) -> int:
        """
        Get the total number of documents in the index.
        
        Returns:
            Number of documents in the index
            
        Raises:
            Exception: If count operation fails
        """
        try:
            # Perform an empty search to get total count
            results = self.search_client.search(
                search_text="*",
                include_total_count=True,
                top=0
            )
            return results.get_count()
        except Exception as e:
            logger.error(f"Failed to get document count: {str(e)}")
            raise
    
    def clear_index(self) -> bool:
        """
        Clear all documents from the index.
        
        Returns:
            True if clearing was successful, False otherwise
        """
        try:
            logger.info(f"Clearing all documents from index: {self.index_name}")
            
            # Get all document IDs
            results = self.search_client.search(
                search_text="*",
                select=["id"],
                top=10000  # Adjust based on expected max documents
            )
            
            # Delete all documents
            documents_to_delete = [{"id": result["id"]} for result in results]
            
            if documents_to_delete:
                delete_result = self.search_client.delete_documents(documents_to_delete)
                failed_count = sum(1 for r in delete_result if not r.succeeded)
                
                if failed_count > 0:
                    logger.warning(f"{failed_count} documents failed to delete")
                    return False
                
                logger.info(f"Successfully cleared {len(documents_to_delete)} documents")
            else:
                logger.info("Index is already empty")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear index: {str(e)}")
            return False
    
    def index_exists(self) -> bool:
        """
        Check if the search index exists.
        
        Returns:
            True if index exists, False otherwise
        """
        try:
            self.index_client.get_index(self.index_name)
            return True
        except ResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Error checking index existence: {str(e)}")
            return False


# Global search service instance - initialized lazily
_search_service = None

def get_search_service() -> SearchService:
    """Get the global search service instance."""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service