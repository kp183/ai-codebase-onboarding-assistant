"""
Query processing service for handling chat interactions and response generation.

This service orchestrates the complete pipeline from user queries to grounded responses,
including query embedding, search, context preparation, and Azure OpenAI chat completion.
"""

import asyncio
import logging
import time
from typing import List, Optional, Dict, Any
from openai import AsyncAzureOpenAI

from app.models.data_models import QueryResponse, SourceReference, CodeChunk
from app.services.embedding_service import get_embedding_service
from app.services.search_service import get_search_service, SearchResult

logger = logging.getLogger(__name__)


class QueryProcessingService:
    """
    Service for processing user queries and generating grounded responses.
    
    Orchestrates the complete pipeline: query embedding → search → context preparation → response generation
    """
    
    def __init__(self, client=None, chat_model=None):
        """
        Initialize the query processing service.
        
        Args:
            client: Optional Azure OpenAI client (for testing)
            chat_model: Optional chat model name override
        """
        if client is not None:
            self.client = client
            self.chat_model = chat_model or "gpt-4"
        else:
            # Import settings only when needed to avoid config issues in tests
            from app.config import settings
            self.client = AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint
            )
            self.chat_model = settings.azure_openai_chat_deployment
        
        self.embedding_service = get_embedding_service()
        self.search_service = get_search_service()
    
    async def process_query(self, user_question: str, top_k: int = 5) -> QueryResponse:
        """
        Process a user query and generate a grounded response.
        
        Args:
            user_question: The user's question about the codebase
            top_k: Number of top search results to use for context
            
        Returns:
            QueryResponse with answer, sources, and metadata
            
        Raises:
            Exception: If query processing fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: '{user_question[:100]}...'")
            
            # Step 1: Retrieve relevant code chunks
            relevant_chunks = await self.retrieve_relevant_chunks(user_question, top_k)
            
            # Step 2: Generate grounded response
            answer = await self.generate_grounded_response(user_question, relevant_chunks)
            
            # Step 3: Create source references
            sources = [result.to_source_reference() for result in relevant_chunks]
            
            # Step 4: Calculate confidence score based on search results
            confidence_score = self._calculate_confidence_score(relevant_chunks)
            
            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            response = QueryResponse(
                answer=answer,
                sources=sources,
                confidence_score=confidence_score,
                processing_time_ms=processing_time_ms
            )
            
            logger.info(f"Successfully processed query in {processing_time_ms}ms")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process query: {str(e)}")
            raise
    
    async def retrieve_relevant_chunks(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Retrieve relevant code chunks for a given query.
        
        Args:
            query: User query text
            top_k: Number of top results to return
            
        Returns:
            List of search results with relevance scores
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            logger.debug(f"Retrieving relevant chunks for query: '{query[:50]}...'")
            
            # Generate embedding for the query
            query_embedding = await self.embedding_service.embed_single_text(query)
            
            # Perform vector similarity search
            search_results = self.search_service.vector_search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            
            logger.debug(f"Retrieved {len(search_results)} relevant chunks")
            return search_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve relevant chunks: {str(e)}")
            raise
    
    async def generate_grounded_response(self, question: str, context_chunks: List[SearchResult]) -> str:
        """
        Generate a grounded response using Azure OpenAI chat completion.
        
        Args:
            question: User's question
            context_chunks: Relevant code chunks for context
            
        Returns:
            Generated answer text
            
        Raises:
            Exception: If response generation fails
        """
        try:
            logger.debug("Generating grounded response with Azure OpenAI")
            
            # Prepare context from search results
            context = self._prepare_context(context_chunks)
            
            # Create system prompt with grounding instructions
            system_prompt = self._create_system_prompt()
            
            # Create user prompt with question and context
            user_prompt = self._create_user_prompt(question, context)
            
            # Generate response using Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent, factual responses
                max_tokens=1000,  # Reasonable limit for responses
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            logger.debug(f"Generated response of {len(answer)} characters")
            
            return answer
            
        except Exception as e:
            logger.error(f"Failed to generate grounded response: {str(e)}")
            raise
    
    def _prepare_context(self, search_results: List[SearchResult]) -> str:
        """
        Prepare context string from search results.
        
        Args:
            search_results: List of search results to include in context
            
        Returns:
            Formatted context string
        """
        if not search_results:
            return "No relevant code found in the codebase."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            chunk = result.chunk
            context_part = f"""
Code Snippet {i}:
File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})
Language: {chunk.language}
Type: {chunk.chunk_type}

```{chunk.language}
{chunk.content}
```
"""
            context_parts.append(context_part.strip())
        
        return "\n\n".join(context_parts)
    
    def _create_system_prompt(self) -> str:
        """
        Create the system prompt with grounding instructions.
        
        Returns:
            System prompt text
        """
        return """You are an AI assistant helping developers understand a codebase. Your role is to provide accurate, helpful answers about the code based on the provided context.

IMPORTANT INSTRUCTIONS:
1. Base your answers ONLY on the provided code snippets and context
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Always reference specific files and line numbers when discussing code
4. Provide practical, actionable guidance for developers
5. Use clear, concise language appropriate for software developers
6. When explaining code, focus on what it does, how it works, and how it fits into the larger system
7. If you see patterns or architectural decisions, explain them
8. Suggest next steps or related areas to explore when helpful

FORMAT YOUR RESPONSE:
- Start with a direct answer to the question
- Provide specific details with file references
- End with practical next steps if applicable

Remember: You are helping a developer understand and navigate this codebase effectively."""
    
    def _create_user_prompt(self, question: str, context: str) -> str:
        """
        Create the user prompt with question and context.
        
        Args:
            question: User's question
            context: Prepared context from search results
            
        Returns:
            User prompt text
        """
        return f"""Question: {question}

Relevant Code Context:
{context}

Please provide a helpful answer based on the code context above."""
    
    def _calculate_confidence_score(self, search_results: List[SearchResult]) -> float:
        """
        Calculate confidence score based on search results quality.
        
        Args:
            search_results: List of search results
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        if not search_results:
            return 0.0
        
        # Simple confidence calculation based on:
        # 1. Number of results found
        # 2. Average relevance score
        # 3. Score distribution
        
        scores = [result.score for result in search_results]
        avg_score = sum(scores) / len(scores)
        
        # Normalize based on typical search score ranges (0.5-1.0 for good matches)
        normalized_score = min(avg_score / 0.8, 1.0)
        
        # Boost confidence if we have multiple good results
        result_count_factor = min(len(search_results) / 3.0, 1.0)
        
        # Final confidence is weighted average
        confidence = (normalized_score * 0.7) + (result_count_factor * 0.3)
        
        return round(confidence, 2)
    
    async def close(self):
        """Close the Azure OpenAI client connection."""
        if hasattr(self.client, 'close'):
            await self.client.close()


# Global query processing service instance - initialized lazily
_query_processing_service = None

def get_query_processing_service() -> QueryProcessingService:
    """Get the global query processing service instance."""
    global _query_processing_service
    if _query_processing_service is None:
        _query_processing_service = QueryProcessingService()
    return _query_processing_service