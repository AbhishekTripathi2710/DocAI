"""
src/evaluation/align_dataset_ids.py
------------------------------------
Dynamic Alignment Script.
Updates obsolete 'doc_id' and 'file_path' fields inside `evaluation_dataset.json`
to match the newly assigned doc_ids in `metadata.json` after re-ingestion,
retaining all existing ground-truth QA pairs.
"""

import os
import sys
import json
from pathlib import Path

# Add src path to system path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from api.config import METADATA_STORE_PATH

def align_ids():
    print("=======================================================")
    print("        ALIGNING EVALUATION DATASET DOCUMENT IDS       ")
    print("=======================================================")

    dataset_path = Path(__file__).resolve().parent / "evaluation_dataset.json"
    metadata_path = Path(METADATA_STORE_PATH)

    if not dataset_path.exists():
        print(f"[ERROR] evaluation_dataset.json not found at {dataset_path}")
        return

    if not metadata_path.exists():
        print(f"[ERROR] metadata.json not found at {metadata_path}. Please ingest documents first.")
        return

    # 1. Load active metadata.json
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        print(f"Loaded active metadata store containing {len(metadata)} documents.")
    except Exception as e:
        print(f"[ERROR] Failed to load metadata: {e}")
        return

    # Map file_name -> doc_id
    filename_to_doc_id = {}
    for doc_id, doc_meta in metadata.items():
        fn = doc_meta.get("file_name")
        if fn:
            filename_to_doc_id[fn.lower()] = doc_id

    # 2. Load evaluation_dataset.json
    try:
        with open(dataset_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        print(f"Loaded evaluation dataset containing {len(dataset.get('test_cases', []))} test documents.")
    except Exception as e:
        print(f"[ERROR] Failed to load evaluation dataset: {e}")
        return

    # 3. Update IDs and file_paths in test cases
    aligned_count = 0
    missing_count = 0
    
    test_cases = dataset.get("test_cases", [])
    for case in test_cases:
        fn = case.get("file_name")
        if not fn:
            continue
            
        fn_lower = fn.lower()
        if fn_lower in filename_to_doc_id:
            new_doc_id = filename_to_doc_id[fn_lower]
            old_doc_id = case.get("doc_id")
            
            # Update fields
            case["doc_id"] = new_doc_id
            case["file_path"] = f"uploads/{new_doc_id}/{fn}"
            
            if old_doc_id != new_doc_id:
                print(f"  - Aligned '{fn}': {old_doc_id} -> {new_doc_id}")
            aligned_count += 1
        else:
            print(f"  [WARNING] New document '{fn}' is missing from metadata.json! Has it been ingested?")
            missing_count += 1

    # 4. Save updated evaluation_dataset.json
    try:
        with open(dataset_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)
        print("\n[SUCCESS] ALIGNMENT COMPLETE!")
        print(f"  - Total test documents aligned: {aligned_count}")
        if missing_count > 0:
            print(f"  - [WARNING] Total test documents not found in metadata: {missing_count}")
        print("=======================================================")
    except Exception as e:
        print(f"[ERROR] Failed to save updated evaluation dataset: {e}")

if __name__ == "__main__":
    align_ids()
