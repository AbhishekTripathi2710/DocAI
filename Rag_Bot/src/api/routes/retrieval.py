"""
Query and retrieval endpoints - search and ask questions
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException

from api.models import (
    QueryRequest,
    QueryResponse,
    RetrievalMode,
)
from api.dependencies import (
    get_embedder,
    get_rag_chain,
    get_retriever,
    get_document_metadata,
)
from api.utils import format_retrieval_results

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["retrieval"])


@router.post("/dense", response_model=QueryResponse)
async def query_dense(request: QueryRequest):
    """
    Query documents using dense retrieval only (semantic similarity)
    
    - **query**: Question or search query
    - **top_k**: Number of top results (1-20, default 5)
    - **doc_id**: Optional specific document to search
    - **include_metadata**: Include metadata in results
    
    Returns answer and retrieved chunks
    """
    start_time = time.time()
    
    try:
        logger.info(f"Dense query: {request.query[:100]}...")
        
        # Get embedder and perform dense retrieval
        embedder = get_embedder()
        
        # Build filter if doc_ids or doc_id is specified
        where_filter = None
        metadata_store = get_document_metadata()
        if request.doc_ids:
            for d_id in request.doc_ids:
                if d_id not in metadata_store:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document not found: {d_id}"
                    )
            where_filter = {"doc_id": {"$in": request.doc_ids}}
        elif request.doc_id:
            if request.doc_id not in metadata_store:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document not found: {request.doc_id}"
                )
            where_filter = {"doc_id": {"$eq": request.doc_id}}
        
        # Perform query
        results = embedder.query(
            request.query,
            top_k=request.top_k,
            where=where_filter,
        )
        
        # Initial chunk list (raw)
        raw_chunks = []
        if results and results["documents"] and results["documents"][0]:
            for doc, meta, distance in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0] if results.get("distances") else []
            ):
                similarity = 1 - (distance / 2)
                raw_chunks.append({
                    "text": doc,
                    "metadata": meta,
                    "score": similarity,
                    "type": meta.get("type", "text_block")
                })
        
        # Generate answer using RAG chain
        rag_chain = get_rag_chain()
        answer = rag_chain.answer(
            request.query,
            top_k=request.top_k,
            where=where_filter,
            llm_provider=request.llm_provider,
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Use utility for standardized response formatting
        return format_retrieval_results(
            query=request.query,
            answer=answer,
            retrieved_chunks=raw_chunks,
            retrieval_mode="dense",
            processing_time_ms=processing_time,
            include_metadata=request.include_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dense query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/hybrid", response_model=QueryResponse)
async def query_hybrid(request: QueryRequest):
    """
    Query documents using hybrid retrieval (dense + sparse with RRF)
    
    - **query**: Question or search query
    - **top_k**: Number of top results (1-20, default 5)
    - **doc_id**: Optional specific document to search
    - **include_metadata**: Include metadata in results
    
    Combines semantic similarity and keyword matching for better results
    """
    start_time = time.time()
    
    try:
        logger.info(f"Hybrid query: {request.query[:100]}...")
        
        # Get retriever and perform hybrid retrieval
        retriever = get_retriever()
        
        # Build filter if doc_ids or doc_id is specified
        where_filter = None
        metadata_store = get_document_metadata()
        if request.doc_ids:
            for d_id in request.doc_ids:
                if d_id not in metadata_store:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Document not found: {d_id}"
                    )
            where_filter = {"doc_id": {"$in": request.doc_ids}}
        elif request.doc_id:
            if request.doc_id not in metadata_store:
                raise HTTPException(
                    status_code=404,
                    detail=f"Document not found: {request.doc_id}"
                )
            where_filter = {"doc_id": {"$eq": request.doc_id}}
        
        # Perform hybrid retrieval
        retrieved_chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            where=where_filter,
        )
        
        # Generate answer using RAG chain
        rag_chain = get_rag_chain()
        answer = rag_chain.answer_hybrid(
            request.query,
            top_k=request.top_k,
            where=where_filter,
            llm_provider=request.llm_provider,
        )
        
        processing_time = (time.time() - start_time) * 1000
        
        # Use utility for standardized response formatting
        return format_retrieval_results(
            query=request.query,
            answer=answer,
            retrieved_chunks=retrieved_chunks,
            retrieval_mode="hybrid",
            processing_time_ms=processing_time,
            include_metadata=request.include_metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in hybrid query: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )


@router.post("/ask", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """
    Ask a question with automatic retrieval mode selection
    
    - **query**: Question to ask
    - **mode**: Retrieval mode - "dense" or "hybrid" (default hybrid)
    - **top_k**: Number of top results to retrieve
    - **doc_id**: Optional specific document to search
    
    Routes to appropriate retrieval method based on mode parameter
    """
    if request.mode == RetrievalMode.DENSE:
        return await query_dense(request)
    elif request.mode == RetrievalMode.HYBRID:
        return await query_hybrid(request)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown retrieval mode: {request.mode}"
        )


@router.get("/search")
async def search(
    q: str,
    doc_id: Optional[str] = None,
    top_k: int = 5,
    mode: str = "hybrid",
):
    """
    Simple search endpoint using query parameters
    
    - **q**: Search query
    - **doc_id**: Optional document ID to search
    - **top_k**: Number of results (1-20)
    - **mode**: Retrieval mode (dense or hybrid)
    
    Convenience endpoint for basic search
    """
    request = QueryRequest(
        query=q,
        doc_id=doc_id,
        top_k=min(max(top_k, 1), 100),
        mode=RetrievalMode(mode) if mode in ["dense", "hybrid"] else RetrievalMode.HYBRID,
    )
    
    return await ask_question(request)
