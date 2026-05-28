"""
RAG Bot API - Main FastAPI Application

A REST API for Retrieval Augmented Generation over PDF documents.

Usage:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Environment Variables:
    - OPENAI_API_KEY: OpenAI API key (required)
    - EMBEDDING_MODEL: Embedding model name (default: all-MiniLM-L6-v2)
    - LLM_MODEL: LLM model name (default: gpt-4o-mini)
    - CHROMA_DB_PATH: Path to ChromaDB (default: ./chroma_db)
    - UPLOAD_DIR: Upload directory (default: ./uploads)
"""

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from dotenv import load_dotenv
load_dotenv()

from api.config import (
    API_TITLE,
    API_VERSION,
    API_DESCRIPTION,
    CORS_ORIGINS,
    LOG_LEVEL,
    LOG_FILE,
)
from api.dependencies import initialize_all, shutdown_all
from api.utils import setup_logging
from api.routes import health, documents, retrieval

# ── Setup Logging ──────────────────────────────────────────────────────────

setup_logging(log_level=LOG_LEVEL, log_file=LOG_FILE)
logger = logging.getLogger(__name__)


# ============================================================================
# ── Startup & Shutdown ─────────────────────────────────────────────────────
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown
    """
    # Startup
    logger.info("=" * 70)
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info("=" * 70)
    
    success = initialize_all()
    if not success:
        logger.error("Failed to initialize RAG system")
        raise RuntimeError("Failed to initialize RAG system")
    
    logger.info("Application started successfully")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("=" * 70)
    logger.info("Shutting down application...")
    logger.info("=" * 70)
    
    shutdown_all()
    
    logger.info("Application shut down successfully")


# ============================================================================
# ── Create FastAPI Application ────────────────────────────────────────────
# ============================================================================

app = FastAPI(
    title=API_TITLE,
    version=API_VERSION,
    description=API_DESCRIPTION,
    lifespan=lifespan,
)

# ============================================================================
# ── CORS Middleware ───────────────────────────────────────────────────────
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ── Request/Response Middleware ───────────────────────────────────────────
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses"""
    method = request.method
    path = request.url.path
    
    logger.debug(f"→ {method} {path}")
    
    try:
        response = await call_next(request)
        logger.debug(f"← {method} {path} - {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Error {method} {path} - {str(e)}")
        raise


# ============================================================================
# ── Exception Handlers ────────────────────────────────────────────────────
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP Error",
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred",
            "status_code": 500,
        },
    )


# ============================================================================
# ── Include Routers ───────────────────────────────────────────────────────
# ============================================================================

# Health check endpoints
app.include_router(health.router)

# Document management endpoints
app.include_router(documents.router)

# Query and retrieval endpoints
app.include_router(retrieval.router)


# ============================================================================
# ── Root Endpoint ────────────────────────────────────────────────────────
# ============================================================================

@app.get("/", tags=["info"])
async def root():
    """
    Root endpoint - API information
    """
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "description": API_DESCRIPTION,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


# ============================================================================
# ── Custom OpenAPI Schema ────────────────────────────────────────────────
# ============================================================================

def custom_openapi():
    """Customize OpenAPI schema"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=API_TITLE,
        version=API_VERSION,
        description=API_DESCRIPTION,
        routes=app.routes,
    )
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Local development server",
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# ============================================================================
# ── Application Entry Point ──────────────────────────────────────────────
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting RAG Bot API server...")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=LOG_LEVEL.lower(),
    )
