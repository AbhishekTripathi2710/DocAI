"""
rag/prompt.py
-------------
Contains the system instruction and a helper to format
retrieved chunks into a single LLM prompt.
"""

from typing import List, Dict, Any
import json

SYSTEM_INSTRUCTIONS = (
    "You are a precise, data-driven Document Assistant. Your goal is to provide direct, accurate, and concise answers.\n\n"
    "STRICT RULES:\n"
    "1. DIRECT ANSWER ONLY: If the user asks a simple question (e.g., 'What is the total?'), provide ONLY the value or a short sentence. NEVER start with 'Based on the document...' or 'The context states...'.\n"
    "2. NO CONTEXT RESTATING: Do not repeat or summarize the provided context chunks in your response.\n"
    "3. TABLES: Use Markdown tables ONLY if the user asks to 'list', 'show history', or 'compare' multiple items. For single data points, use plain text.\n"
    "4. ACCURACY & CORRELATION: Extract values exactly as they appear. You MUST associate the extracted facts strictly with the 'Document Name' listed in the same CHUNK block as the extracted content. Never map a value from one chunk to a document name of another chunk.\n"
    "5. MISSING VALUES IN TABLES: If a user requests a list or table of specific values across multiple documents, and some information is missing for a specific document, represent it as 'Not Found' or 'N/A' in that table cell. Do NOT append loose negative statements (e.g., 'I could not find...') outside the table if a partial list is successfully generated.\n"
    "6. TABLE FORMATTING: When using a table, each row MUST be a single line of Markdown code. Do NOT wrap particulars or long IDs to new lines. Use proper | Header | syntax.\n"
    "7. NO PREAMBLE: Start your response directly with the answer."
)

def format_context(chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "Unknown")
        page = meta.get("page", "?")
        text = chunk.get("text", "")
        
        # Identity hint if available
        identity = f"\nOwner: {meta['customer_name']}" if "customer_name" in meta else ""
        
        header = (
            f"=== CHUNK {i} ===\n"
            f"Document Name: {source}\n"
            f"Page Number: {page}"
            f"{identity}"
        )
        
        # Use concise Key: Value for structured data to avoid LLM table confusion
        structured_data = ""
        if "raw_json" in meta:
            try:
                raw = json.loads(meta["raw_json"])
                kv_pairs = [f"{k.replace('_', ' ').title()}: {v}" for k, v in raw.items() if v]
                structured_data = "\n".join(kv_pairs)
            except:
                pass
        
        content = text
        if structured_data:
            # If we have situational context (from contextualizer), keep it, then add KV pairs
            if "\n\n" in text:
                prefix = text.split("\n\n")[0]
                content = f"{prefix}\n{structured_data}"
            else:
                content = structured_data
                
        parts.append(f"{header}\nContent:\n{content}\n====================")
    return "\n\n".join(parts)

def build_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    context = format_context(chunks)
    return f"{SYSTEM_INSTRUCTIONS}\n\nContext:\n{context}\n\nQuestion: {question}\n\nAnswer:"