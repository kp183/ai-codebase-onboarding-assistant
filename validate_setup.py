#!/usr/bin/env python3
"""
Validation script to verify the project setup is correct.
"""

import os
import sys
from pathlib import Path

def validate_project_structure():
    """Validate that all required files and directories exist."""
    required_paths = [
        "app/__init__.py",
        "app/main.py",
        "app/config.py",
        "app/api/__init__.py",
        "app/api/chat.py",
        "app/api/health.py",
        "app/services/__init__.py",
        "app/models/__init__.py",
        "static/index.html",
        "static/style.css",
        "static/script.js",
        "tests/__init__.py",
        "tests/test_config.py",
        "tests/test_health.py",
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "README.md"
    ]
    
    missing_files = []
    for path in required_paths:
        if not Path(path).exists():
            missing_files.append(path)
    
    if missing_files:
        print("❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        return False
    else:
        print("✅ All required files and directories exist")
        return True

def validate_configuration():
    """Validate configuration can be loaded with test values."""
    try:
        # Set test environment variables
        os.environ.update({
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com/',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_SEARCH_ENDPOINT': 'https://test.search.windows.net',
            'AZURE_SEARCH_API_KEY': 'test-search-key'
        })
        
        from app.config import settings
        
        assert settings.app_name == "AI Codebase Onboarding Assistant"
        assert settings.azure_openai_endpoint == "https://test.openai.azure.com/"
        assert settings.azure_search_endpoint == "https://test.search.windows.net"
        
        print("✅ Configuration management working correctly")
        return True
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return False

def validate_fastapi_app():
    """Validate FastAPI application can be created."""
    try:
        from app.main import app
        
        # Check that app has the expected routes
        routes = [route.path for route in app.routes]
        expected_routes = ["/api/health", "/api/chat", "/api/predefined/where-to-start"]
        
        for expected_route in expected_routes:
            if not any(expected_route in route for route in routes):
                print(f"❌ Missing expected route: {expected_route}")
                return False
        
        print("✅ FastAPI application created successfully with expected routes")
        return True
    except Exception as e:
        print(f"❌ FastAPI application validation failed: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🔍 Validating AI Codebase Onboarding Assistant Setup...")
    print("=" * 60)
    
    checks = [
        ("Project Structure", validate_project_structure),
        ("Configuration Management", validate_configuration),
        ("FastAPI Application", validate_fastapi_app)
    ]
    
    all_passed = True
    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All validation checks passed! Project setup is complete.")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your Azure credentials")
        print("2. Run: python run_dev.py")
        print("3. Open: http://localhost:8000")
        return 0
    else:
        print("❌ Some validation checks failed. Please review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())