"""
preprocessing/chunker.py
---------------------------
Convert extracted JSON to searchable chunks with enhanced options.
"""

import json
import uuid
from typing import Any, Dict, List, Optional, Literal

TableStrategy = Literal["sentence", "raw_json", "auto"]
SIMPLE_TABLE_THRESHOLD = 5  # max columns for sentence‑style conversion


def _row_to_sentence(row: Dict[str, Any]) -> str:
    """Convert a table row dict into a natural-language sentence."""
    parts = []
    for k, v in row.get("columns", {}).items():
        if v is None:
            continue
        parts.append(f"{k}: {v}")
    return ", ".join(parts)


def _row_to_json_string(row: Dict[str, Any]) -> str:
    """Return the row as a compact JSON string."""
    return json.dumps(row.get("columns", {}), ensure_ascii=False)


def _optimise_kv_text(data: str) -> str:
    """
    Improve embedding quality for simple single-line key_value text.
    Replace colon with space to help vector similarity for short pairs.
    """
    if ":" not in data or "\n" in data:
        return data
    parts = data.split(":", 1)
    if len(parts) == 2 and len(parts[0].split()) <= 8:
        # short key – join with space
        return f"{parts[0].strip()} {parts[1].strip()}"
    return data


def _merge_small_plain_chunks(chunks: List[Dict[str, Any]], max_len: int = 1200) -> List[Dict[str, Any]]:
    """Merge consecutive text blocks on the same page into larger chunks."""
    merged = []
    buffer_chunks = []
    
    def flush_buffer():
        if not buffer_chunks:
            return
        if len(buffer_chunks) == 1:
            merged.append(buffer_chunks[0])
            buffer_chunks.clear()
            return
        
        # Merge them
        combined_text = "\n".join(c["text"] for c in buffer_chunks)
        # Use metadata of the first chunk
        meta = buffer_chunks[0]["metadata"].copy()
        
        merged.append({
            "text": combined_text,
            "metadata": meta,
            "type": "text_block"
        })
        buffer_chunks.clear()

    for c in chunks:
        # We merge consecutive chunks of type 'text_block' on the SAME page.
        # Note: we check both 'type' and page equality.
        if c["type"] == "text_block":
            page = c["metadata"].get("page", "?")
            if buffer_chunks:
                buf_page = buffer_chunks[0]["metadata"].get("page", "?")
                # If page is different, flush first
                if page != buf_page:
                    flush_buffer()
            
            buffer_chunks.append(c)
            
            # Check length: if total length of texts in buffer exceeds max_len, flush.
            total_len = sum(len(bc["text"]) for bc in buffer_chunks)
            if total_len >= max_len:
                flush_buffer()
        else:
            # Non-'text_block' (e.g. table, table_window) - flush first, then append c
            flush_buffer()
            merged.append(c)
            
    flush_buffer()
    return merged





def _flatten_item(
    item: Dict[str, Any], 
    source_name: str, 
    parent_context: str = ""
) -> List[Dict[str, Any]]:
    """Recursively flattens a nested extraction item into searchable chunks."""
    chunks = []
    item_type = item.get("type", "unknown")
    page_num = item.get("page", "?")
    nested = item.get("nested_content", [])
    
    # 1. Prepare Parent Text
    parent_text = item.get("data", "") or item.get("text", "")
    if item_type == "table":
        # pyrefly: ignore [missing-import]
        from utils.table_utils import table_to_markdown
        parent_text = table_to_markdown(item.get("data", []))

    # 2. Process Children First (Granular pieces)
    child_chunks = []
    child_text_combined = ""
    current_context = f"[Inside {item_type.replace('_', ' ').title()}]"
    if parent_context:
        current_context = f"{parent_context} > {current_context}"

    for child in nested:
        child_res = _flatten_item(child, source_name, current_context)
        child_chunks.extend(child_res)
        child_text_combined += " " + " ".join([c["text"] for c in child_res])

    # 3. Add Parent Chunk
    if parent_text:
        prefix = f"[Document: {source_name}]"
        if parent_context:
            prefix += f" {parent_context}"
            
        final_text = f"{prefix}\n\n{parent_text}"
        
        # Sanitize metadata for ChromaDB (must be str, int, float, or bool)
        sanitized_meta = {}
        for k, v in {
            "page": page_num,
            "source": source_name,
            "type": item_type,
            "role": item.get("role")
        }.items():
            if v is None:
                sanitized_meta[k] = ""
            elif isinstance(v, (str, int, float, bool)):
                sanitized_meta[k] = v
            else:
                sanitized_meta[k] = str(v)

        if item_type == "table" and len(item.get("data", [])) > 7:
            # pyrefly: ignore [missing-import]
            from utils.table_utils import table_to_markdown
            rows = item.get("data", [])
            for i in range(0, len(rows), 3): # stride 3, window 5
                window = rows[i:i+5]
                if not window: break
                win_md = table_to_markdown(window)
                
                # Copy sanitized meta and update for window
                win_meta = sanitized_meta.copy()
                win_meta["type"] = "table_window"
                
                chunks.append({
                    "text": f"{prefix}\n[Table Rows {i+1}-{i+len(window)}]\n{win_md}",
                    "metadata": win_meta,
                    "type": "table"
                })
        else:
            chunks.append({
                "text": final_text,
                "metadata": sanitized_meta,
                "type": "text_block" if item_type != "table" else "table"
            })

    # 5. Add all child chunks
    chunks.extend(child_chunks)
    return chunks


def chunk_extracted_data(
    extracted: Dict[str, Any],
    table_strategy: TableStrategy = "auto",
    merge_plain: bool = True,
    merge_plain_max_len: int = 1200,
) -> List[Dict[str, Any]]:
    """
    Produce a list of chunk dicts from the output of extract_pdf().

    Parameters
    ----------
    extracted : dict
        PDF extraction result.
    table_strategy : "sentence" | "raw_json" | "auto"
        How to convert table rows. "auto" uses SIMPLE_TABLE_THRESHOLD.
    merge_plain : bool
        Whether to merge consecutive plain text blocks.
    merge_plain_max_len : int
        Target maximum character length for merged plain blocks.

    Returns
    -------
    Produce a list of chunk dicts from the hierarchical extraction JSON.
    """
    source_name = extracted["document"]["metadata"]["source"]
    all_chunks: List[Dict[str, Any]] = []

    for page in extracted["document"]["pages"]:
        for item in page["content"]:
            item_chunks = _flatten_item(item, source_name)
            all_chunks.extend(item_chunks)

    # Perform text block merging if requested
    if merge_plain:
        all_chunks = _merge_small_plain_chunks(all_chunks, max_len=merge_plain_max_len)

    # Assign unique IDs
    import uuid
    for c in all_chunks:
        c["id"] = str(uuid.uuid4())

    return all_chunks