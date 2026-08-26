"""
Vercel serverless entry point for the RAG System API.

Vercel automatically maps all /api/* requests to this file.
The HTTP middleware below strips the /api prefix so FastAPI's existing
routes (/status, /query, /ingest) match unchanged — no route modifications
needed in app/main.py.

Local development: run uvicorn directly against app.main:app as usual.
"""
import os
import sys

# Ensure the project root is on sys.path so `from app.*` imports resolve
# correctly regardless of how Vercel sets up the Python environment.
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app  # noqa: E402, F401 — Vercel uses `app` as the ASGI handler


@app.middleware("http")
async def _strip_api_prefix(request, call_next):
    """
    Strip the /api prefix Vercel prepends before delegating to FastAPI.

    Example: Vercel receives GET /api/status  →  FastAPI sees GET /status
    """
    path: str = request.scope.get("path", "")
    if path.startswith("/api"):
        stripped = path[4:] or "/"
        request.scope["path"] = stripped
        request.scope["raw_path"] = stripped.encode()
    return await call_next(request)
