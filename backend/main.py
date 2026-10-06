"""
main.py – FastAPI application for CultureLens.

This is the entry point. It:
  1. Creates the FastAPI app with metadata.
  2. Sets up CORS so the frontend works from any origin.
  3. Mounts the frontend directory as static files.
  4. Loads the NLP engine once at startup via lifespan.
  5. Defines routes that delegate to service.py.
  6. Adds basic request logging and error handling.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION, FRONTEND_DIR
from backend.schemas import AnalyzeRequest
from backend.service import get_all_cultures, get_examples, get_health, run_analysis

# ── Logging setup ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load the NLP engine once at startup, not per request."""
    from nlp_engine.pipeline import init_engine

    logger.info("=== CultureLens starting up ===")
    init_engine()
    logger.info("Server ready at http://localhost:8000")
    yield
    logger.info("=== CultureLens shutting down ===")


# ── App creation ───────────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
)

# CORS – allow all origins so the frontend also works if opened as a
# file:// or from a different port during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve CSS and JS from frontend/ at /static
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


# ── Request logging middleware ─────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    elapsed = (time.perf_counter() - t0) * 1000
    # Only log API requests (not static files) to keep logs clean
    if request.url.path.startswith("/api"):
        logger.info("%s %s → %d (%.0f ms)",
                     request.method, request.url.path,
                     response.status_code, elapsed)
    return response


# ── Exception handlers ─────────────────────────────────────────────
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc,
                 exc_info=True)
    return JSONResponse(status_code=500,
                        content={"detail": "Internal server error."})


# ── Routes ─────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the single-page frontend."""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/api/health", summary="Health check")
async def health_check():
    """Returns system status and which NLP layers are active."""
    return get_health()


@app.get("/api/cultures", summary="List cultures")
async def cultures():
    """Returns all culture profiles for the UI dropdowns."""
    return get_all_cultures()


@app.post("/api/analyze", summary="Analyze text")
async def analyze(request: AnalyzeRequest):
    """Analyze text for cross-cultural communication risks."""
    return run_analysis(request)


@app.get("/api/examples", summary="Demo examples")
async def examples():
    """Returns pre-built demo messages."""
    return get_examples()
