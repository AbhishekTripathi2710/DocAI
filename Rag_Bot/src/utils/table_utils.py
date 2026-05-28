from typing import List, Dict, Any

def table_to_markdown(rows: List[Dict[str, Any]]) -> str:
    """
    Converts a list of row dictionaries to a clean Markdown table.
    Expects rows in the format: [{"row_id": 1, "columns": {"header1": "val1", ...}}, ...]
    """
    if not rows:
        return ""

    # 1. Extract headers from the first row
    headers = list(rows[0].get("columns", {}).keys())
    if not headers:
        return ""

    # 2. Build header row
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"

    # 3. Build data rows
    data_lines = []
    for row in rows:
        cols = row.get("columns", {})
        row_vals = [str(cols.get(h, "") or "").replace("|", "\\|").strip() for h in headers]
        data_lines.append("| " + " | ".join(row_vals) + " |")

    return "\n".join([header_line, separator_line] + data_lines)
