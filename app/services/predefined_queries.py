"""
Predefined query service for common onboarding questions.

This service provides predefined queries that help new developers get oriented
in the codebase, including codebase overview and first task suggestions.
"""

import logging
from typing import List, Dict, Any
from openai import AsyncAzureOpenAI

from app.models.data_models import QueryResponse, SourceReference
from app.services.search_service import get_search_service, SearchResult
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class PredefinedQueryService:
    """
    Service for handling predefined onboarding queries.
    
    Provides structured responses to common questions that help developers
    understand codebase structure and get started with development tasks.
    """
    
    def __init__(self, client=None, chat_model=None):
        """
        Initialize the predefined query service.
        
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
    
    async def where_do_i_start(self) -> QueryResponse:
        """
        Generate a comprehensive "Where do I start?" response for new developers.
        
        This predefined query provides:
        1. Codebase overview and structure
        2. Entry points and main components
        3. Specific first task suggestion with file references
        
        Returns:
            QueryResponse with codebase overview and getting started guidance
            
        Raises:
            Exception: If query processing fails
        """
        try:
            logger.info("Processing 'Where do I start?' predefined query")
            
            # Get codebase overview by searching for common entry points and patterns
            overview_chunks = await self._get_codebase_overview()
            
            # Generate structured response with overview and first task
            answer = await self._generate_overview_response(overview_chunks)
            
            # Create source references from the overview chunks
            sources = [result.to_source_reference() for result in overview_chunks]
            
            response = QueryResponse(
                answer=answer,
                sources=sources,
                confidence_score=0.9,  # High confidence for predefined query
                processing_time_ms=0  # Will be set by caller
            )
            
            logger.info("Successfully generated 'Where do I start?' response")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process 'Where do I start?' query: {str(e)}")
            raise
    
    async def _get_codebase_overview(self) -> List[SearchResult]:
        """
        Retrieve code chunks that provide a good overview of the codebase.
        
        Searches for common entry points, main files, and architectural components
        to give new developers a comprehensive view of the system.
        
        Returns:
            List of search results representing key codebase components
        """
        try:
            # Define search queries for different aspects of the codebase
            overview_queries = [
                "main entry point application startup",
                "API endpoints routes controllers",
                "configuration settings environment",
                "data models database schemas",
                "core business logic services",
                "README documentation getting started"
            ]
            
            all_results = []
            
            # Search for each aspect and collect results
            for query in overview_queries:
                try:
                    query_embedding = await self.embedding_service.embed_single_text(query)
                    results = self.search_service.vector_search(
                        query_embedding=query_embedding,
                        top_k=3  # Get top 3 results for each query
                    )
                    all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Failed to search for '{query}': {str(e)}")
                    continue
            
            # Remove duplicates and sort by relevance
            unique_results = self._deduplicate_results(all_results)
            
            # Return top 8 most relevant results for overview
            return sorted(unique_results, key=lambda x: x.score, reverse=True)[:8]
            
        except Exception as e:
            logger.error(f"Failed to get codebase overview: {str(e)}")
            raise
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """
        Remove duplicate search results based on chunk ID.
        
        Args:
            results: List of search results that may contain duplicates
            
        Returns:
            List of unique search results
        """
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.chunk.id not in seen_ids:
                seen_ids.add(result.chunk.id)
                unique_results.append(result)
        
        return unique_results
    
    async def _generate_overview_response(self, overview_chunks: List[SearchResult]) -> str:
        """
        Generate a structured overview response using Azure OpenAI.
        
        Args:
            overview_chunks: Code chunks representing key codebase components
            
        Returns:
            Generated overview and getting started response
        """
        try:
            # Prepare context from overview chunks
            context = self._prepare_overview_context(overview_chunks)
            
            # Create specialized system prompt for overview generation
            system_prompt = self._create_overview_system_prompt()
            
            # Create user prompt for overview generation
            user_prompt = self._create_overview_user_prompt(context)
            
            # Generate response using Azure OpenAI
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,  # Slightly higher for more engaging overview
                max_tokens=1200,  # More tokens for comprehensive overview
                top_p=0.9
            )
            
            answer = response.choices[0].message.content.strip()
            logger.debug(f"Generated overview response of {len(answer)} characters")
            
            return answer
            
        except Exception as e:
            logger.error(f"Failed to generate overview response: {str(e)}")
            raise
    
    def _prepare_overview_context(self, search_results: List[SearchResult]) -> str:
        """
        Prepare context string optimized for codebase overview.
        
        Args:
            search_results: List of search results representing key components
            
        Returns:
            Formatted context string for overview generation
        """
        if not search_results:
            return "No code files found in the codebase."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            chunk = result.chunk
            context_part = f"""
Component {i}:
File: {chunk.file_path} (lines {chunk.start_line}-{chunk.end_line})
Language: {chunk.language}
Type: {chunk.chunk_type}

```{chunk.language}
{chunk.content}
```
"""
            context_parts.append(context_part.strip())
        
        return "\n\n".join(context_parts)
    
    def _create_overview_system_prompt(self) -> str:
        """
        Create system prompt specialized for codebase overview generation.
        
        Returns:
            System prompt for overview generation
        """
        return """You are an expert developer mentor helping a new team member understand a codebase. Your goal is to provide a comprehensive yet approachable overview that helps them get started quickly.

TASK: Generate a "Where do I start?" response that includes:

1. **CODEBASE OVERVIEW** (2-3 sentences)
   - What this application/system does
   - Main technology stack and architecture style

2. **KEY COMPONENTS** (bullet points)
   - Identify 3-4 most important directories/files
   - Briefly explain what each component does
   - Include specific file references

3. **ENTRY POINTS** (bullet points)
   - Where the application starts (main files, startup scripts)
   - Key configuration files
   - Important API endpoints or interfaces

4. **FIRST TASK RECOMMENDATION** (specific and actionable)
   - Suggest ONE specific file to examine first
   - Explain why this file is a good starting point
   - Mention what they should look for in that file

STYLE GUIDELINES:
- Be encouraging and welcoming
- Use clear, jargon-free language
- Focus on practical next steps
- Include specific file paths and line numbers
- Keep it concise but comprehensive
- Make it feel like advice from a helpful colleague

Base your response ONLY on the provided code context."""
    
    def _create_overview_user_prompt(self, context: str) -> str:
        """
        Create user prompt for overview generation.
        
        Args:
            context: Prepared context from search results
            
        Returns:
            User prompt for overview generation
        """
        return f"""Please analyze this codebase and provide a comprehensive "Where do I start?" response for a new developer joining the team.

Codebase Context:
{context}

Generate a welcoming, practical overview that helps them understand the system and know exactly where to begin exploring."""
    
    async def close(self):
        """Close the Azure OpenAI client connection."""
        if hasattr(self.client, 'close'):
            await self.client.close()


# Global predefined query service instance - initialized lazily
_predefined_query_service = None

def get_predefined_query_service() -> PredefinedQueryService:
    """Get the global predefined query service instance."""
    global _predefined_query_service
    if _predefined_query_service is None:
        _predefined_query_service = PredefinedQueryService()
    return _predefined_query_service