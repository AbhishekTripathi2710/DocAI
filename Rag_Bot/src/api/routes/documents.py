"""
Document management endpoints - upload, delete, list documents
"""

import logging
import time
from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException, Form, BackgroundTasks

# pyrefly: ignore [missing-import]
from api.models import (
    DocumentStatus, 
    DocumentInfo, 
    DocumentListResponse, 
    DocumentDeleteResponse, 
    ErrorResponse
)

# pyrefly: ignore [missing-import]
from extraction.pipeline import extract_pdf
# pyrefly: ignore [missing-import]
from preprocessing.chunker import chunk_extracted_data
# pyrefly: ignore [missing-import]
from api.dependencies import (
    get_embedder,
    add_chunks_to_bm25,
    rebuild_bm25_index,
    get_document_metadata,
    add_document_metadata,
    remove_document_metadata,
)
# pyrefly: ignore [missing-import]
from api.utils import (
    generate_doc_id,
    validate_upload_file,
    save_upload_file,
    save_extraction_result,
    delete_document_files,
    create_document_metadata,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])
async def _process_document_task(
    doc_id: str, 
    file_path: str, 
    filename: str, 
    doc_type: str,
    metadata: dict
):
    """Background task to process a document (Extract -> Chunk -> Contextualize -> Embed)"""
    try:
        # Step 1: Extract
        logger.info(f"[1/5] Background extraction started for {doc_id} ({filename})")
        extraction_result = await extract_pdf(file_path, doc_type=doc_type)
        save_extraction_result(extraction_result, doc_id)
        
        doc_data = extraction_result.get("document", {})
        pages = len(doc_data.get("pages", []))
        # Use the doc_type provided at upload time directly,
        # since the extraction pipeline doesn't forward it in metadata
        document_type = doc_type
        
        # Step 2: Chunk
        logger.info(f"[2/5] Chunking document {doc_id}")
        chunks = chunk_extracted_data(extraction_result)
        for chunk in chunks:
            chunk["metadata"]["doc_id"] = doc_id
        
        # Step 3: Contextualize
        logger.info(f"[3/5] Contextualizing {len(chunks)} chunks using AI...")
        # pyrefly: ignore [missing-import]
        from api.dependencies import get_contextualizer
        contextualizer = get_contextualizer()
        chunks = await contextualizer.contextualize_chunks(chunks, filename, doc_type)
        
        # Step 4: Embed
        logger.info(f"[4/5] Adding {len(chunks)} chunks to Vector DB...")
        embedder = get_embedder()
        embedder.add_chunks(chunks)
        
        # Step 5: Update Metadata & Index
        logger.info(f"[5/5] Finalizing metadata and search index...")
        metadata.update({
            "pages": pages,
            "chunks_count": len(chunks),
            "document_type": document_type,
            "status": DocumentStatus.COMPLETED
        })
        add_document_metadata(doc_id, metadata)
        
        # Incremental update instead of full rebuild
        add_chunks_to_bm25(chunks)
        
        logger.info(f"✅ Background processing completed for {doc_id}")
        
    except Exception as e:
        logger.error(f"Background processing failed for {doc_id}: {e}", exc_info=True)
        metadata["status"] = DocumentStatus.FAILED
        add_document_metadata(doc_id, metadata)

@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    doc_type: str = Form(...),
    force_reprocess: bool = Form(False)
):
    """
    Upload and process a PDF document (Asynchronous)
    """
    try:
        # Check if already exists and if we should delete it first
        existing_meta = get_document_metadata()
        for old_doc_id, info in existing_meta.items():
            if info["file_name"] == file.filename and force_reprocess:
                logger.info(f"Force re-processing requested for {file.filename}. Deleting old version...")
                await delete_document(old_doc_id)
                break
        # Basic Validation
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        if not file.content_type == "application/pdf":
            raise HTTPException(status_code=400, detail="Invalid file type. Only PDF files are allowed")
        
        content = await file.read()
        error = validate_upload_file(file.filename, len(content))
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        doc_id = generate_doc_id()
        file_path = save_upload_file(content, file.filename, doc_id)
        
        # Initial Metadata
        metadata = create_document_metadata(
            doc_id=doc_id,
            filename=file.filename,
            pages=0,
            chunks_count=0,
            document_type=doc_type,
        )
        metadata["status"] = DocumentStatus.PROCESSING
        add_document_metadata(doc_id, metadata)
        
        # Start Background Task
        background_tasks.add_task(
            _process_document_task, 
            doc_id, str(file_path), file.filename, doc_type, metadata
        )
        
        return {
            "doc_id": doc_id,
            "file_name": file.filename,
            "pages": 0,
            "chunks_count": 0,
            "created_at": metadata["created_at"],
            "status": DocumentStatus.PROCESSING,
            "document_type": doc_type,
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{doc_id}", response_model=DocumentInfo)
async def get_document_status(doc_id: str):
    """Get the current processing status of a document"""
    metadata = get_document_metadata().get(doc_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {
        "doc_id": doc_id,
        "file_name": metadata["file_name"],
        "pages": metadata.get("pages", 0),
        "chunks_count": metadata.get("chunks_count", 0),
        "created_at": metadata["created_at"],
        "status": metadata.get("status", DocumentStatus.COMPLETED),
        "document_type": metadata.get("document_type"),
    }

@router.get("/", response_model=DocumentListResponse)
async def list_documents():
    """
    List all uploaded and processed documents
    
    Returns list of documents with metadata
    """
    try:
        metadata_store = get_document_metadata()
        documents = [
            DocumentInfo(**doc_data)
            for doc_data in metadata_store.values()
        ]
        
        return {
            "documents": documents,
            "total": len(documents),
        }
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list documents"
        )


@router.get("/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: str):
    """
    Get information about a specific document
    
    - **doc_id**: Document ID
    """
    try:
        metadata_store = get_document_metadata()
        
        if doc_id not in metadata_store:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {doc_id}"
            )
        
        doc_data = metadata_store[doc_id]
        return DocumentInfo(**doc_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving document: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve document"
        )


@router.delete("/{doc_id}", response_model=DocumentDeleteResponse)
async def delete_document(doc_id: str):
    """
    Delete a document and its associated data
    
    - **doc_id**: Document ID to delete
    
    Removes chunks from embeddings and BM25 index
    """
    try:
        metadata_store = get_document_metadata()
        
        if doc_id not in metadata_store:
            raise HTTPException(
                status_code=404,
                detail=f"Document not found: {doc_id}"
            )
        
        doc_metadata = metadata_store[doc_id]
        chunks_count = doc_metadata.get("chunks_count", 0)
        
        logger.info(f"Deleting document: {doc_id}")
        
        # Remove from embedder (ChromaDB)
        embedder = get_embedder()
        embedder.delete_by_filter({"doc_id": {"$eq": doc_id}})
        logger.info(f"Removed {chunks_count} chunks from embedder")
        
        # Delete files
        delete_document_files(doc_id)
        
        # Remove metadata
        remove_document_metadata(doc_id)

        # Rebuild BM25 index globally
        rebuild_bm25_index()
        
        logger.info(f"Document deleted: {doc_id}")
        
        return {
            "message": f"Document deleted successfully",
            "doc_id": doc_id,
            "chunks_deleted": chunks_count,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete document"
        )
@router.post("/purge", response_model=dict)
async def purge_all_documents():
    """
    DANGEROUS: Deletes all documents, all metadata, and clears the vector database.
    Use this to reset the system if data corruption (like context bleeding) occurs.
    """
    try:
        # Clear Vector DB first (efficient reset)
        embedder = get_embedder()
        embedder.reset()
        
        # Clear metadata and other files
        metadata_store = list(get_document_metadata().keys())
        for doc_id in metadata_store:
            # We don't need to call embedder.delete here as reset handles it
            delete_document_files(doc_id)
            remove_document_metadata(doc_id)

        # Rebuild empty BM25
        rebuild_bm25_index()
            
        return {"message": f"System purged. All collections reset and {len(metadata_store)} documents removed from disk."}
    except Exception as e:
        logger.error(f"Purge failed: {e}")
        raise HTTPException(status_code=500, detail="Purge failed")
