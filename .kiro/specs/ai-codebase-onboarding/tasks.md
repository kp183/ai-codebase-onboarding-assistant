# Implementation Plan: AI Codebase Onboarding Assistant (MVP Focus)

## Overview

This implementation plan focuses on delivering a working Imagine Cup MVP that demonstrates the core value proposition: helping developers understand codebases through AI-powered chat. The approach prioritizes the demo path over comprehensive testing, with optional enhancements clearly marked.

## Phase A: Core MVP Pipeline (MUST BUILD)

- [x] 1. Set up project structure and core dependencies
  - Create FastAPI project structure with basic organization
  - Set up Python virtual environment and install core dependencies (FastAPI, Azure SDK)
  - Configure environment variables for Azure OpenAI and Azure AI Search
  - Create basic configuration management
  - _Requirements: 7.1, 7.5_

- [x] 2. Implement core data models
  - [x] 2.1 Create essential data model classes
    - Define Pydantic models for CodeFile, CodeChunk, QueryResponse
    - Include required fields: file_path, content, start_line, end_line
    - _Requirements: 2.4, 4.5_

- [x] 3. Implement GitHub repository ingestion
  - [x] 3.1 Create simple repository fetching
    - Implement basic GitHub repository cloning or file fetching
    - Add file type filtering for common code files (.py, .js, .ts, .java)
    - Include basic error handling with user-friendly messages
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 4. Implement code chunking (simplified approach)
  - [x] 4.1 Create basic code chunking service
    - Start with simple function/class boundary detection using regex patterns
    - Implement fixed-size chunking with overlap as fallback
    - Target 500-1000 character chunks with 25% overlap
    - _Requirements: 2.1, 2.2_

- [x] 5. Implement Azure OpenAI embedding service
  - [x] 5.1 Create embedding service with Azure OpenAI
    - Implement embedding generation using text-embedding-3-small
    - Add basic batch processing and simple retry logic
    - Include file path and line number metadata
    - _Requirements: 2.3, 2.4_

- [x] 6. Implement Azure AI Search integration
  - [x] 6.1 Create search service with basic index
    - Implement Azure AI Search index creation with vector fields
    - Add methods for storing embeddings with metadata
    - _Requirements: 2.5, 3.1_

  - [x] 6.2 Implement vector similarity search
    - Add query embedding and similarity search methods
    - Return top 5 results with file references
    - Handle empty results gracefully
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

- [x] 7. Checkpoint - Test core pipeline
  - Verify ingestion → chunking → embedding → search works end-to-end

## Phase B: Chat Interface (DEMO CRITICAL)

- [x] 8. Implement query processing and chat service
  - [x] 8.1 Create chat processing pipeline
    - Implement query embedding, search, and context preparation
    - Add Azure OpenAI chat completion with grounding instructions
    - Format responses with answer text and source references
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 8.2 Implement "Where do I start?" predefined query
    - Create codebase overview generation with entry points
    - Add simple first task suggestion with file references
    - Make query work without additional user input
    - _Requirements: 5.2, 5.3, 5.4, 5.5_

- [x] 9. Implement FastAPI endpoints
  - [x] 9.1 Create essential API endpoints
    - Implement POST /chat endpoint with basic request/response models
    - Add GET /predefined/where-to-start endpoint
    - Include simple health check endpoint
    - _Requirements: 4.5, 5.1, 5.2_

- [x] 10. Implement simple web UI
  - [x] 10.1 Create basic chat interface
    - Build simple HTML/CSS/JavaScript chat interface
    - Add chat input, message history, and "Where do I start?" button
    - Include basic loading states and error messages
    - _Requirements: 6.1, 6.4, 6.5_

  - [x] 10.2 Display responses with source references
    - Show both answer text and file references clearly
    - Make file references copyable (clickable optional)
    - _Requirements: 6.2, 6.3_

- [x] 11. End-to-end integration and wiring
  - [x] 11.1 Wire all services together
    - Connect the complete pipeline: ingestion → chunking → embedding → search → chat
    - Add basic service initialization and startup checks
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 12. Final MVP validation
  - [x] 12.1 Test complete demo workflow
    - Verify end-to-end functionality with a sample repository
    - Test "Where do I start?" and custom questions
    - Ensure source references work correctly
    - _Requirements: 7.5_

## Phase C: Quality & Polish (TIME PERMITTING)

- [x] 13. Optional enhancements (only if time allows)
  - [x] 13.1 Add basic testing
    - Write 2-3 critical unit tests for core pipeline
    - Test error handling and edge cases
    - _Requirements: 7.4_

  - [x] 13.2 Improve chunking (upgrade path)
    - Consider adding tree-sitter for Python files only
    - Improve function/class boundary detection
    - _Requirements: 2.1, 2.2_

  - [x] 13.3 UI improvements
    - Add better styling and user experience
    - Improve error messages and loading states
    - _Requirements: 6.5, 7.4_

## Notes

**MVP Focus Strategy:**
- **Phase A (Core Pipeline)**: Must work for demo - this is your minimum viable product
- **Phase B (Chat Interface)**: Demo-critical features that judges will see
- **Phase C (Quality & Polish)**: Only if time allows - nice to have, not essential

**Key Principles:**
- Each task references specific requirements for traceability
- Checkpoints ensure the demo path works before adding complexity
- Simple implementations first, sophisticated features later
- Focus on user experience over engineering perfection
- Azure service configuration should be externalized to environment variables

**Competition Strategy:**
- Stop at Phase B if time is tight - you have a complete MVP
- Phase C enhancements can be mentioned as "future work" in presentations
- Judges value working demos over comprehensive test suites
- Keep the story simple: "AI helps developers understand codebases faster"