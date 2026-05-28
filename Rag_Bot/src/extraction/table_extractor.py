"""
src/extraction/table_extractor.py
---------------------------------
Table extraction and validation logic.
"""

import re
from collections import Counter, defaultdict

import pdfplumber

from .parser import (
    TABLE_SETTINGS,
    MIN_ROWS,
    MIN_COLS,
    MAX_HEADER_LEN,
    MIN_FILL_RATIO,
    ROW_CONSISTENCY,
    VALID_SCORE_THRESHOLD,
    to_snake_case,
    sanitise_cell,
    is_empty_row,
)

# =============================================================================
# Helper functions for flow-layout detection
# =============================================================================

TABLE_ROLE_TOKENS = {
    "item", "items", "description", "details", "particulars", "narration",
    "qty", "quantity", "rate", "price", "amount", "total", "debit", "credit", "balance"
}

META_HEADER_TOKENS = {
    "billed", "invoice", "issued", "issue", "date", "due", "account", "address", "contact", "name", "payment"
}


from .geometry import group_words_geometrically

def cluster_words_to_rows(words, y_tol=6):
    """
    Groups words into rows using geometric slope-aware logic.
    The y_tol parameter is kept for signature compatibility but 
    the underlying logic is now significantly more robust.
    """
    return group_words_geometrically(words)


def _row_tokens(row):
    tokens = []
    for w in row:
        tok = re.sub(r"[^a-z0-9]+", "", w["text"].lower())
        if tok:
            tokens.append(tok)
    return tokens


def is_candidate_row(row):
    if len(row) < 3:
        return False
    x_range = max(w['x1'] for w in row) - min(w['x0'] for w in row)
    if x_range < 120:
        return False
    texts = [w['text'] for w in row]
    numeric_count = sum(1 for t in texts if re.fullmatch(r'[\d.,$%-]+', t))
    if numeric_count / len(texts) >= 0.5:
        return False
    if ":" in " ".join(texts).lower():
        return False
    return True


def _transactional_lookahead_score(rows, header_idx, boundaries, header_names, window=6):
    if header_idx + 1 >= len(rows):
        return -5
    amount_pattern = re.compile(r"[$€£]?\d[\d,]*\.?\d{0,2}")
    look_rows = rows[header_idx + 1 : min(len(rows), header_idx + 1 + window)]
    valid_rows, amount_hits, repeated_shape_hits, prev_filled = 0, 0, 0, None

    for r in look_rows:
        mapped = assign_words_to_columns(r, boundaries)
        non_empty = sum(1 for col_idx in range(len(boundaries)) if mapped.get(f"column_{col_idx + 1}", "").strip())
        if non_empty >= 2:
            valid_rows += 1
            if amount_pattern.search(" ".join([mapped.get(f"column_{i + 1}", "").strip() for i in range(len(boundaries))])):
                amount_hits += 1
            if prev_filled is not None and abs(non_empty - prev_filled) <= 1:
                repeated_shape_hits += 1
            prev_filled = non_empty
    return valid_rows * 2 + amount_hits * 3 + repeated_shape_hits * 2


def has_column_structure(rows, start_idx, window=6):
    if start_idx + 1 >= len(rows):
        return False
    x_positions = []
    for row_idx in range(start_idx + 1, min(start_idx + 1 + window, len(rows))):
        for word in rows[row_idx]:
            x_positions.append(word['x0'])
    if not x_positions:
        return False
    x_positions.sort()
    clusters = []
    current_cluster = [x_positions[0]]
    for x in x_positions[1:]:
        if x - current_cluster[-1] <= 25:
            current_cluster.append(x)
        else:
            clusters.append(current_cluster)
            current_cluster = [x]
    if current_cluster:
        clusters.append(current_cluster)
    return len(clusters) >= 2


def _header_score(rows, idx, row):
    tokens = set(_row_tokens(row))
    row_text = " ".join(w['text'] for w in row).lower()
    score = len(tokens & TABLE_ROLE_TOKENS) * 6 - len(tokens & META_HEADER_TOKENS) * 4
    if max(w['x1'] for w in row) - min(w['x0'] for w in row) > 200:
        score += 2
    if has_column_structure(rows, idx, window=6):
        score += 8
    else:
        score -= 6
    if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', row_text):
        score -= 4
    if re.search(r'(january|february|march|april|may|june|july|august|september|october|november|december)', row_text):
        score -= 3
    header_row_sorted = sorted(row, key=lambda w: w['x0'])
    boundaries = get_column_boundaries(header_row_sorted)
    header_names = [re.sub(r'[^a-zA-Z0-9]', '_', w['text'].strip().lower()) for w in header_row_sorted]
    score += _transactional_lookahead_score(rows, idx, boundaries, header_names, window=6)
    return score


def detect_header_row(rows):
    if not rows:
        return None
    candidates = [(idx, row, _header_score(rows, idx, row)) for idx, row in enumerate(rows) if is_candidate_row(row)]
    if not candidates:
        return None
    candidates.sort(key=lambda x: x[2], reverse=True)
    top_score = candidates[0][2]
    tied = [c for c in candidates if c[2] == top_score]
    if len(tied) > 1:
        best, best_evidence = None, float('-inf')
        for idx, row, _ in tied:
            header_row_sorted = sorted(row, key=lambda w: w['x0'])
            evidence = _transactional_lookahead_score(rows, idx, get_column_boundaries(header_row_sorted), 
                                                      [re.sub(r'[^a-zA-Z0-9]', '_', w['text'].strip().lower()) for w in header_row_sorted], window=8)
            if evidence > best_evidence:
                best, best_evidence = (idx, row), evidence
        return best[1] if best else candidates[0][1]
    return candidates[0][1]


def get_column_boundaries(header_row):
    header_row_sorted = sorted(header_row, key=lambda w: w['x0'])
    boundaries = []
    for i, word in enumerate(header_row_sorted):
        left = word['x0']
        right = (word['x1'] + header_row_sorted[i + 1]['x0']) / 2 if i < len(header_row_sorted) - 1 else word['x1'] + 50
        boundaries.append((left, right))
    return boundaries


def assign_words_to_columns(row, boundaries):
    columns = defaultdict(str)
    if not boundaries:
        return columns
    first_left, last_right = boundaries[0][0], boundaries[-1][1]
    for word in row:
        wx = (word['x0'] + word['x1']) / 2.0
        target_idx = None
        for idx, (left, right) in enumerate(boundaries):
            if left <= wx < right:
                target_idx = idx
                break
        if target_idx is None:
            if wx < first_left: target_idx = 0
            elif wx >= last_right: target_idx = len(boundaries) - 1
            else:
                centers = [((l + r) / 2.0) for (l, r) in boundaries]
                target_idx = min(range(len(centers)), key=lambda i: abs(centers[i] - wx))
        col_key = f"column_{target_idx + 1}"
        if columns[col_key]: columns[col_key] += " "
        columns[col_key] += word['text']
    return columns


def _sanitize_header_name(text: str, used: set[str]) -> str:
    name = re.sub(r'[^a-zA-Z0-9]+', '_', text.strip().lower())
    name = re.sub(r'_+', '_', name).strip('_') or 'column'
    base, i = name, 2
    while name in used:
        name, i = f"{base}_{i}", i + 1
    used.add(name)
    return name


def extract_flow_layout_table(page, words):
    rows = cluster_words_to_rows(words, y_tol=6)
    if not rows: return []
    header_row = detect_header_row(rows)
    if header_row is None: return []

    boundaries = get_column_boundaries(header_row)
    header_row_sorted = sorted(header_row, key=lambda w: w['x0'])
    used_names = set()
    header_names = [_sanitize_header_name(w['text'], used_names) for w in header_row_sorted]
    header_top = min(w['top'] for w in header_row)
    data_rows = [row for row in rows if min(w['top'] for w in row) > header_top]

    row_tops = [min(w['top'] for w in row) for row in data_rows[:12]]
    pos_gaps = sorted([row_tops[i + 1] - row_tops[i] for i in range(len(row_tops) - 1) if row_tops[i + 1] - row_tops[i] > 0])
    fixed_gap = pos_gaps[len(pos_gaps) // 2] if len(pos_gaps) % 2 == 1 else (pos_gaps[len(pos_gaps) // 2 - 1] + pos_gaps[len(pos_gaps) // 2]) / 2 if pos_gaps else 0

    output, prev_row_top, consecutive_large_gaps = [], None, 0

    for row in data_rows:
        raw_columns = assign_words_to_columns(row, boundaries)
        columns = {}
        for col_idx in range(len(boundaries)):
            key, value = f"column_{col_idx + 1}", raw_columns.get(f"column_{col_idx + 1}", '').strip()
            if value:
                columns[header_names[col_idx] if col_idx < len(header_names) else key] = value
        non_empty_cols = {k: v for k, v in columns.items() if v.strip()}
        
        # --- MULTI-LINE ROW MERGING ---
        # If this row only has content in one column and we have a previous row,
        # it's likely a multi-line continuation (e.g., long transaction description).
        if len(non_empty_cols) == 1 and output:
            last_row = output[-1]["columns"]
            col_name = list(non_empty_cols.keys())[0]
            val = non_empty_cols[col_name]
            
            # Heuristic: merge if it's text, not a date/amount/digit-heavy string
            is_digit_heavy = sum(c.isdigit() for c in val) / max(len(val), 1) > 0.3
            if not is_digit_heavy and len(val) > 2:
                last_row[col_name] = (last_row.get(col_name, "") + " " + val).strip()
                continue

        if len(non_empty_cols) < 2:
            continue
            
        row_text = " ".join(v for v in columns.values() if v.strip()).lower()
        if any(k in row_text for k in ["terms", "conditions", "payment details", "notes"]): break
        if output and any(k in row_text for k in ["subtotal", "grand total", "amount due"]): break

        current_row_top = min(w['top'] for w in row)
        if prev_row_top is not None and fixed_gap > 0:
            if abs(current_row_top - prev_row_top) > fixed_gap * 2.6: consecutive_large_gaps += 1
            else: consecutive_large_gaps = 0
            if len(output) >= 2 and consecutive_large_gaps >= 2: break

        output.append({"row_id": len(output) + 1, "columns": dict(columns)})
        prev_row_top = current_row_top

    if not output: return []
    if sum(1 for r in output if re.search(r"[$€£]?\d[\d,]*\.?\d{0,2}", " ".join(str(v) for v in r["columns"].values()))) == 0: return []
    return output


def try_parse_flow_layout_table(page, score):
    try:
        words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False, extra_attrs=[])
        if not words or len(words) < 10: return None
        processed_rows = extract_flow_layout_table(page, words)
        if not processed_rows: return None
        if len(processed_rows) >= 2: return processed_rows
        cols = {k.lower(): str(v) for k, v in processed_rows[0].get("columns", {}).items() if v}
        joined = " ".join(cols.values())
        if bool(re.search(r"[$€£]?\d[\d,]*\.?\d{0,2}", joined)) and any(k in cols for k in ["description", "item", "qty", "quantity", "price", "total", "amount"]):
            return processed_rows
        return None
    except Exception as e:
        print(f"    [flow-layout] Fallback failed: {e}")
        return None

# =============================================================================
# Helper functions for semi-structured inference
# =============================================================================

def _infer_column_types(rows: list[list], num_cols: int) -> list[str]:
    types = ["unknown"] * num_cols
    for col_idx in range(num_cols):
        col_values = [sanitise_cell(row[col_idx]) for row in rows[1:] if col_idx < len(row) and sanitise_cell(row[col_idx])]
        if not col_values: continue
        date_count, amount_count, balance_count, long_text_count = 0, 0, 0, 0
        for v in col_values:
            if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', v): date_count += 1
            if re.match(r'^\d+\.?\d{0,2}$', v): amount_count += 1
            if re.search(r'(CR|DR)$', v): balance_count += 1
            if len(v) > 20: long_text_count += 1
        total = len(col_values)
        if date_count / total >= 0.4: types[col_idx] = "date"
        elif balance_count / total >= 0.50: types[col_idx] = "balance"
        elif amount_count / total >= 0.70: types[col_idx] = "amount"
        elif long_text_count / total >= 0.60: types[col_idx] = "description"
    return types


def _generate_column_names(column_types: list[str]) -> list[str]:
    names, type_counter, fallback_counter = [], {}, 0
    for col_type in column_types:
        if col_type == "unknown":
            fallback_counter += 1
            names.append(f"column_{fallback_counter}")
        else:
            count = type_counter.get(col_type, 0)
            type_counter[col_type] = count + 1
            names.append(col_type if count == 0 else f"{col_type}_{count + 1}")
    return names

def try_parse_semi_structured_table(raw_table: list[list], score: int) -> list[dict] | None:
    if len(raw_table) <= 5: return None
    non_empty_rows = [r for r in raw_table if not is_empty_row(r)]
    if len(non_empty_rows) < 5: return None
    num_cols = max(len(r) for r in non_empty_rows)
    if num_cols < 2: return None
    column_types = _infer_column_types(non_empty_rows, num_cols)
    column_names = _generate_column_names(column_types)
    processed_rows = []
    row_id = 1
    for raw_row in non_empty_rows[1:]:
        if is_empty_row(raw_row): continue
        cells = (list(raw_row) + [None] * max(0, num_cols - len(raw_row)))[:num_cols]
        processed_rows.append({"row_id": row_id, "columns": {col_name: sanitise_cell(cell_value) for col_name, cell_value in zip(column_names, cells)}})
        row_id += 1
    return processed_rows if processed_rows else None

# =============================================================================
# Main table extraction functions
# =============================================================================

def table_score(raw_table: list[list]) -> tuple[int, list[str]]:
    reasons = []
    score = 100
    non_empty_rows = [r for r in raw_table if not is_empty_row(r)]
    num_rows = len(non_empty_rows)
    if num_rows < MIN_ROWS:
        reasons.append(f"too few non-empty rows ({num_rows} < {MIN_ROWS})")
        return 0, reasons
    header_row, data_rows = non_empty_rows[0], non_empty_rows[1:]
    num_cols = len(header_row)
    if num_cols < MIN_COLS:
        reasons.append(f"too few columns ({num_cols} < {MIN_COLS})")
        return 0, reasons
    header_cells = [sanitise_cell(c) for c in header_row if sanitise_cell(c)]
    for cell in header_cells:
        if cell and (":" in cell or len(cell) > MAX_HEADER_LEN * 2):
            reasons.append(f"header looks like KV or too long ({len(cell)} chars)")
            return 0, reasons
    if not header_cells:
        reasons.append("header row is entirely blank")
        return 0, reasons
    long_headers = [c for c in header_cells if len(c) > MAX_HEADER_LEN]
    if long_headers:
        penalty = min(60, len(long_headers) * 20)
        reasons.append(f"{len(long_headers)} header cell(s) exceed {MAX_HEADER_LEN} chars (penalty -{penalty})")
        score -= penalty
    unique_ratio = len(set(header_cells)) / len(header_cells)
    if unique_ratio < 0.6:
        penalty = 20
        reasons.append(f"low header uniqueness ({unique_ratio:.0%}, penalty -{penalty})")
        score -= penalty
    all_cells = [sanitise_cell(c) for row in non_empty_rows for c in row]
    filled = [c for c in all_cells if c is not None]
    fill_ratio = len(filled) / max(len(all_cells), 1)
    if fill_ratio < MIN_FILL_RATIO:
        reasons.append(f"fill ratio too low ({fill_ratio:.0%} < {MIN_FILL_RATIO:.0%})")
        return 0, reasons
    row_lengths = [len(r) for r in data_rows]
    if row_lengths:
        modal_len = Counter(row_lengths).most_common(1)[0][0]
        consistent = sum(1 for l in row_lengths if l == modal_len) / len(row_lengths)
        if consistent < ROW_CONSISTENCY:
            penalty = 15
            reasons.append(f"low row-length consistency ({consistent:.0%} < {ROW_CONSISTENCY:.0%}, penalty -{penalty})")
            score -= penalty
    if num_cols >= 2 and data_rows:
        col_text_lengths = [0] * num_cols
        for row in data_rows:
            for idx, cell in enumerate(row[:num_cols]):
                val = sanitise_cell(cell)
                if val: col_text_lengths[idx] += len(val)
        total_text = sum(col_text_lengths)
        if total_text > 0:
            max_col_share = max(col_text_lengths) / total_text
            if max_col_share > 0.90:
                reasons.append(f"single column holds {max_col_share:.0%} of text")
                return 0, reasons
    giant_cells = [c for c in filled if len(c) > 250]
    if giant_cells:
        penalty = min(40, len(giant_cells) * 15)
        reasons.append(f"{len(giant_cells)} giant cell(s) (>250 chars, penalty -{penalty})")
        score -= penalty
    return max(0, score), reasons


def is_valid_table(raw_table: list[list]) -> tuple[bool, int, list[str]]:
    score, reasons = table_score(raw_table)
    return score >= max(40, VALID_SCORE_THRESHOLD - 10), score, reasons


def extract_tables(page: pdfplumber.page.Page) -> list[list[list]]:
    tables = []
    try:
        tables = page.extract_tables(table_settings=TABLE_SETTINGS)
        if tables: return tables
    except Exception as e: print(f"      [table] Strategy 1 (lines) failed: {e}")
    try:
        tables = page.extract_tables(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
        if tables: return tables
    except Exception as e: print(f"      [table] Strategy 2 (text) failed: {e}")
    try:
        found_tables = list(page.find_tables())
        if found_tables:
            tables = [t.extract() for t in found_tables if t.extract()]
            if tables: return tables
    except Exception as e: print(f"      [table] Strategy 3 (grid) failed: {e}")
    return tables or []


def process_table(raw_table: list[list]) -> list[dict]:
    if not raw_table: return []
    header_row, data_start = None, 0
    for idx, row in enumerate(raw_table):
        if not is_empty_row(row):
            header_row, data_start = row, idx + 1
            break
    if header_row is None: return []
    headers, seen = [], {}
    for raw_h in header_row:
        name = to_snake_case(str(raw_h)) if sanitise_cell(raw_h) else "column"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else: seen[name] = 0
        headers.append(name)
    rows, row_id = [], 1
    for raw_row in raw_table[data_start:]:
        if is_empty_row(raw_row): continue
        cells = (list(raw_row) + [None] * max(0, len(headers) - len(raw_row)))[:len(headers)]
        rows.append({"row_id": row_id, "columns": {h: sanitise_cell(v) for h, v in zip(headers, cells)}})
        row_id += 1
    return rows


def _is_split_header_token(token: str) -> bool:
    t = (token or "").strip().lower()
    if not t: return False
    if t in {".", "_", "-"}: return True
    return len(re.sub(r"[^a-z]", "", t)) <= 3 and len(t) <= 6


def _table_semantic_quality(processed_rows: list[dict]) -> tuple[bool, list[str]]:
    reasons = []
    if not processed_rows: return False, ["empty table"]
    headers = list(processed_rows[0].get("columns", {}).keys())
    if headers:
        split_ratio = sum(1 for h in headers if _is_split_header_token(h)) / max(len(headers), 1)
        if split_ratio >= 0.45: reasons.append(f"split/gibberish headers ({split_ratio:.0%})")
    meta_markers = {"invoice", "issued", "issue", "due", "date", "account", "payment", "address", "contact", "branch"}
    sample_rows = processed_rows[: min(8, len(processed_rows))]
    meta_hits, checked = 0, 0
    for row in sample_rows:
        row_text = " ".join(str(v).lower() for v in row.get("columns", {}).values() if v)
        if not row_text: continue
        checked += 1
        if any(m in row_text for m in meta_markers): meta_hits += 1
    if checked > 0 and meta_hits / checked >= 0.60: reasons.append(f"metadata-heavy rows ({meta_hits / checked:.0%})")
    if not sum(1 for row in processed_rows for v in row.get("columns", {}).values() if v and re.search(r"[$€£]?\d[\d,]*\.?\d{0,2}", str(v))):
        reasons.append("no amount-like values")
    return len(reasons) == 0, reasons
