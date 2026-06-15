"""
Vercel serverless adapter for Observia FastAPI backend.
Exports the ASGI app for the Vercel Python runtime.
"""
import os
import sys

server_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "server"))
if server_path not in sys.path:
    sys.path.insert(0, server_path)

# Serverless: only /tmp is writable; use it for SQLite
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/observia.db")
os.environ.setdefault("SECRET_KEY", os.environ.get("SECRET_KEY", "change-me-in-production"))

from app.main import app  # noqa: E402
