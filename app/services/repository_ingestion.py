"""
Repository ingestion service for fetching and processing GitHub repositories.

This module provides functionality to fetch code files from GitHub repositories,
filter by supported file types, and handle errors gracefully.
"""

import os
import tempfile
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Set, Optional
from urllib.parse import urlparse
import logging

import git
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError

from app.models.data_models import CodeFile, IngestionResult

logger = logging.getLogger(__name__)


class RepositoryIngestionService:
    """
    Service for ingesting GitHub repositories and extracting code files.
    
    Supports fetching repositories via Git clone and filtering files by type.
    Provides comprehensive error handling for various failure scenarios.
    """
    
    # Supported code file extensions
    SUPPORTED_EXTENSIONS: Set[str] = {
        '.py', '.js', '.ts', '.java', '.cpp', '.c', '.cs', 
        '.go', '.rs', '.rb', '.php', '.jsx', '.tsx', '.kt',
        '.swift', '.scala', '.clj', '.hs', '.ml', '.fs'
    }
    
    # Maximum file size in bytes (1MB)
    MAX_FILE_SIZE: int = 1024 * 1024
    
    # Timeout for Git operations in seconds
    GIT_TIMEOUT: int = 300  # 5 minutes
    
    def __init__(self):
        """Initialize the repository ingestion service."""
        self._temp_dir: Optional[str] = None
    
    async def ingest_repository(self, repo_url: str) -> IngestionResult:
        """
        Ingest a GitHub repository and extract all supported code files.
        
        Args:
            repo_url: GitHub repository URL (https://github.com/owner/repo)
            
        Returns:
            IngestionResult with success status, file count, and any errors
            
        Raises:
            ValueError: If the repository URL is invalid
        """
        try:
            # Validate repository URL
            if not self._is_valid_github_url(repo_url):
                return IngestionResult(
                    success=False,
                    file_count=0,
                    message="Invalid GitHub repository URL. Please provide a valid GitHub URL.",
                    errors=["Invalid repository URL format"]
                )
            
            # Check if repository is accessible
            if not await self._check_repository_accessibility(repo_url):
                return IngestionResult(
                    success=False,
                    file_count=0,
                    message="Repository is not accessible. Please check the URL and ensure the repository is public.",
                    errors=["Repository not accessible"]
                )
            
            # Clone repository and extract files
            code_files = await self._clone_and_extract_files(repo_url)
            
            if not code_files:
                return IngestionResult(
                    success=True,
                    file_count=0,
                    message="Repository ingested successfully, but no supported code files were found.",
                    processed_files=[]
                )
            
            # Store files for later processing (in a real implementation, 
            # this would integrate with the chunking and embedding services)
            processed_file_paths = [file.file_path for file in code_files]
            
            return IngestionResult(
                success=True,
                file_count=len(code_files),
                message=f"Successfully ingested {len(code_files)} code files from repository.",
                processed_files=processed_file_paths
            )
            
        except git.exc.GitCommandError as e:
            logger.error(f"Git command failed: {e}")
            return IngestionResult(
                success=False,
                file_count=0,
                message="Failed to clone repository. The repository may be private or the URL may be incorrect.",
                errors=[f"Git error: {str(e)}"]
            )
            
        except Exception as e:
            logger.error(f"Unexpected error during repository ingestion: {e}")
            return IngestionResult(
                success=False,
                file_count=0,
                message="An unexpected error occurred during repository ingestion. Please try again.",
                errors=[f"Unexpected error: {str(e)}"]
            )
        
        finally:
            # Clean up temporary directory
            self._cleanup_temp_directory()
    
    async def fetch_code_files(self, repo_path: str) -> List[CodeFile]:
        """
        Extract and filter code files from a local repository path.
        
        Args:
            repo_path: Path to the local repository directory
            
        Returns:
            List of CodeFile objects for supported file types
        """
        code_files: List[CodeFile] = []
        repo_path_obj = Path(repo_path)
        
        if not repo_path_obj.exists():
            logger.warning(f"Repository path does not exist: {repo_path}")
            return code_files
        
        try:
            # Walk through all files in the repository
            for file_path in repo_path_obj.rglob('*'):
                if file_path.is_file() and self.validate_file_type(str(file_path)):
                    try:
                        # Skip files that are too large
                        if file_path.stat().st_size > self.MAX_FILE_SIZE:
                            logger.warning(f"Skipping large file: {file_path} ({file_path.stat().st_size} bytes)")
                            continue
                        
                        # Read file content
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        
                        # Create relative path from repository root
                        relative_path = file_path.relative_to(repo_path_obj)
                        
                        # Detect language from file extension
                        language = self._detect_language(str(file_path))
                        
                        # Get file modification time
                        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                        
                        code_file = CodeFile(
                            file_path=str(relative_path),
                            content=content,
                            language=language,
                            size_bytes=file_path.stat().st_size,
                            last_modified=last_modified
                        )
                        
                        code_files.append(code_file)
                        
                    except (UnicodeDecodeError, PermissionError) as e:
                        logger.warning(f"Could not read file {file_path}: {e}")
                        continue
                        
        except Exception as e:
            logger.error(f"Error processing repository files: {e}")
            raise
        
        logger.info(f"Extracted {len(code_files)} code files from repository")
        return code_files
    
    def validate_file_type(self, file_path: str) -> bool:
        """
        Check if a file type is supported for processing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file type is supported, False otherwise
        """
        file_extension = Path(file_path).suffix.lower()
        return file_extension in self.SUPPORTED_EXTENSIONS
    
    def _is_valid_github_url(self, url: str) -> bool:
        """
        Validate if the provided URL is a valid GitHub repository URL.
        
        Args:
            url: Repository URL to validate
            
        Returns:
            True if valid GitHub URL, False otherwise
        """
        try:
            parsed = urlparse(url)
            
            # Check if it uses HTTPS protocol
            if parsed.scheme.lower() != 'https':
                return False
            
            # Check if it's a GitHub URL
            if parsed.netloc.lower() not in ['github.com', 'www.github.com']:
                return False
            
            # Check if path has the expected format: /owner/repo
            path_parts = [part for part in parsed.path.split('/') if part]
            if len(path_parts) < 2:
                return False
            
            return True
            
        except Exception:
            return False
    
    async def _check_repository_accessibility(self, repo_url: str) -> bool:
        """
        Check if the repository is accessible via HTTP request.
        
        Args:
            repo_url: Repository URL to check
            
        Returns:
            True if accessible, False otherwise
        """
        try:
            # Convert to API URL to check accessibility
            parsed = urlparse(repo_url)
            path_parts = [part for part in parsed.path.split('/') if part]
            
            if len(path_parts) >= 2:
                owner, repo = path_parts[0], path_parts[1]
                # Remove .git suffix if present
                if repo.endswith('.git'):
                    repo = repo[:-4]
                
                api_url = f"https://api.github.com/repos/{owner}/{repo}"
                
                response = requests.get(api_url, timeout=10)
                return response.status_code == 200
            
            return False
            
        except (RequestException, Timeout, ConnectionError) as e:
            logger.warning(f"Could not check repository accessibility: {e}")
            return False
    
    async def _clone_and_extract_files(self, repo_url: str) -> List[CodeFile]:
        """
        Clone the repository and extract code files.
        
        Args:
            repo_url: Repository URL to clone
            
        Returns:
            List of extracted CodeFile objects
        """
        # Create temporary directory for cloning
        self._temp_dir = tempfile.mkdtemp(prefix="repo_ingestion_")
        
        try:
            logger.info(f"Cloning repository: {repo_url}")
            
            # Clone repository with timeout
            repo = git.Repo.clone_from(
                repo_url, 
                self._temp_dir,
                depth=1,  # Shallow clone for faster operation
                timeout=self.GIT_TIMEOUT
            )
            
            logger.info(f"Repository cloned to: {self._temp_dir}")
            
            # Extract code files
            code_files = await self.fetch_code_files(self._temp_dir)
            
            return code_files
            
        except git.exc.GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            raise
    
    def _detect_language(self, file_path: str) -> str:
        """
        Detect programming language from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Programming language name
        """
        extension = Path(file_path).suffix.lower()
        
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.kt': 'kotlin',
            '.swift': 'swift',
            '.scala': 'scala',
            '.clj': 'clojure',
            '.hs': 'haskell',
            '.ml': 'ocaml',
            '.fs': 'fsharp'
        }
        
        return language_map.get(extension, 'unknown')
    
    def _cleanup_temp_directory(self):
        """Clean up temporary directory used for cloning."""
        if self._temp_dir and os.path.exists(self._temp_dir):
            try:
                shutil.rmtree(self._temp_dir)
                logger.info(f"Cleaned up temporary directory: {self._temp_dir}")
            except Exception as e:
                logger.warning(f"Could not clean up temporary directory {self._temp_dir}: {e}")
            finally:
                self._temp_dir = None


# Global service instance
repository_service = RepositoryIngestionService()