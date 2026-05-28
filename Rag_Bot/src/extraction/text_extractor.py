"""
src/extraction/text_extractor.py
----------------------------------
Advanced layout-aware text extraction using geometric 'bbox-align' logic.
Handles skewed text and complex alignments using slope-aware grouping.
"""

import re
import math
from collections import defaultdict

import numpy as np
import pdfplumber

from .parser import (
    TEXT_X_TOLERANCE,
    TEXT_Y_TOLERANCE,
    LINE_Y_TOLERANCE,
    COLUMN_GAP_THRESHOLD,
    KV_KEY_MAX_TOKENS,
    _RE_URL,
    _RE_EMAIL,
    clean_text,
)

# =============================================================================
# Geometric Primitives for Alignment
# =============================================================================

from .geometry import group_words_geometrically

# =============================================================================
# Fallback: plain text extraction
# =============================================================================

def _fallback_text_blocks(page):
    print("    [layout] ⚠ Falling back to legacy extract_text()")
    raw = page.extract_text(
        layout=True, x_tolerance=TEXT_X_TOLERANCE, y_tolerance=TEXT_Y_TOLERANCE
    )
    if not raw or not raw.strip():
        raw = page.extract_text(
            x_tolerance=TEXT_X_TOLERANCE, y_tolerance=TEXT_Y_TOLERANCE
        ) or ""
    cleaned = clean_text(raw)
    if not cleaned:
        return []
    parts = re.split(r" {2,}", cleaned)
    return [{"type": "text", "role": "plain", "data": p.strip()} for p in parts if p.strip()]

# =============================================================================
# Main extraction function (Geometric bbox-align Logic)
# =============================================================================

def extract_layout_blocks(
    page,
    table_bboxes = None,
):
    table_bboxes = table_bboxes or []

    try:
        all_words = page.extract_words(
            x_tolerance=TEXT_X_TOLERANCE,
            y_tolerance=TEXT_Y_TOLERANCE,
            keep_blank_chars=False,
            use_text_flow=False,
            extra_attrs=[],
        )
        def _word_in_bboxes(word, bboxes, padding=4):
            wx0, wy0 = word["x0"], word["top"]
            wx1, wy1 = word["x1"], word["bottom"]
            for x0, y0, x1, y1 in bboxes:
                if wx0 < x1 + padding and wx1 > x0 - padding \
                   and wy0 < y1 + padding and wy1 > y0 - padding:
                    return True
            return False

        if table_bboxes:
            all_words = [w for w in all_words if not _word_in_bboxes(w, table_bboxes)]
    except Exception as exc:
        print(f"    [layout] extract_words() raised {exc!r} — using fallback")
        all_words = []

    if not all_words:
        return _fallback_text_blocks(page)

    # Group into lines using geometric slope-aware logic
    rows = group_words_geometrically(all_words)
    print(f"    [layout] Visual lines formed: {len(rows)}")

    # 5. Form line text and determine roles
    unique_blocks = []
    for row_words in rows:
        parts = []
        for i, curr_word in enumerate(row_words):
            if i > 0:
                prev_word = row_words[i-1]
                gap = curr_word["x0"] - prev_word["x1"]
                # Large horizontal gap indicates a column break or multi-space
                sep = "  " if gap > COLUMN_GAP_THRESHOLD else " "
                parts.append(sep)
            parts.append(curr_word["text"])
        
        text = "".join(parts).strip()
        if not text: continue

        role = "plain"
        if ":" in text:
            colon_pos = text.find(":")
            key_part = text[:colon_pos].strip()
            if len(key_part.split()) <= KV_KEY_MAX_TOKENS \
               and not bool(_RE_URL.search(key_part)) \
               and not bool(_RE_EMAIL.search(key_part)):
                role = "key_value"

        unique_blocks.append({
            "type": "text",
            "role": role,
            "data": text
        })

    # 6. Post-processing merge
    def is_short_label(t):
        t_strip = t.strip()
        if not t_strip: return False
        tokens = t_strip.split()
        if not (1 <= len(tokens) <= 4): return False
        if not t_strip[0].isupper(): return False
        if t_strip[-1] in ",;.!?": return False
        return True

    def looks_like_standalone_value(t):
        t_strip = t.strip()
        if re.fullmatch(r'[\d,.\-₹$€£¥%\s]+', t_strip): return True
        if bool(_RE_URL.search(t_strip)) or bool(_RE_EMAIL.search(t_strip)): return True
        return False

    merged_blocks = []
    i = 0
    while i < len(unique_blocks):
        current = unique_blocks[i].copy()
        if current["role"] == "key_value" and i + 1 < len(unique_blocks):
            nxt = unique_blocks[i + 1]
            if nxt["role"] == "plain" and len(nxt["data"]) < 60:
                nxt_data = nxt["data"]
                # Heuristic: merge if it's not a short label/standalone value 
                # OR if it starts with a lowercase letter (strong continuation signal)
                is_continuation = not nxt_data[0].isupper() if nxt_data else False
                
                if is_continuation or (not is_short_label(nxt_data) and not looks_like_standalone_value(nxt_data)):
                    current["data"] = current["data"] + " " + nxt_data
                    merged_blocks.append(current)
                    i += 2
                    continue
        merged_blocks.append(current)
        i += 1

    kv_count    = sum(1 for b in merged_blocks if b["role"] == "key_value")
    plain_count = sum(1 for b in merged_blocks if b["role"] == "plain")
    print(f"    [layout] Blocks created   : {len(merged_blocks)} ({kv_count} kv, {plain_count} plain)")
    return merged_blocks
