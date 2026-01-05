"""
Core data models for the AI Codebase Onboarding Assistant.

This module defines the essential Pydantic models used throughout the system
for representing code files, code chunks, and query responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CodeFile(BaseModel):
    """
    Represents a code file from a repository.
    
    Attributes:
        file_path: Relative path to the file within the repository
        content: Full text content of the file
        language: Programming language detected from file extension
        size_bytes: Size of the file in bytes
        last_modified: Timestamp when the file was last modified
    """
    file_path: str = Field(..., description="Relative path to the file within the repository")
    content: str = Field(..., description="Full text content of the file")
    language: str = Field(..., description="Programming language detected from file extension")
    size_bytes: int = Field(..., ge=0, description="Size of the file in bytes")
    last_modified: datetime = Field(..., description="Timestamp when the file was last modified")


class CodeChunk(BaseModel):
    """
    Represents a processed segment of code with metadata.
    
    Attributes:
        id: Unique identifier for the chunk
        file_path: Path to the source file
        content: Text content of the chunk
        start_line: Starting line number in the source file
        end_line: Ending line number in the source file
        language: Programming language of the chunk
        chunk_type: Type of code segment (function, class, module, other)
        metadata: Additional metadata about the chunk
    """
    id: str = Field(..., description="Unique identifier for the chunk")
    file_path: str = Field(..., description="Path to the source file")
    content: str = Field(..., description="Text content of the chunk")
    start_line: int = Field(..., ge=1, description="Starting line number in the source file")
    end_line: int = Field(..., ge=1, description="Ending line number in the source file")
    language: str = Field(..., description="Programming language of the chunk")
    chunk_type: str = Field(
        default="other", 
        description="Type of code segment (function, class, module, other)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Additional metadata about the chunk"
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that end_line >= start_line"""
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")


class SourceReference(BaseModel):
    """
    Represents a reference to a specific location in the codebase.
    
    Attributes:
        file_path: Path to the referenced file
        start_line: Starting line number of the reference
        end_line: Ending line number of the reference
        content_preview: Short preview of the referenced content
    """
    file_path: str = Field(..., description="Path to the referenced file")
    start_line: int = Field(..., ge=1, description="Starting line number of the reference")
    end_line: int = Field(..., ge=1, description="Ending line number of the reference")
    content_preview: str = Field(..., description="Short preview of the referenced content")

    def model_post_init(self, __context: Any) -> None:
        """Validate that end_line >= start_line"""
        if self.end_line < self.start_line:
            raise ValueError("end_line must be greater than or equal to start_line")


class QueryResponse(BaseModel):
    """
    Represents the response to a user query with grounded answers.
    
    Attributes:
        answer: The generated answer text
        sources: List of source references that ground the answer
        confidence_score: Confidence score for the response (0.0 to 1.0)
        processing_time_ms: Time taken to process the query in milliseconds
    """
    answer: str = Field(..., description="The generated answer text")
    sources: List[SourceReference] = Field(
        default_factory=list, 
        description="List of source references that ground the answer"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Confidence score for the response (0.0 to 1.0)"
    )
    processing_time_ms: int = Field(
        ..., 
        ge=0, 
        description="Time taken to process the query in milliseconds"
    )


class EmbeddedChunk(BaseModel):
    """
    Represents a code chunk with its vector embedding.
    
    Attributes:
        chunk: The original code chunk
        embedding: Vector embedding of the chunk content
        embedding_model: Name of the model used to generate the embedding
        created_at: Timestamp when the embedding was created
    """
    chunk: CodeChunk = Field(..., description="The original code chunk")
    embedding: List[float] = Field(..., description="Vector embedding of the chunk content")
    embedding_model: str = Field(..., description="Name of the model used to generate the embedding")
    created_at: datetime = Field(..., description="Timestamp when the embedding was created")


class IngestionResult(BaseModel):
    """
    Represents the result of a repository ingestion operation.
    
    Attributes:
        success: Whether the ingestion was successful
        file_count: Number of files processed
        message: Descriptive message about the result
        processed_files: List of file paths that were processed
        errors: List of error messages if any occurred
    """
    success: bool = Field(..., description="Whether the ingestion was successful")
    file_count: int = Field(..., ge=0, description="Number of files processed")
    message: str = Field(..., description="Descriptive message about the result")
    processed_files: List[str] = Field(
        default_factory=list, 
        description="List of file paths that were processed"
    )
    errors: List[str] = Field(
        default_factory=list, 
        description="List of error messages if any occurred"
    )