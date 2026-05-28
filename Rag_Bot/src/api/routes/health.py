"""
Health check and system status endpoints
"""

import logging
from datetime import datetime

from fastapi import APIRouter

from api.models import HealthResponse, PingResponse
from api.dependencies import get_system_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/ping", response_model=PingResponse)
async def ping():
    """Simple ping endpoint to verify API is running"""
    return {
        "message": "pong",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health", response_model=HealthResponse)
async def health():
    """Get system health status"""
    status = get_system_status()
    
    return {
        "status": "healthy" if all([
            status["embedder_ready"],
            status["rag_chain_ready"],
        ]) else "degraded",
        "embedder_ready": status["embedder_ready"],
        "bm25_index_ready": status["bm25_ready"],
        "documents_count": status["documents_count"],
        "total_chunks": status["total_chunks"],
    }
