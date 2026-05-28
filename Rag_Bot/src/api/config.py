"""
Configuration settings for the RAG API
"""

import os
from pathlib import Path
from typing import Optional

# Base directory (src/)
BASE_DIR = Path(__file__).resolve().parent.parent
# Project root (where chroma_db, uploads, etc. live in this setup)
PROJECT_ROOT = BASE_DIR


API_TITLE = "RAG Bot API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "Retrieval Augmented Generation API for PDF documents"

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]


# Upload directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(PROJECT_ROOT / "uploads"))
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)

# Extracted info directory (JSON)
EXTRACTED_DIR = os.getenv("EXTRACTED_DIR", str(PROJECT_ROOT / "extracted"))
Path(EXTRACTED_DIR).mkdir(parents=True, exist_ok=True)

# Allowed file types
ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


# ChromaDB persistence
CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", str(PROJECT_ROOT / "chroma_db"))
Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

# BM25 index persistence
BM25_INDEX_PATH = os.getenv("BM25_INDEX_PATH", str(PROJECT_ROOT / "bm25_index"))
Path(BM25_INDEX_PATH).mkdir(parents=True, exist_ok=True)

# Document metadata store
METADATA_STORE_PATH = os.getenv("METADATA_STORE_PATH", str(BASE_DIR / "metadata.json"))


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHROMA_COLLECTION_NAME = os.getenv("COLLECTION_NAME", "pdf-rag-documents")


# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Ollama configuration
OLLAMA_API_KEY = "ollama"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_GEN_MODEL = os.getenv("OLLAMA_GEN_MODEL", OLLAMA_MODEL)
CONTEXT_GEN_MODEL = os.getenv("CONTEXT_GEN_MODEL", "llama3.2:3b")
MAX_CONTEXTUAL_PARALLEL = int(os.getenv("MAX_CONTEXTUAL_PARALLEL", "4"))

LLM_MODEL = os.getenv("LLM_MODEL", OLLAMA_MODEL)
MAX_CONTEXT_CHARS = 8000  # ~2000 tokens

# Hybrid retrieval parameters
DEFAULT_TOP_K = 10
MAX_TOP_K = 40
RRF_K_PARAMETER = 60  # Reciprocal Rank Fusion parameter
DENSE_WEIGHT = 0.3  # Give more weight to BM25 for keyword/date matching


CHUNK_TABLE_STRATEGY = "auto"  # "sentence", "raw_json", "auto"
CHUNK_MERGE_THRESHOLD = 300  # Max chars for small chunk merging


# Max workers for background tasks
MAX_WORKERS = os.getenv("MAX_WORKERS", "4")

# Request timeout (seconds)
REQUEST_TIMEOUT = 60

# Log level
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(PROJECT_ROOT / "logs" / "api.log"))
Path(PROJECT_ROOT / "logs").mkdir(parents=True, exist_ok=True)

# Tesseract OCR path
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r'C:\Users\Abhishek Tripathi\AppData\Local\Programs\Tesseract-OCR\tesseract.exe')

def validate_config():
    """Validate critical configuration settings"""
    errors = []
    
    if not os.path.isdir(UPLOAD_DIR):
        errors.append(f"UPLOAD_DIR does not exist: {UPLOAD_DIR}")
    
    return errors


if __name__ == "__main__":
    print("RAG API Configuration Loaded:")
    print(f"  - API: {API_TITLE} v{API_VERSION}")
    print(f"  - Embedding Model: {EMBEDDING_MODEL}")
    print(f"  - LLM Model: {LLM_MODEL}")
    print(f"  - ChromaDB Path: {CHROMA_DB_PATH}")
    print(f"  - Upload Dir: {UPLOAD_DIR}")
    
    errors = validate_config()
    if errors:
        print("\nConfiguration Warnings:")
        for error in errors:
            print(f"  ⚠️  {error}")
    else:
        print("\n✅ Configuration valid")
