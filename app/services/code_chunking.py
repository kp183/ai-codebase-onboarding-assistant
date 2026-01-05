"""
Code chunking service for processing code files into semantic chunks.

This module provides functionality to chunk code files into logical segments,
preserving function and class boundaries where possible, with fallback to
fixed-size chunking with overlap.
"""

import re
import uuid
from typing import List, Dict, Tuple, Optional
import logging

from app.models.data_models import CodeFile, CodeChunk

logger = logging.getLogger(__name__)


class CodeChunkingService:
    """
    Service for chunking code files into semantic segments.
    
    Uses regex patterns to detect function and class boundaries for intelligent
    chunking, with fallback to fixed-size chunking when semantic boundaries
    cannot be detected.
    """
    
    # Target chunk size in characters
    TARGET_CHUNK_SIZE: int = 750  # Middle of 500-1000 range
    MIN_CHUNK_SIZE: int = 500
    MAX_CHUNK_SIZE: int = 1000
    OVERLAP_PERCENTAGE: float = 0.25  # 25% overlap
    
    # Language-specific regex patterns for function and class detection
    LANGUAGE_PATTERNS: Dict[str, Dict[str, str]] = {
        'python': {
            'function': r'^(\s*)(def\s+\w+.*?:)',
            'class': r'^(\s*)(class\s+\w+.*?:)',
            'method': r'^(\s+)(def\s+\w+.*?:)'
        },
        'javascript': {
            'function': r'^(\s*)(function\s+\w+\s*\([^)]*\)\s*\{|const\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{|let\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{|var\s+\w+\s*=\s*\([^)]*\)\s*=>\s*\{)',
            'class': r'^(\s*)(class\s+\w+\s*(?:extends\s+\w+)?\s*\{)',
            'method': r'^(\s+)(\w+\s*\([^)]*\)\s*\{)'
        },
        'typescript': {
            'function': r'^(\s*)(function\s+\w+\s*\([^)]*\)\s*:\s*\w+\s*\{|const\s+\w+\s*=\s*\([^)]*\)\s*:\s*\w+\s*=>\s*\{)',
            'class': r'^(\s*)(class\s+\w+\s*(?:extends\s+\w+)?\s*\{|interface\s+\w+\s*\{)',
            'method': r'^(\s+)(\w+\s*\([^)]*\)\s*:\s*\w+\s*\{)'
        },
        'java': {
            'function': r'^(\s*)((?:public|private|protected|static|\s)+\w+\s+\w+\s*\([^)]*\)\s*\{)',
            'class': r'^(\s*)((?:public|private|protected|\s)*class\s+\w+\s*(?:extends\s+\w+)?\s*(?:implements\s+[\w,\s]+)?\s*\{)',
            'method': r'^(\s+)((?:public|private|protected|static|\s)+\w+\s+\w+\s*\([^)]*\)\s*\{)'
        },
        'cpp': {
            'function': r'^(\s*)(\w+\s+\w+\s*\([^)]*\)\s*\{)',
            'class': r'^(\s*)(class\s+\w+\s*(?::\s*(?:public|private|protected)\s+\w+)?\s*\{)',
            'method': r'^(\s+)(\w+\s+\w+\s*\([^)]*\)\s*\{)'
        },
        'c': {
            'function': r'^(\s*)(\w+\s+\w+\s*\([^)]*\)\s*\{)',
        },
        'csharp': {
            'function': r'^(\s*)((?:public|private|protected|static|\s)+\w+\s+\w+\s*\([^)]*\)\s*\{)',
            'class': r'^(\s*)((?:public|private|protected|\s)*class\s+\w+\s*(?::\s*\w+)?\s*\{)',
            'method': r'^(\s+)((?:public|private|protected|static|\s)+\w+\s+\w+\s*\([^)]*\)\s*\{)'
        },
        'go': {
            'function': r'^(\s*)(func\s+(?:\(\w+\s+\*?\w+\)\s+)?\w+\s*\([^)]*\)\s*(?:\([^)]*\))?\s*\{)',
            'struct': r'^(\s*)(type\s+\w+\s+struct\s*\{)',
            'method': r'^(\s*)(func\s+\(\w+\s+\*?\w+\)\s+\w+\s*\([^)]*\)\s*(?:\([^)]*\))?\s*\{)'
        },
        'rust': {
            'function': r'^(\s*)((?:pub\s+)?fn\s+\w+\s*\([^)]*\)\s*(?:->\s*\w+)?\s*\{)',
            'struct': r'^(\s*)((?:pub\s+)?struct\s+\w+\s*\{)',
            'impl': r'^(\s*)(impl\s+(?:<[^>]*>\s+)?\w+\s*(?:for\s+\w+)?\s*\{)'
        },
        'ruby': {
            'function': r'^(\s*)(def\s+\w+\s*(?:\([^)]*\))?)',
            'class': r'^(\s*)(class\s+\w+\s*(?:<\s*\w+)?)',
            'module': r'^(\s*)(module\s+\w+)'
        },
        'php': {
            'function': r'^(\s*)((?:public|private|protected|\s)*function\s+\w+\s*\([^)]*\)\s*\{)',
            'class': r'^(\s*)((?:abstract\s+|final\s+)?class\s+\w+\s*(?:extends\s+\w+)?\s*(?:implements\s+[\w,\s]+)?\s*\{)',
            'method': r'^(\s+)((?:public|private|protected|static|\s)*function\s+\w+\s*\([^)]*\)\s*\{)'
        }
    }
    
    def __init__(self):
        """Initialize the code chunking service."""
        pass
    
    def chunk_code_file(self, code_file: CodeFile) -> List[CodeChunk]:
        """
        Chunk a code file into semantic segments.
        
        Args:
            code_file: CodeFile object to chunk
            
        Returns:
            List of CodeChunk objects representing the file segments
        """
        try:
            logger.info(f"Chunking file: {code_file.file_path} ({code_file.language})")
            
            # Try semantic chunking first
            chunks = self._semantic_chunking(code_file)
            
            # If semantic chunking didn't produce good results, fall back to fixed-size
            if not chunks or self._needs_fixed_size_fallback(chunks, code_file.content):
                logger.info(f"Falling back to fixed-size chunking for {code_file.file_path}")
                chunks = self._fixed_size_chunking(code_file)
            
            logger.info(f"Created {len(chunks)} chunks for {code_file.file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error chunking file {code_file.file_path}: {e}")
            # Fallback to fixed-size chunking on any error
            return self._fixed_size_chunking(code_file)
    
    def _semantic_chunking(self, code_file: CodeFile) -> List[CodeChunk]:
        """
        Attempt to chunk code using semantic boundaries (functions, classes).
        
        Args:
            code_file: CodeFile to chunk semantically
            
        Returns:
            List of CodeChunk objects, empty if semantic chunking fails
        """
        language = code_file.language.lower()
        
        # Check if we have patterns for this language
        if language not in self.LANGUAGE_PATTERNS:
            logger.debug(f"No semantic patterns available for language: {language}")
            return []
        
        patterns = self.LANGUAGE_PATTERNS[language]
        lines = code_file.content.split('\n')
        
        # Find all semantic boundaries
        boundaries = self._find_semantic_boundaries(lines, patterns)
        
        if not boundaries:
            logger.debug(f"No semantic boundaries found in {code_file.file_path}")
            return []
        
        # Create chunks from boundaries
        chunks = []
        for i, (start_line, end_line, chunk_type) in enumerate(boundaries):
            chunk_content = '\n'.join(lines[start_line-1:end_line])
            
            # Skip very small chunks (likely incomplete detection)
            if len(chunk_content.strip()) < 20:
                continue
            
            # If chunk is too large, split it further
            if len(chunk_content) > self.MAX_CHUNK_SIZE:
                sub_chunks = self._split_large_chunk(
                    code_file, chunk_content, start_line, chunk_type
                )
                chunks.extend(sub_chunks)
            else:
                chunk = CodeChunk(
                    id=str(uuid.uuid4()),
                    file_path=code_file.file_path,
                    content=chunk_content,
                    start_line=start_line,
                    end_line=end_line,
                    language=code_file.language,
                    chunk_type=chunk_type,
                    metadata={
                        'chunking_method': 'semantic',
                        'original_file_size': code_file.size_bytes
                    }
                )
                chunks.append(chunk)
        
        return chunks
    
    def _find_semantic_boundaries(self, lines: List[str], patterns: Dict[str, str]) -> List[Tuple[int, int, str]]:
        """
        Find semantic boundaries (functions, classes) in code lines.
        
        Args:
            lines: List of code lines
            patterns: Dictionary of regex patterns for the language
            
        Returns:
            List of tuples (start_line, end_line, chunk_type)
        """
        boundaries = []
        
        for line_num, line in enumerate(lines, 1):
            # Check for semantic patterns
            for chunk_type, pattern in patterns.items():
                match = re.match(pattern, line, re.MULTILINE)
                if match:
                    # Find the end of this block by looking for the next function/class or end of file
                    end_line = self._find_block_end(lines, line_num - 1, len(match.group(1)))
                    boundaries.append((line_num, end_line, chunk_type))
                    break
        
        # Sort boundaries by start line before removing overlaps
        boundaries.sort(key=lambda x: x[0])
        
        # Remove overlapping boundaries (keep the first one)
        boundaries = self._remove_overlapping_boundaries(boundaries)
        
        return boundaries
    
    def _find_block_end(self, lines: List[str], start_line: int, base_indent: int) -> int:
        """
        Find the end line of a code block starting at start_line.
        
        Args:
            lines: List of code lines
            start_line: Starting line number (0-indexed)
            base_indent: Base indentation level of the block
            
        Returns:
            End line number (1-indexed)
        """
        current_line = start_line + 1  # Start from the line after the function/class declaration
        brace_count = 0
        found_opening_brace = False
        
        # Check if the starting line contains an opening brace
        if '{' in lines[start_line]:
            brace_count += lines[start_line].count('{')
            brace_count -= lines[start_line].count('}')
            found_opening_brace = True
        
        while current_line < len(lines):
            line = lines[current_line]
            
            # Count braces for languages that use them
            if '{' in line or '}' in line:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                found_opening_brace = True
                
                # If braces are balanced, we've found the end
                if found_opening_brace and brace_count == 0:
                    return current_line + 1  # Return 1-indexed line number
            
            # Skip empty lines and comments for indentation-based languages
            if not line.strip() or line.strip().startswith('#') or line.strip().startswith('//'):
                current_line += 1
                continue
            
            # For indentation-based languages (like Python), check indentation
            if not found_opening_brace:
                line_indent = len(line) - len(line.lstrip())
                
                # If we find a line with same or less indentation than base, we've reached the end
                if line_indent <= base_indent and line.strip():
                    return current_line  # Return 1-indexed line number
            
            current_line += 1
        
        # If we reach the end of file, return the last line
        return len(lines)
    
    def _remove_overlapping_boundaries(self, boundaries: List[Tuple[int, int, str]]) -> List[Tuple[int, int, str]]:
        """
        Remove overlapping boundaries, keeping the first occurrence.
        
        Args:
            boundaries: List of tuples (start_line, end_line, chunk_type)
            
        Returns:
            List of non-overlapping boundaries
        """
        if not boundaries:
            return []
        
        # Sort boundaries by start line
        sorted_boundaries = sorted(boundaries, key=lambda x: x[0])
        non_overlapping = [sorted_boundaries[0]]
        
        for current in sorted_boundaries[1:]:
            last_boundary = non_overlapping[-1]
            
            # If current boundary starts after the last one ends, it's not overlapping
            if current[0] > last_boundary[1]:
                non_overlapping.append(current)
            # If current boundary starts before the last one ends but is longer, replace it
            elif current[1] > last_boundary[1]:
                non_overlapping[-1] = current
            # Otherwise, skip the current boundary (it's contained within the last one)
        
        return non_overlapping
    
    def _is_block_end(self, lines: List[str], line_num: int, base_indent: int) -> bool:
        """
        Determine if we've reached the end of a code block.
        
        Args:
            lines: List of code lines
            line_num: Current line number (0-indexed)
            base_indent: Base indentation level of the block
            
        Returns:
            True if this appears to be the end of the block
        """
        # Look at the next few lines to confirm
        for i in range(line_num + 1, min(line_num + 3, len(lines))):
            if i < len(lines) and lines[i].strip():
                next_indent = len(lines[i]) - len(lines[i].lstrip())
                if next_indent > base_indent:
                    return False  # Still inside the block
        
        return True
    
    def _split_large_chunk(self, code_file: CodeFile, content: str, start_line: int, chunk_type: str) -> List[CodeChunk]:
        """
        Split a large semantic chunk into smaller fixed-size chunks.
        
        Args:
            code_file: Original code file
            content: Content of the large chunk
            start_line: Starting line number of the chunk
            chunk_type: Type of the semantic chunk
            
        Returns:
            List of smaller CodeChunk objects
        """
        chunks = []
        lines = content.split('\n')
        overlap_size = int(len(content) * self.OVERLAP_PERCENTAGE)
        
        current_pos = 0
        chunk_num = 0
        
        while current_pos < len(content):
            # Calculate chunk end position
            end_pos = min(current_pos + self.TARGET_CHUNK_SIZE, len(content))
            
            # Try to end at a line boundary
            chunk_content = content[current_pos:end_pos]
            if end_pos < len(content):
                last_newline = chunk_content.rfind('\n')
                if last_newline > len(chunk_content) // 2:  # Only if we're not cutting too much
                    end_pos = current_pos + last_newline + 1
                    chunk_content = content[current_pos:end_pos]
            
            # Calculate line numbers for this chunk
            lines_before = content[:current_pos].count('\n')
            lines_in_chunk = chunk_content.count('\n')
            chunk_start_line = start_line + lines_before
            chunk_end_line = chunk_start_line + lines_in_chunk
            
            chunk = CodeChunk(
                id=str(uuid.uuid4()),
                file_path=code_file.file_path,
                content=chunk_content,
                start_line=chunk_start_line,
                end_line=chunk_end_line,
                language=code_file.language,
                chunk_type=f"{chunk_type}_part_{chunk_num}",
                metadata={
                    'chunking_method': 'semantic_split',
                    'parent_chunk_type': chunk_type,
                    'part_number': chunk_num,
                    'original_file_size': code_file.size_bytes
                }
            )
            chunks.append(chunk)
            
            # Move to next position with overlap
            next_pos = end_pos - overlap_size
            if next_pos <= current_pos:  # Prevent infinite loop - ensure we make progress
                current_pos = end_pos  # Move to end if overlap would cause us to go backwards
            else:
                current_pos = next_pos
            
            # Safety check to prevent infinite loops
            if current_pos >= len(content):
                break
            
            chunk_num += 1
        
        return chunks
    
    def _fixed_size_chunking(self, code_file: CodeFile) -> List[CodeChunk]:
        """
        Chunk code using fixed-size approach with overlap.
        
        Args:
            code_file: CodeFile to chunk
            
        Returns:
            List of CodeChunk objects
        """
        content = code_file.content
        chunks = []
        overlap_size = int(self.TARGET_CHUNK_SIZE * self.OVERLAP_PERCENTAGE)
        
        current_pos = 0
        chunk_num = 0
        
        while current_pos < len(content):
            # Calculate chunk end position
            end_pos = min(current_pos + self.TARGET_CHUNK_SIZE, len(content))
            
            # Try to end at a line boundary to avoid cutting lines
            chunk_content = content[current_pos:end_pos]
            if end_pos < len(content):
                last_newline = chunk_content.rfind('\n')
                if last_newline > len(chunk_content) // 2:  # Only if we're not cutting too much
                    end_pos = current_pos + last_newline + 1
                    chunk_content = content[current_pos:end_pos]
            
            # Calculate line numbers
            lines_before = content[:current_pos].count('\n')
            lines_in_chunk = chunk_content.count('\n')
            start_line = lines_before + 1
            end_line = start_line + lines_in_chunk
            
            chunk = CodeChunk(
                id=str(uuid.uuid4()),
                file_path=code_file.file_path,
                content=chunk_content,
                start_line=start_line,
                end_line=end_line,
                language=code_file.language,
                chunk_type="fixed_size",
                metadata={
                    'chunking_method': 'fixed_size',
                    'chunk_number': chunk_num,
                    'overlap_size': overlap_size,
                    'original_file_size': code_file.size_bytes
                }
            )
            chunks.append(chunk)
            
            # Move to next position with overlap
            next_pos = end_pos - overlap_size
            if next_pos <= current_pos:  # Prevent infinite loop - ensure we make progress
                current_pos = end_pos  # Move to end if overlap would cause us to go backwards
            else:
                current_pos = next_pos
            
            # Safety check to prevent infinite loops
            if current_pos >= len(content):
                break
                
            chunk_num += 1
        
        return chunks
    
    def _needs_fixed_size_fallback(self, chunks: List[CodeChunk], original_content: str) -> bool:
        """
        Determine if semantic chunking results need fixed-size fallback.
        
        Args:
            chunks: List of chunks from semantic chunking
            original_content: Original file content
            
        Returns:
            True if fallback is needed
        """
        if not chunks:
            return True
        
        # Check if chunks cover most of the original content
        total_chunk_length = sum(len(chunk.content) for chunk in chunks)
        coverage_ratio = total_chunk_length / len(original_content)
        
        # If coverage is too low, use fixed-size fallback
        if coverage_ratio < 0.7:  # Less than 70% coverage
            return True
        
        # Check if chunks are reasonably sized
        oversized_chunks = [c for c in chunks if len(c.content) > self.MAX_CHUNK_SIZE * 1.5]
        if len(oversized_chunks) > len(chunks) * 0.3:  # More than 30% oversized
            return True
        
        return False


# Global service instance
chunking_service = CodeChunkingService()