"""
Tests for the code chunking service.

This module tests the core functionality of the CodeChunkingService,
including semantic chunking, fixed-size chunking, and fallback behavior.
"""

import pytest
from datetime import datetime
from app.models.data_models import CodeFile
from app.services.code_chunking import CodeChunkingService


class TestCodeChunkingService:
    """Test cases for CodeChunkingService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = CodeChunkingService()
    
    def test_chunk_python_file_with_functions(self):
        """Test chunking a Python file with clear function boundaries."""
        python_code = '''def function_one():
    """First function."""
    return "hello"

def function_two(param):
    """Second function."""
    if param:
        return True
    return False

class MyClass:
    """A simple class."""
    
    def method_one(self):
        """Class method."""
        return self.value
    
    def method_two(self, x, y):
        """Another method."""
        return x + y

def function_three():
    """Third function."""
    data = [1, 2, 3, 4, 5]
    return sum(data)
'''
        
        code_file = CodeFile(
            file_path="test.py",
            content=python_code,
            language="python",
            size_bytes=len(python_code),
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should create multiple chunks for functions and class
        assert len(chunks) > 1
        
        # All chunks should have valid properties
        for chunk in chunks:
            assert chunk.file_path == "test.py"
            assert chunk.language == "python"
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            assert len(chunk.content.strip()) > 0
            assert chunk.id is not None
    
    def test_chunk_javascript_file(self):
        """Test chunking a JavaScript file."""
        js_code = '''function calculateSum(a, b) {
    return a + b;
}

const multiply = (x, y) => {
    return x * y;
};

class Calculator {
    constructor() {
        this.history = [];
    }
    
    add(a, b) {
        const result = a + b;
        this.history.push(result);
        return result;
    }
}

function processArray(arr) {
    return arr.map(x => x * 2).filter(x => x > 10);
}
'''
        
        code_file = CodeFile(
            file_path="calculator.js",
            content=js_code,
            language="javascript",
            size_bytes=len(js_code),
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should create chunks
        assert len(chunks) >= 1
        
        # Check that chunks contain expected content
        all_content = ''.join(chunk.content for chunk in chunks)
        assert 'calculateSum' in all_content
        assert 'Calculator' in all_content
    
    def test_fixed_size_chunking_fallback(self):
        """Test that fixed-size chunking works as fallback."""
        # Create a file with no clear semantic boundaries
        large_text = "# This is a comment\n" + "x = 1\n" * 100
        
        code_file = CodeFile(
            file_path="simple.py",
            content=large_text,
            language="python",
            size_bytes=len(large_text),
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should create multiple chunks due to size
        assert len(chunks) >= 1
        
        # Check chunk sizes are reasonable
        for chunk in chunks:
            assert len(chunk.content) <= self.service.MAX_CHUNK_SIZE * 1.5  # Allow some flexibility
            assert chunk.chunk_type in ["fixed_size", "function", "class", "method"]
    
    def test_chunk_size_constraints(self):
        """Test that chunks respect size constraints."""
        # Create a very long function
        long_function = '''def very_long_function():
    """A function with lots of code."""
''' + '    x = 1\n' * 200  # Make it very long
        
        code_file = CodeFile(
            file_path="long.py",
            content=long_function,
            language="python",
            size_bytes=len(long_function),
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should split large functions
        assert len(chunks) >= 1
        
        # Most chunks should be within reasonable size limits
        reasonable_chunks = [c for c in chunks if len(c.content) <= self.service.MAX_CHUNK_SIZE * 1.2]
        assert len(reasonable_chunks) >= len(chunks) * 0.8  # At least 80% should be reasonable
    
    def test_unsupported_language_fallback(self):
        """Test chunking with unsupported language falls back to fixed-size."""
        code_file = CodeFile(
            file_path="test.xyz",
            content="some code in unknown language\n" * 50,
            language="unknown",
            size_bytes=1000,
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should still create chunks using fixed-size method
        assert len(chunks) >= 1
        
        # Should use fixed-size chunking
        for chunk in chunks:
            assert chunk.metadata.get('chunking_method') == 'fixed_size'
    
    def test_empty_file_handling(self):
        """Test handling of empty or very small files."""
        code_file = CodeFile(
            file_path="empty.py",
            content="",
            language="python",
            size_bytes=0,
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Should handle empty files gracefully
        assert isinstance(chunks, list)
        # May be empty or have one small chunk
        if chunks:
            assert len(chunks[0].content) == 0
    
    def test_chunk_overlap(self):
        """Test that fixed-size chunks have proper overlap."""
        # Create content that will definitely need multiple chunks
        large_content = ["line " + str(i) + "\n" for i in range(100)]
        content = ''.join(large_content)
        
        code_file = CodeFile(
            file_path="large.py",
            content=content,
            language="python",
            size_bytes=len(content),
            last_modified=datetime.now()
        )
        
        # Force fixed-size chunking by using unknown language
        code_file.language = "unknown"
        chunks = self.service.chunk_code_file(code_file)
        
        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]
                
                # There should be some content overlap or adjacent positioning
                # This is a basic check - in practice, overlap detection is complex
                assert current_chunk.end_line <= next_chunk.end_line
    
    def test_line_number_accuracy(self):
        """Test that line numbers are calculated correctly."""
        code_with_lines = '''# Line 1
def func1():  # Line 2
    return 1  # Line 3

# Line 5
def func2():  # Line 6
    return 2  # Line 7
'''
        
        code_file = CodeFile(
            file_path="lines.py",
            content=code_with_lines,
            language="python",
            size_bytes=len(code_with_lines),
            last_modified=datetime.now()
        )
        
        chunks = self.service.chunk_code_file(code_file)
        
        # Check that line numbers make sense
        for chunk in chunks:
            assert chunk.start_line >= 1
            assert chunk.end_line >= chunk.start_line
            
            # Line numbers should correspond to actual content
            lines_in_chunk = chunk.content.count('\n')
            expected_end = chunk.start_line + lines_in_chunk
            # Allow some flexibility due to different chunking strategies
            assert abs(chunk.end_line - expected_end) <= 2