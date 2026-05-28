"""
src/evaluation/generator.py
----------------------------
Automated Synthetic Ground Truth Generator using LLM (Ollama or Groq).
Bootstraps QA pairs from extracted document layout blocks and tables to build evaluation datasets.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add src path to system path for imports
sys.path.append(str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
from api.config import (
    GROQ_API_KEY,
    GROQ_BASE_URL,
    GROQ_MODEL,
    EXTRACTED_DIR,
)

class SyntheticGenerator:
    def __init__(self, use_ollama: bool = False, ollama_model: str = "llama3.2:3b"):
        self.use_ollama = use_ollama
        if use_ollama:
            self.model = ollama_model
            self.client = OpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1"
            )
        else:
            self.model = os.getenv("GROQ_MODEL") or GROQ_MODEL or "llama-3.3-70b-versatile"
            self.client = OpenAI(
                api_key=os.getenv("GROQ_API_KEY") or GROQ_API_KEY,
                base_url=os.getenv("GROQ_BASE_URL") or GROQ_BASE_URL or "https://api.groq.com/openai/v1"
            )

    def _call_llm(self, prompt: str, system_prompt: str) -> str:
        """Call the LLM with error handling."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM API error during synthesis: {e}")
            # Try a plain-text backup if JSON format is not supported or failed
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt + "\nIMPORTANT: Return ONLY raw valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
            except Exception as backup_e:
                print(f"Backup LLM call failed: {backup_e}")
                return ""

    def generate_qa_pairs(self, doc_id: str, file_name: str, extracted_json_path: Path) -> List[Dict[str, Any]]:
        """Generate synthetic QA pairs for a single document extraction layout."""
        if not extracted_json_path.exists():
            print(f"Extraction file does not exist: {extracted_json_path}")
            return []

        try:
            with open(extracted_json_path, "r", encoding="utf-8") as f:
                extraction_data = json.load(f)
        except Exception as e:
            print(f"Error loading extraction data: {e}")
            return []

        pages = extraction_data.get("document", {}).get("pages", [])
        if not pages:
            print(f"No pages found in extraction data for {doc_id}")
            return []

        all_qa_pairs = []
        
        # We iterate over pages and select high-information content blocks (e.g. tables, key-value groups)
        for page in pages:
            page_num = page.get("page_number", 1)
            content_blocks = page.get("content", [])
            
            for b_idx, block in enumerate(content_blocks):
                block_type = block.get("type", "text")
                block_data = block.get("data", "")
                
                # Filter out low-information or extremely short blocks to maintain high-quality dataset
                if block_type == "text" and (not block_data or len(block_data.split()) < 10):
                    continue
                if block_type == "table" and (not block_data or len(block_data) < 2):
                    continue

                # Prepare textual representation of block
                block_str = ""
                if block_type == "table":
                    block_str = f"TABLE STRUCTURE:\n"
                    # Format as JSON string for LLM reading
                    block_str += json.dumps(block_data, indent=2)
                else:
                    block_str = f"TEXT BLOCK:\n{block_data}"

                system_prompt = (
                    "You are a precise Synthetic Dataset Generator. Your task is to ingest a structural content block "
                    "from a document page and generate exactly 1 to 2 high-quality, factual Question-Answer (QA) pairs. "
                    "The questions must be highly specific, directly answerable ONLY by the provided content, and contain "
                    "sufficient context (such as matching document name patterns or key variables if relevant). "
                    "Respond ONLY with a valid JSON object matching the schema below:\n\n"
                    "{\n"
                    "  \"qa_pairs\": [\n"
                    "    {\n"
                    "      \"question\": \"The specific query to ask...\",\n"
                    "      \"expected_answer\": \"The exact answer extracted from the block...\",\n"
                    "      \"keywords\": [\"important\", \"search\", \"terms\"]\n"
                    "    }\n"
                    "  ]\n"
                    "}"
                )

                prompt = (
                    f"Document Name: {file_name}\n"
                    f"Page Number: {page_num}\n"
                    f"Content Block:\n{block_str}\n\n"
                    f"Generate 1 to 2 high-quality QA pairs based strictly on the content above."
                )

                print(f"Generating QA for {file_name} Page {page_num} block {b_idx+1} ({block_type})...")
                response_str = self._call_llm(prompt, system_prompt)
                if not response_str:
                    continue

                try:
                    # Clean response string to find JSON bounds if LLM added formatting
                    if "```json" in response_str:
                        response_str = response_str.split("```json")[1].split("```")[0]
                    elif "```" in response_str:
                        response_str = response_str.split("```")[1].split("```")[0]
                    
                    parsed = json.loads(response_str.strip())
                    pairs = parsed.get("qa_pairs", [])
                    
                    for pair in pairs:
                        # Append metadata/lineage mapping
                        pair["page"] = page_num
                        pair["target_block_type"] = block_type
                        pair["target_block_index"] = b_idx
                        # Store exact content reference for Context Recall/Precision matching
                        pair["target_chunk_content"] = block_str
                        all_qa_pairs.append(pair)
                except Exception as e:
                    print(f"Failed to parse LLM QA output: {e}. Output was:\n{response_str}")

        return all_qa_pairs

async def main():
    parser = argparse.ArgumentParser(description="Synthetic Ground Truth QA Generator")
    parser.add_argument("--source_dir", type=str, default=str(Path(EXTRACTED_DIR)), help="Directory with processed extraction JSONs")
    parser.add_argument("--pdf_dir", type=str, default=str(Path(__file__).resolve().parents[2] / "test" / "files"), help="Directory containing raw PDFs for auto-ingestion")
    parser.add_argument("--output", type=str, default=str(Path(__file__).resolve().parent / "evaluation_dataset.json"), help="Output dataset path")
    parser.add_argument("--use_ollama", action="store_true", help="Use local Ollama model instead of Groq")
    parser.add_argument("--ollama_model", type=str, default="llama3.2:3b", help="Ollama model to use")
    
    args = parser.parse_args()
    
    source_dir = Path(args.source_dir)
    output_path = Path(args.output)
    pdf_dir = Path(args.pdf_dir)
    
    print(f"Starting Synthetic Ground Truth generation...")
    print(f"Source Directory: {source_dir}")
    print(f"PDF Directory   : {pdf_dir if pdf_dir.exists() else 'Not Found (Skipping Auto-Ingest)'}")
    print(f"Output File: {output_path}")
    print(f"LLM Engine: {'Ollama (' + args.ollama_model + ')' if args.use_ollama else 'Groq'}")
    
    # Load all processed documents metadata to map doc_id to filenames
    metadata_path = Path(source_dir.parent / "metadata.json")
    metadata_store = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, "r") as f:
                metadata_store = json.load(f)
        except Exception as e:
            print(f"Warning: could not load metadata.json: {e}")

    # Auto-Ingest PDFs from pdf_dir if they are not already in metadata_store
    if pdf_dir.exists() and pdf_dir.is_dir():
        pdf_files = list(pdf_dir.glob("*.pdf"))
        ingested_any = False
        
        for pdf_file in pdf_files:
            file_name = pdf_file.name
            
            # Check if already ingested (matching file_name in metadata_store values)
            already_ingested = False
            for doc_id, meta in metadata_store.items():
                if meta.get("file_name") == file_name:
                    already_ingested = True
                    break
                    
            if not already_ingested:
                print(f"\n[Auto-Ingest] Detected new test PDF: {file_name}. Ingesting...")
                try:
                    # Lazy dynamic imports to avoid circular dependency
                    from extraction.pipeline import extract_pdf
                    from preprocessing.chunker import chunk_extracted_data
                    from api.dependencies import get_embedder, add_document_metadata
                    from api.utils import generate_doc_id, save_upload_file, save_extraction_result, create_document_metadata
                    
                    doc_id = generate_doc_id()
                    
                    # 1. Read content
                    with open(pdf_file, "rb") as f:
                        content = f.read()
                    save_upload_file(content, file_name, doc_id)
                    
                    # 2. Extract PDF
                    extraction_result = await extract_pdf(str(pdf_file))
                    save_extraction_result(extraction_result, doc_id)
                    
                    doc_data = extraction_result.get("document", {})
                    pages = len(doc_data.get("pages", []))
                    document_type = doc_data.get("metadata", {}).get("document_type")
                    
                    # 3. Chunk
                    chunks = chunk_extracted_data(extraction_result)
                    for chunk in chunks:
                        chunk["metadata"]["doc_id"] = doc_id
                    
                    # 4. Embed
                    get_embedder().add_chunks(chunks)
                    
                    # 5. Metadata
                    metadata = create_document_metadata(
                        doc_id=doc_id,
                        filename=file_name,
                        pages=pages,
                        chunks_count=len(chunks),
                        document_type=document_type,
                    )
                    # Add completed status so it is indexable by BM25
                    metadata["status"] = "completed"
                    add_document_metadata(doc_id, metadata)
                    
                    metadata_store[doc_id] = metadata
                    ingested_any = True
                    print(f"[Auto-Ingest] Successfully ingested {file_name} -> {doc_id}")
                except Exception as e:
                    print(f"[Auto-Ingest] Error ingesting {file_name}: {e}")
                    
        if ingested_any:
            # Rebuild sparse index globally once
            from api.dependencies import rebuild_bm25_index
            print("\n[Auto-Ingest] Rebuilding global BM25 sparse search index...")
            rebuild_bm25_index()

    generator = SyntheticGenerator(use_ollama=args.use_ollama, ollama_model=args.ollama_model)
    
    # Find all extraction JSONs
    json_files = list(source_dir.glob("*.json"))
    if not json_files:
        print(f"No processed extraction files found in {source_dir}. Process some files first using uvicorn/api.")
        return

    evaluation_dataset = {"test_cases": []}
    
    for json_file in json_files:
        doc_id = json_file.stem
        # Map to original filename
        doc_meta = metadata_store.get(doc_id, {})
        file_name = doc_meta.get("file_name", f"{doc_id}.pdf")
        
        print(f"\n--- Ingesting Document: {file_name} (ID: {doc_id}) ---")
        qa_pairs = generator.generate_qa_pairs(doc_id, file_name, json_file)
        print(f"Generated {len(qa_pairs)} QA pairs for {file_name}")
        
        if qa_pairs:
            # Reconstruct the expected layout nodes and types for Block 1/2/3/4 structural eval if needed
            test_case = {
              "doc_id": doc_id,
              "file_name": file_name,
              "file_path": doc_meta.get("file_path", f"uploads/{doc_id}/{file_name}"),
              "ground_truth": {
                "queries": qa_pairs
              }
            }
            evaluation_dataset["test_cases"].append(test_case)

    # Save to evaluation_dataset.json
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(evaluation_dataset, f, indent=2)
        
    print(f"\n=== Bootstrapping Complete! ===")
    total_test_cases = len(evaluation_dataset["test_cases"])
    total_questions = sum(len(tc["ground_truth"]["queries"]) for tc in evaluation_dataset["test_cases"])
    print(f"Total Test Documents: {total_test_cases}")
    print(f"Total Synthesized Questions: {total_questions}")
    print(f"Saved evaluation dataset to: {output_path}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
