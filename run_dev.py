#!/usr/bin/env python3
"""
Development server startup script for AI Codebase Onboarding Assistant.
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8002,
        reload=True,
        log_level=settings.log_level.lower()
    )