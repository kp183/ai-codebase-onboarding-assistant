"""
Tests for repository ingestion service.
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.repository_ingestion import RepositoryIngestionService
from app.models.data_models import CodeFile


class TestRepositoryIngestionService:
    """Test cases for RepositoryIngestionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.service = RepositoryIngestionService()
    
    def test_validate_file_type_supported_extensions(self):
        """Test that supported file extensions are correctly identified."""
        # Test supported extensions
        assert self.service.validate_file_type("test.py") is True
        assert self.service.validate_file_type("test.js") is True
        assert self.service.validate_file_type("test.ts") is True
        assert self.service.validate_file_type("test.java") is True
        assert self.service.validate_file_type("test.cpp") is True
        
        # Test unsupported extensions
        assert self.service.validate_file_type("test.txt") is False
        assert self.service.validate_file_type("test.md") is False
        assert self.service.validate_file_type("test.pdf") is False
        assert self.service.validate_file_type("README") is False
    
    def test_validate_file_type_case_insensitive(self):
        """Test that file type validation is case insensitive."""
        assert self.service.validate_file_type("test.PY") is True
        assert self.service.validate_file_type("test.JS") is True
        assert self.service.validate_file_type("Test.JAVA") is True
    
    def test_is_valid_github_url_valid_urls(self):
        """Test validation of valid GitHub URLs."""
        valid_urls = [
            "https://github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "https://www.github.com/owner/repo",
            "https://github.com/owner/repo-name",
            "https://github.com/owner-name/repo"
        ]
        
        for url in valid_urls:
            assert self.service._is_valid_github_url(url) is True
    
    def test_is_valid_github_url_invalid_urls(self):
        """Test validation of invalid GitHub URLs."""
        invalid_urls = [
            "https://gitlab.com/owner/repo",
            "https://bitbucket.org/owner/repo",
            "https://github.com/owner",  # Missing repo name
            "https://github.com/",
            "not-a-url",
            "ftp://github.com/owner/repo",
            ""
        ]
        
        for url in invalid_urls:
            assert self.service._is_valid_github_url(url) is False
    
    def test_detect_language(self):
        """Test programming language detection from file extensions."""
        test_cases = [
            ("test.py", "python"),
            ("test.js", "javascript"),
            ("test.jsx", "javascript"),
            ("test.ts", "typescript"),
            ("test.tsx", "typescript"),
            ("test.java", "java"),
            ("test.cpp", "cpp"),
            ("test.c", "c"),
            ("test.cs", "csharp"),
            ("test.go", "go"),
            ("test.rs", "rust"),
            ("test.rb", "ruby"),
            ("test.php", "php"),
            ("test.unknown", "unknown")
        ]
        
        for file_path, expected_language in test_cases:
            assert self.service._detect_language(file_path) == expected_language
    
    @pytest.mark.asyncio
    async def test_fetch_code_files_with_temp_directory(self):
        """Test fetching code files from a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            test_files = [
                ("test.py", "print('Hello, World!')"),
                ("test.js", "console.log('Hello, World!');"),
                ("README.md", "# Test Repository"),  # Should be ignored
                ("test.txt", "Plain text file")  # Should be ignored
            ]
            
            for filename, content in test_files:
                file_path = Path(temp_dir) / filename
                with open(file_path, 'w') as f:
                    f.write(content)
            
            # Fetch code files
            code_files = await self.service.fetch_code_files(temp_dir)
            
            # Should only return supported file types
            assert len(code_files) == 2
            
            # Check that we got the right files
            file_paths = [cf.file_path for cf in code_files]
            assert "test.py" in file_paths
            assert "test.js" in file_paths
            assert "README.md" not in file_paths
            assert "test.txt" not in file_paths
            
            # Check file content
            py_file = next(cf for cf in code_files if cf.file_path == "test.py")
            assert py_file.content == "print('Hello, World!')"
            assert py_file.language == "python"
            assert py_file.size_bytes > 0
    
    @pytest.mark.asyncio
    async def test_fetch_code_files_nonexistent_directory(self):
        """Test fetching code files from a nonexistent directory."""
        code_files = await self.service.fetch_code_files("/nonexistent/directory")
        assert len(code_files) == 0
    
    @pytest.mark.asyncio
    async def test_ingest_repository_invalid_url(self):
        """Test repository ingestion with invalid URL."""
        result = await self.service.ingest_repository("invalid-url")
        
        assert result.success is False
        assert result.file_count == 0
        assert "Invalid GitHub repository URL" in result.message
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_ingest_repository_valid_url_format(self):
        """Test repository ingestion with valid URL format but mock accessibility check."""
        with patch.object(self.service, '_check_repository_accessibility', return_value=False):
            result = await self.service.ingest_repository("https://github.com/owner/repo")
            
            assert result.success is False
            assert result.file_count == 0
            assert "not accessible" in result.message
    
    @pytest.mark.asyncio 
    async def test_check_repository_accessibility_success(self):
        """Test successful repository accessibility check."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            
            accessible = await self.service._check_repository_accessibility("https://github.com/owner/repo")
            assert accessible is True
    
    @pytest.mark.asyncio
    async def test_check_repository_accessibility_failure(self):
        """Test failed repository accessibility check."""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response
            
            accessible = await self.service._check_repository_accessibility("https://github.com/owner/nonexistent")
            assert accessible is False