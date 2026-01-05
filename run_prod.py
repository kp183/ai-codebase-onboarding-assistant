#!/usr/bin/env python3
"""
Production server startup script for AI Codebase Onboarding Assistant.
NO RELOAD - Single process for MVP demo.
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=False,  # CRITICAL: No reload for singleton state
        log_level=settings.log_level.lower()
    )