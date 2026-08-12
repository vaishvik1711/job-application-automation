"""
Root-level entry point for Railway deployment.
Railpack auto-detects 'uvicorn main:app' as the start command, so this file
imports the FastAPI app from the backend directory.
"""
import sys
import os

# Add the backend directory to the Python path so imports work
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from api.main import app  # noqa: E402
