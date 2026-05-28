"""
src/scratch/ingest_all_test_files.py
-------------------------------------
Ingests all PDF files in test/files into the optimized RAG pipeline.
It extracts layout, builds region trees, extracts content, chunks trees,
runs local contextualization via Ollama (Llama3.2:3b), embeds vectors, and sparse indexes them.
Does not generate QA pairs to avoid costly LLM calls.
"""

import os
import sys
import json
import asyncio
from pathlib import Path

# Add src path to system path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from api.config import EXTRACTED_DIR
from extraction.pipeline import extract_pdf
from preprocessing.chunker import chunk_extracted_data
from api.dependencies import (
    get_embedder,
    add_document_metadata,
    rebuild_bm25_index,
    get_document_metadata,
)
from api.utils import (
    generate_doc_id,
    save_upload_file,
    save_extraction_result,
    create_document_metadata,
)

async def ingest_test_files():
    print("=======================================================")
    print("         INGESTING ALL TEST PDF DOCUMENTS              ")
    print("=======================================================")

    pdf_dir = Path(__file__).resolve().parents[2] / "test" / "files"
    if not pdf_dir.exists() or not pdf_dir.is_dir():
        print(f"[ERROR] pdf_dir not found at {pdf_dir}")
        return

    pdf_files = list(pdf_dir.glob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files inside {pdf_dir}")

    # Load active metadata (which should be empty if purged)
    metadata_store = get_document_metadata()
    ingested_count = 0

    for idx, pdf_file in enumerate(pdf_files, 1):
        file_name = pdf_file.name
        
        # Check if already ingested
        already_ingested = False
        for doc_id, meta in metadata_store.items():
            if meta.get("file_name") == file_name:
                already_ingested = True
                break
                
        if already_ingested:
            print(f"[{idx}/{len(pdf_files)}] '{file_name}' already ingested. Skipping.")
            continue

        print(f"\n[{idx}/{len(pdf_files)}] Ingesting '{file_name}'...")
        try:
            doc_id = generate_doc_id()
            
            # 1. Save uploaded file content
            with open(pdf_file, "rb") as f:
                content = f.read()
            save_upload_file(content, file_name, doc_id)
            
            # 2. Extract layout structure and text
            print("  - Running Heron Layout Detection & OCR...")
            extraction_result = await extract_pdf(str(pdf_file))
            save_extraction_result(extraction_result, doc_id)
            
            doc_data = extraction_result.get("document", {})
            pages = len(doc_data.get("pages", []))
            
            # 3. Tree-Aware chunking
            print("  - Building tree-aware chunks...")
            chunks = chunk_extracted_data(extraction_result)
            for chunk in chunks:
                chunk["metadata"]["doc_id"] = doc_id
            
            # 4. Contextualize chunks using Ollama Llama 3.2 3B
            print(f"  - Contextualizing {len(chunks)} chunks...")
            from api.dependencies import get_contextualizer
            contextualizer = get_contextualizer()
            # Ingest PDFs dynamically using generic or file-named document type
            doc_type = "invoice" if "invoice" in file_name.lower() else "bank_statement" if "statement" in file_name.lower() else "document"
            chunks = await contextualizer.contextualize_chunks(chunks, file_name, doc_type)
            
            # 5. Add to ChromaDB vector store
            print(f"  - Inserting into ChromaDB...")
            embedder = get_embedder()
            embedder.add_chunks(chunks)
            
            # 6. Add metadata
            metadata = create_document_metadata(
                doc_id=doc_id,
                filename=file_name,
                pages=pages,
                chunks_count=len(chunks),
                document_type=doc_type,
            )
            metadata["status"] = "completed"
            add_document_metadata(doc_id, metadata)
            
            metadata_store[doc_id] = metadata
            ingested_count += 1
            print(f"  -> Successfully ingested '{file_name}' -> ID: {doc_id}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  [ERROR] Error processing '{file_name}': {e}")

    if ingested_count > 0:
        print("\nRebuilding global BM25 sparse index from vector DB...")
        rebuild_bm25_index()
        print("[SUCCESS] BM25 Sparse Index rebuilt.")

    print("\n=======================================================")
    print(f"INGESTION FINISHED. Total PDFs newly ingested: {ingested_count}")
    print("=======================================================")

if __name__ == "__main__":
    asyncio.run(ingest_test_files())
