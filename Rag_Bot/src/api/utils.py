"""
Utility functions for the RAG API
"""

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import json

from .config import UPLOAD_DIR, EXTRACTED_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE

logger = logging.getLogger(__name__)


# ============================================================================
# ── File Utilities ─────────────────────────────────────────────────────────
# ============================================================================

def generate_doc_id() -> str:
    """Generate a unique document ID"""
    return f"doc_{uuid.uuid4().hex[:12]}"


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is allowed"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def validate_upload_file(filename: str, file_size: int) -> Optional[str]:
    """
    Validate uploaded file.
    Returns error message if invalid, None if valid.
    """
    if not filename:
        return "Filename is empty"
    
    if not is_allowed_file(filename):
        allowed = ", ".join(ALLOWED_EXTENSIONS)
        return f"File type not allowed. Allowed: {allowed}"
    
    if file_size > MAX_FILE_SIZE:
        max_mb = MAX_FILE_SIZE / (1024 * 1024)
        return f"File too large. Maximum size: {max_mb}MB"
    
    return None


def get_file_path(filename: str, doc_id: str) -> Path:
    """Get the full path for a stored file"""
    return Path(UPLOAD_DIR) / doc_id / filename


def save_upload_file(file_content: bytes, filename: str, doc_id: str) -> Path:
    """Save uploaded file to disk"""
    file_path = get_file_path(filename, doc_id)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "wb") as f:
        f.write(file_content)
    
    logger.info(f"Saved file: {file_path}")
    return file_path


def save_extraction_result(extraction_data: dict, doc_id: str) -> Path:
    """Save extraction result as JSON to disk"""
    file_path = Path(EXTRACTED_DIR) / f"{doc_id}.json"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(extraction_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved extraction JSON: {file_path}")
    return file_path


def delete_document_files(doc_id: str):
    """Delete all files associated with a document"""
    # Delete uploaded source files
    doc_dir = Path(UPLOAD_DIR) / doc_id
    
    if doc_dir.exists():
        try:
            for file in doc_dir.glob("*"):
                file.unlink()
            doc_dir.rmdir()
            logger.info(f"Deleted document directory: {doc_dir}")
        except Exception as e:
            logger.error(f"Failed to delete document files: {e}")
            
    # Delete extraction JSON
    ext_file = Path(EXTRACTED_DIR) / f"{doc_id}.json"
    if ext_file.exists():
        try:
            ext_file.unlink()
            logger.info(f"Deleted extraction JSON: {ext_file}")
        except Exception as e:
            logger.error(f"Failed to delete extraction JSON: {e}")


# ============================================================================
# ── Document Utilities ─────────────────────────────────────────────────────
# ============================================================================

def create_document_metadata(
    doc_id: str,
    filename: str,
    pages: int,
    chunks_count: int,
    document_type: Optional[str] = None,
) -> dict:
    """Create metadata for a processed document"""
    return {
        "doc_id": doc_id,
        "file_name": filename,
        "pages": pages,
        "chunks_count": chunks_count,
        "created_at": datetime.utcnow().isoformat(),
        "document_type": document_type,
    }


# ============================================================================
# ── Chunk Utilities ────────────────────────────────────────────────────────
# ============================================================================

def format_chunk_for_response(chunk: dict, include_score: bool = True) -> dict:
    """Format chunk data for API response"""
    formatted = {
        "text": chunk.get("text", ""),
        "metadata": chunk.get("metadata", {}),
        "type": chunk.get("type", "text_block"),
    }
    
    if include_score and "score" in chunk:
        formatted["score"] = chunk["score"]
    
    return formatted


def merge_chunks_by_page(chunks: List[dict]) -> dict:
    """Group chunks by page number"""
    by_page = {}
    
    for chunk in chunks:
        page = chunk.get("metadata", {}).get("page", "unknown")
        if page not in by_page:
            by_page[page] = []
        by_page[page].append(chunk)
    
    return by_page


# ============================================================================
# ── Response Utilities ─────────────────────────────────────────────────────
# ============================================================================

def format_retrieval_results(
    query: str,
    answer: str,
    retrieved_chunks: List[dict],
    retrieval_mode: str,
    processing_time_ms: float,
    include_metadata: bool = True,
) -> dict:
    """Format retrieval results for API response"""
    chunks_response = []
    
    for chunk in retrieved_chunks:
        chunk_data = {
            "text": chunk.get("text", ""),
            "type": chunk.get("type", "text_block"),
        }
        
        if include_metadata:
            chunk_data["metadata"] = chunk.get("metadata", {})
        
        if "score" in chunk:
            chunk_data["score"] = round(chunk["score"], 4)
        
        chunks_response.append(chunk_data)
    
    return {
        "query": query,
        "answer": answer,
        "retrieved_chunks": chunks_response,
        "retrieval_mode": retrieval_mode,
        "chunks_count": len(chunks_response),
        "processing_time_ms": round(processing_time_ms, 2),
    }


# ============================================================================
# ── Error Utilities ────────────────────────────────────────────────────────
# ============================================================================

def create_error_response(error: str, detail: Optional[str] = None, status_code: int = 400) -> dict:
    """Create standardized error response"""
    return {
        "error": error,
        "detail": detail or "",
        "status_code": status_code,
    }


# ============================================================================
# ── Logging Utilities ──────────────────────────────────────────────────────
# ============================================================================

def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file}")


def log_request(method: str, path: str, params: dict):
    """Log incoming request"""
    logger.debug(f"{method} {path} - params: {params}")


def log_response(method: str, path: str, status_code: int, duration_ms: float):
    """Log outgoing response"""
    logger.debug(f"{method} {path} - status: {status_code} - duration: {duration_ms}ms")
