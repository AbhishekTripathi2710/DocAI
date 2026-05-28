"""
src/scratch/purge_all_data.py
------------------------------
Maintenance script to completely clear:
1. ChromaDB vector database collections
2. Inverted BM25 indices on disk
3. Uploaded source PDF documents
4. Extracted structured hierarchical JSONs
5. Metadata stores
"""

import os
import shutil
import sys
from pathlib import Path

# Add src path to system path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from api.config import (
    UPLOAD_DIR,
    EXTRACTED_DIR,
    CHROMA_DB_PATH,
    BM25_INDEX_PATH,
    METADATA_STORE_PATH,
)
from api.dependencies import (
    get_embedder,
    rebuild_bm25_index,
    get_document_metadata,
    remove_document_metadata,
)

def purge_all():
    print("=======================================================")
    print("             STARTING ABSOLUTE SYSTEM PURGE            ")
    print("=======================================================")

    # 1. Reset ChromaDB collection
    try:
        print("[1/6] Resetting ChromaDB collections...")
        embedder = get_embedder()
        embedder.reset()
        print("  - ChromaDB reset completed successfully.")
    except Exception as e:
        print(f"  ⚠️ Error resetting ChromaDB: {e}")

    # 2. Clear Document Metadata Store
    try:
        print("[2/6] Clearing document metadata store...")
        metadata = get_document_metadata()
        doc_ids = list(metadata.keys())
        for doc_id in doc_ids:
            remove_document_metadata(doc_id)
        
        # Ensure metadata store file is set to empty dict
        import json
        with open(METADATA_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
        print("  - Metadata store cleared completely.")
    except Exception as e:
        print(f"  ⚠️ Error clearing metadata store: {e}")

    # 3. Clear Uploaded PDF documents
    try:
        print(f"[3/6] Clearing uploaded source PDFs: {UPLOAD_DIR}")
        uploads_path = Path(UPLOAD_DIR)
        if uploads_path.exists():
            for child in uploads_path.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
        print("  - Uploads directory cleared completely.")
    except Exception as e:
        print(f"  ⚠️ Error clearing uploads directory: {e}")

    # 4. Clear Extracted JSON extractions
    try:
        print(f"[4/6] Clearing extracted structured JSONs: {EXTRACTED_DIR}")
        extracted_path = Path(EXTRACTED_DIR)
        if extracted_path.exists():
            for child in extracted_path.iterdir():
                if child.is_file():
                    child.unlink()
        print("  - Extracted JSONs directory cleared completely.")
    except Exception as e:
        print(f"  ⚠️ Error clearing extracted directory: {e}")

    # 5. Clear BM25 Index Directories
    try:
        print(f"[5/6] Clearing BM25 index persistent storage: {BM25_INDEX_PATH}")
        bm25_path = Path(BM25_INDEX_PATH)
        if bm25_path.exists():
            for child in bm25_path.iterdir():
                if child.is_file():
                    child.unlink()
        print("  - BM25 index storage cleared completely.")
    except Exception as e:
        print(f"  ⚠️ Error clearing BM25 index storage: {e}")

    # 6. Rebuild empty index
    try:
        print("[6/6] Rebuilding empty BM25 sparse search index...")
        rebuild_bm25_index()
        print("  - BM25 empty index rebuilt successfully.")
    except Exception as e:
        print(f"  ⚠️ Error rebuilding BM25 index: {e}")

    print("\n[SUCCESS] ABSOLUTE SYSTEM PURGE COMPLETED SUCCESSFULY!")
    print("=======================================================")

if __name__ == "__main__":
    purge_all()
