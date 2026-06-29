#!/usr/bin/env python3
"""
Health check endpoint for Cloud Run
"""
import os
import sys
import json
from pathlib import Path

def check_environment():
    """Check required environment variables and dependencies"""
    checks = {
        "python_version": sys.version.split()[0],
        "environment": {},
        "dependencies": {},
        "directories": {},
        "status": "healthy"
    }
    
    # Check environment variables
    required_env = ["GOOGLE_CLOUD_PROJECT", "SARVAM_API_KEY"]
    for var in required_env:
        value = os.getenv(var)
        checks["environment"][var] = "set" if value else "missing"
        if not value:
            checks["status"] = "degraded"
    
    # Check critical dependencies
    deps = [
        "google.adk",
        "google.cloud.aiplatform",
        "google.cloud.storage",
        "google.auth",
        "googleapiclient.discovery",
        "fastapi",
        "uvicorn",
        "manim",
        "ffmpeg",
    ]
    
    for dep in deps:
        try:
            __import__(dep.replace("-", "_"))
            checks["dependencies"][dep] = "ok"
        except ImportError:
            checks["dependencies"][dep] = "missing"
            checks["status"] = "unhealthy"
    
    # Check directories
    dirs = ["/app/output", "/app/storyboards", "/app/logs"]
    for d in dirs:
        path = Path(d)
        checks["directories"][d] = "ok" if path.exists() else "missing"
        if not path.exists():
            checks["status"] = "degraded"
    
    return checks


if __name__ == "__main__":
    result = check_environment()
    print(json.dumps(result, indent=2))
    
    if result["status"] == "unhealthy":
        sys.exit(1)
    elif result["status"] == "degraded":
        sys.exit(0)  # Still pass for degraded
    else:
        sys.exit(0)