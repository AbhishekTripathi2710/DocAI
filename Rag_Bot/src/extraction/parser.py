"""
src/extraction/parser.py
------------------------
Configuration constants and lightweight utility/helper functions.

All other modules in this package import from here — keep this file free
of heavy dependencies (no pdfplumber, numpy, sklearn).
"""

import re
from typing import Any

# =============================================================================
# ── pdfplumber tolerances ────────────────────────────────────────────────────
# =============================================================================

TEXT_X_TOLERANCE = 3
TEXT_Y_TOLERANCE = 3

# =============================================================================
# ── Table-detection strategy ─────────────────────────────────────────────────
# =============================================================================

TABLE_SETTINGS = {
    "vertical_strategy":   "lines",
    "horizontal_strategy": "lines",
}

# =============================================================================
# ── Table-validation thresholds ──────────────────────────────────────────────
# =============================================================================

MIN_ROWS              = 2
MIN_COLS              = 2
MAX_HEADER_LEN        = 80
MIN_FILL_RATIO        = 0.30
MIN_COL_DIVERSITY     = 0.50
ROW_CONSISTENCY       = 0.70
VALID_SCORE_THRESHOLD = 50
HORIZONTAL_SEGMENT_GAP = 12.0

# =============================================================================
# ── Layout-block extraction settings ─────────────────────────────────────────
# =============================================================================

LINE_Y_TOLERANCE      = 3.0    # points within which words share the same line
COLUMN_GAP_THRESHOLD  = 20.0   # horizontal gap that signals a column break
DEDUP_OVERLAP         = 0.70

# =============================================================================
# ── Semantic merging settings ─────────────────────────────────────────────────
# =============================================================================

# Vertical gap (points) large enough to break any ongoing KV block.
LARGE_GAP_THRESHOLD   = 15.0

# Maximum tokens allowed in a continuation line following a KV block.
MAX_CONTINUATION_TOKENS = 30

# Minimum number of tokens a line must have before the colon to be a key.
KV_KEY_MAX_TOKENS     = 8

# Debug: set True to embed `structure_hint` in every text block
DEBUG_HINTS           = False

MAX_KV_VALUE_LENGTH      = 200
MAX_PLAIN_MERGE_LENGTH   = 120

# =============================================================================
# ── Regex helpers ─────────────────────────────────────────────────────────────
# =============================================================================

_RE_URL   = re.compile(r'https?://|www\.', re.IGNORECASE)
_RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# =============================================================================
# ── Utility helpers ──────────────────────────────────────────────────────────
# =============================================================================


def to_snake_case(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[\s\-/]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text


def sanitise_cell(value: Any) -> Any:
    if value is None:
        return None
    value = str(value).strip()
    if value in ("", "-", "–", "—"):
        return None
    value = re.sub(r"[\r\n]+", " ", value)
    value = re.sub(r" {2,}", " ", value)
    return value


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"[\r\n]+", " ", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def is_empty_row(row: list) -> bool:
    return all(sanitise_cell(cell) is None for cell in row)
