"""
API Models - Pydantic request/response schemas
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class RetrievalMode(str, Enum):
    """Retrieval mode options"""
    DENSE = "dense"
    HYBRID = "hybrid"


class LLMProvider(str, Enum):
    """LLM provider options"""
    GROQ = "groq"
    OLLAMA = "ollama"


class DocumentStatus(str, Enum):
    """Status of document processing"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentMetadata(BaseModel):
    """Metadata for a processed document"""
    file_name: str
    pages: int
    chunks_count: int
    created_at: str
    status: DocumentStatus = DocumentStatus.COMPLETED
    document_type: Optional[str] = None


class DocumentInfo(BaseModel):
    """Information about a document"""
    doc_id: str
    file_name: str
    pages: Optional[int] = 0
    chunks_count: Optional[int] = 0
    created_at: str
    status: DocumentStatus = DocumentStatus.COMPLETED
    document_type: Optional[str] = None


class QueryRequest(BaseModel):
    """Request model for document querying"""
    query: str = Field(..., description="Question or query string", min_length=1, max_length=1000)
    doc_id: Optional[str] = Field(None, description="Specific document ID to query. If None, searches all documents")
    doc_ids: Optional[List[str]] = Field(None, description="Optional list of document IDs to query. If provided, filters by these document IDs")
    top_k: int = Field(10, ge=1, le=100, description="Number of top results to retrieve")
    mode: RetrievalMode = Field(RetrievalMode.HYBRID, description="Retrieval mode: dense or hybrid")
    llm_provider: LLMProvider = Field(LLMProvider.OLLAMA, description="LLM provider: groq or ollama")
    include_metadata: bool = Field(True, description="Include metadata in retrieved chunks")


class ChunkData(BaseModel):
    """Retrieved chunk data"""
    text: str
    metadata: Dict[str, Any]
    type: str
    score: Optional[float] = None


class QueryResponse(BaseModel):
    """Response model for document queries"""
    answer: str
    retrieved_chunks: List[ChunkData]
    query: str
    retrieval_mode: str
    processing_time_ms: float


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    detail: Optional[str] = None
    status_code: int


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    embedder_ready: bool
    bm25_index_ready: bool
    documents_count: int
    total_chunks: int


class DocumentListResponse(BaseModel):
    """Response for listing documents"""
    documents: List[DocumentInfo]
    total: int


class DocumentDeleteResponse(BaseModel):
    """Response for document deletion"""
    message: str
    doc_id: str
    chunks_deleted: int


class PingResponse(BaseModel):
    """Simple ping response"""
    message: str
    timestamp: str
