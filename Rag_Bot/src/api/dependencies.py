"""
Dependency injection - Singleton instances of RAG components
"""

import logging
from typing import Optional, Any, List
import json
from pathlib import Path

# pyrefly: ignore [missing-import]
from embeddings.embedder import ChunkEmbedder
# pyrefly: ignore [missing-import]
from extraction.bm25_index import BM25Index
# pyrefly: ignore [missing-import]
from extraction.hybrid_retriever import HybridRetriever
# pyrefly: ignore [missing-import]
from rag.chain import RAGChain

from .config import (
    CHROMA_DB_PATH,
    BM25_INDEX_PATH,
    EMBEDDING_MODEL,
    CHROMA_COLLECTION_NAME,
    LLM_MODEL,
    GROQ_API_KEY,
    GROQ_BASE_URL,
    METADATA_STORE_PATH,
    EXTRACTED_DIR,
)

logger = logging.getLogger(__name__)

# ============================================================================
# ── Global Instances (Singletons) ─────────────────────────────────────────
# ============================================================================

_embedder: Optional[ChunkEmbedder] = None
_bm25_index: Optional[BM25Index] = None
_retriever: Optional[HybridRetriever] = None
_rag_chain: Optional[RAGChain] = None
_contextualizer: Optional[Any] = None
_document_metadata: dict = {}


def get_contextualizer() -> Any:
    """Get or create the local contextualizer instance"""
    global _contextualizer
    
    if _contextualizer is None:
        # pyrefly: ignore [missing-import]
        from preprocessing.contextualizer import LocalContextualizer
        from .config import OLLAMA_BASE_URL, CONTEXT_GEN_MODEL, MAX_CONTEXTUAL_PARALLEL
        
        logger.info(f"Initializing LocalContextualizer with model: {CONTEXT_GEN_MODEL}")
        _contextualizer = LocalContextualizer(
            base_url=OLLAMA_BASE_URL,
            model=CONTEXT_GEN_MODEL,
            max_parallel=MAX_CONTEXTUAL_PARALLEL
        )
        
    return _contextualizer


def get_embedder() -> ChunkEmbedder:
    """Get or create the embedder instance"""
    global _embedder
    
    if _embedder is None:
        logger.info(f"Initializing ChunkEmbedder with model: {EMBEDDING_MODEL}")
        _embedder = ChunkEmbedder(
            collection_name=CHROMA_COLLECTION_NAME,
            model_name=EMBEDDING_MODEL,
            persist_directory=CHROMA_DB_PATH,
        )
        logger.info("ChunkEmbedder initialized successfully")
    
    return _embedder


def get_bm25_index() -> BM25Index:
    """Get or create the BM25 index instance"""
    global _bm25_index
    
    if _bm25_index is None:
        logger.info("Initializing BM25Index")
        _bm25_index = BM25Index()
        
        # Try to load from disk if it exists
        index_file = Path(BM25_INDEX_PATH) / "index.pkl"
        if index_file.exists():
            logger.info(f"Loading BM25 index from {index_file}")
            try:
                _bm25_index.load(str(index_file))
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}")
        else:
            logger.info("No existing BM25 index found")
        
        logger.info("BM25Index initialized successfully")
    
    return _bm25_index


def add_chunks_to_bm25(new_chunks: List[dict]):
    """Add new chunks to the existing BM25 index incrementally"""
    global _bm25_index
    
    logger.info(f"Adding {len(new_chunks)} chunks to BM25 index...")
    bm25 = get_bm25_index()
    
    # Combine existing chunks with new ones
    all_chunks = bm25.chunks + new_chunks
    
    # Re-build and save
    bm25.build(all_chunks)
    index_file = Path(BM25_INDEX_PATH) / "index.pkl"
    bm25.save(str(index_file))
    logger.info("BM25 index updated successfully")


def rebuild_bm25_index():
    """Rebuild the BM25 index from all processed documents (Full Recovery)"""
    global _bm25_index
    
    logger.info("Performing FULL rebuild of BM25 index from Vector Store...")
    
    # Get metadata for all documents
    metadata_store = get_document_metadata()
    if not metadata_store:
        logger.info("No documents found to index. Clearing BM25 index.")
        bm25 = get_bm25_index()
        bm25.build([])
        index_file = Path(BM25_INDEX_PATH) / "index.pkl"
        if index_file.exists():
            index_file.unlink()
        return
    
    all_chunks = []
    embedder = get_embedder()
    
    for doc_id, meta in metadata_store.items():
        if meta.get("status") != "completed":
            continue
            
        try:
            # Fetch all chunks for this doc_id from ChromaDB
            results = embedder.collection.get(
                where={"doc_id": doc_id},
                include=["documents", "metadatas"]
            )
            
            docs = results.get("documents", [])
            metas = results.get("metadatas", [])
            
            for d, m in zip(docs, metas):
                all_chunks.append({
                    "text": d,
                    "metadata": m
                })
                
            logger.info(f"Loaded {len(docs)} chunks for {doc_id} from Vector DB")
        except Exception as e:
            logger.error(f"Failed to fetch chunks for {doc_id} from ChromaDB: {e}")
    
    if all_chunks:
        bm25 = get_bm25_index()
        bm25.build(all_chunks)
        
        # Save to disk
        index_file = Path(BM25_INDEX_PATH) / "index.pkl"
        bm25.save(str(index_file))
        logger.info(f"BM25 index rebuilt with {len(all_chunks)} chunks")
    else:
        logger.warning("No chunks found to rebuild index")


def get_retriever() -> HybridRetriever:
    """Get or create the hybrid retriever instance"""
    global _retriever
    
    if _retriever is None:
        logger.info("Initializing HybridRetriever")
        embedder = get_embedder()
        bm25 = get_bm25_index()
        _retriever = HybridRetriever(embedder, bm25)
        logger.info("HybridRetriever initialized successfully")
    
    return _retriever


def get_rag_chain() -> RAGChain:
    """Get or create the RAG chain instance"""
    global _rag_chain
    
    if _rag_chain is None:
        logger.info("Initializing RAGChain")
        embedder = get_embedder()
        bm25 = get_bm25_index()
        
        from .config import (
            GROQ_API_KEY,
            GROQ_BASE_URL,
            GROQ_MODEL,
            OLLAMA_BASE_URL,
            OLLAMA_MODEL,
            OLLAMA_GEN_MODEL,
        )
        
        _rag_chain = RAGChain(
            embedder=embedder,
            bm25_index=bm25,
            groq_api_key=GROQ_API_KEY,
            groq_base_url=GROQ_BASE_URL,
            groq_model=GROQ_MODEL,
            ollama_base_url=OLLAMA_BASE_URL,
            ollama_model=OLLAMA_MODEL,
            ollama_generation_model=OLLAMA_GEN_MODEL,
        )
        logger.info("RAGChain initialized successfully")
    
    return _rag_chain


def get_document_metadata() -> dict:
    """Load document metadata from disk"""
    global _document_metadata
    
    if not _document_metadata:
        metadata_path = Path(METADATA_STORE_PATH)
        
        if metadata_path.exists():
            try:
                with open(metadata_path, "r") as f:
                    _document_metadata = json.load(f)
                logger.info(f"Loaded {len(_document_metadata)} documents from metadata store")
            except Exception as e:
                logger.error(f"Failed to load metadata store: {e}")
                _document_metadata = {}
        else:
            logger.info("No existing metadata store found, starting fresh")
            _document_metadata = {}
    
    return _document_metadata


def save_document_metadata():
    """Save document metadata to disk"""
    try:
        metadata_path = Path(METADATA_STORE_PATH)
        with open(metadata_path, "w") as f:
            json.dump(_document_metadata, f, indent=2)
        logger.debug("Document metadata saved")
    except Exception as e:
        logger.error(f"Failed to save metadata store: {e}")


def add_document_metadata(doc_id: str, metadata: dict):
    """Add or update document metadata"""
    _document_metadata[doc_id] = metadata
    save_document_metadata()


def remove_document_metadata(doc_id: str):
    """Remove document metadata"""
    if doc_id in _document_metadata:
        del _document_metadata[doc_id]
        save_document_metadata()


def get_system_status() -> dict:
    """Get current system status"""
    return {
        "embedder_ready": _embedder is not None,
        "bm25_ready": _bm25_index is not None,
        "retriever_ready": _retriever is not None,
        "rag_chain_ready": _rag_chain is not None,
        "documents_count": len(_document_metadata),
        "total_chunks": sum(
            doc.get("chunks_count", 0) for doc in _document_metadata.values()
        ),
    }


# ============================================================================
# ── Initialization ─────────────────────────────────────────────────────────
# ============================================================================

def initialize_all():
    """Initialize all RAG components"""
    logger.info("Initializing RAG system...")
    
    try:
        # Initialize all components
        get_embedder()
        get_bm25_index()
        get_retriever()
        get_rag_chain()
        get_document_metadata()
        
        # Rebuild BM25 index from all documents on startup
        rebuild_bm25_index()
        
        logger.info("RAG system initialized successfully")
        return True
    except Exception as e:
        logger.info("Failed to initialize RAG system")
        return False


def shutdown_all():
    """Cleanup resources on shutdown"""
    logger.info("Shutting down RAG system...")
    
    global _embedder, _bm25_index, _retriever, _rag_chain
    
    # Clear instances
    _embedder = None
    _bm25_index = None
    _retriever = None
    _rag_chain = None
    
    logger.info("RAG system shut down successfully")
