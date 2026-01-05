#!/usr/bin/env python3
"""Quick test for code chunking service."""

from app.services.code_chunking import CodeChunkingService
from app.models.data_models import CodeFile
from datetime import datetime

def test_basic_chunking():
    """Test basic chunking functionality."""
    service = CodeChunkingService()
    
    # Test Python code
    python_code = '''def function_one():
    """First function."""
    return "hello"

def function_two():
    """Second function."""
    return "world"

class MyClass:
    def method(self):
        return 42
'''
    
    code_file = CodeFile(
        file_path="test.py",
        content=python_code,
        language="python",
        size_bytes=len(python_code),
        last_modified=datetime.now()
    )
    
    chunks = service.chunk_code_file(code_file)
    
    print(f"✓ Created {len(chunks)} chunks for Python file")
    
    for i, chunk in enumerate(chunks):
        print(f"  Chunk {i+1}: lines {chunk.start_line}-{chunk.end_line}, type: {chunk.chunk_type}")
        print(f"    Content preview: {chunk.content[:50].replace(chr(10), ' ')}...")
    
    # Test fixed-size chunking
    large_content = "# Comment line\n" * 100
    large_file = CodeFile(
        file_path="large.py",
        content=large_content,
        language="unknown",  # Force fixed-size chunking
        size_bytes=len(large_content),
        last_modified=datetime.now()
    )
    
    large_chunks = service.chunk_code_file(large_file)
    print(f"✓ Created {len(large_chunks)} chunks for large file (fixed-size)")
    
    return True

if __name__ == "__main__":
    try:
        test_basic_chunking()
        print("✓ All tests passed!")
    except Exception as e:
        print(f"✗ Test failed: {e}")
        import traceback
        traceback.print_exc()