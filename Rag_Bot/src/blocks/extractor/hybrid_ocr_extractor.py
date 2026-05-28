import re
import pytesseract
import pdfplumber
from typing import List, Dict, Any
from collections import defaultdict
from pathlib import Path
from PIL import Image
from core.interfaces import IExtractor
from api.config import TESSERACT_PATH
from extraction.parser import TABLE_SETTINGS, TEXT_X_TOLERANCE, TEXT_Y_TOLERANCE

# Configuration
pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

TABLE_BBOX_Y_PADDING = 15.0
KV_KEY_MAX_TOKENS = 8

class HybridOCRExtractor(IExtractor):
    """
    Hybrid extractor: Uses Tesseract OCR for text/forms and pdfplumber for tables.
    Includes robust fallback logic for complex tables.
    """

    def __init__(self, tesseract_path: str = TESSERACT_PATH):
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path

    def ocr_region(self, img: Image.Image, box_pixels: List[int], margin: int = 2) -> str:
        x0, y0, x1, y1 = box_pixels
        x0 = max(0, x0 - margin)
        y0 = max(0, y0 - margin)
        x1 = min(img.width, x1 + margin)
        y1 = min(img.height, y1 + margin)
        cropped = img.crop((x0, y0, x1, y1))
        return pytesseract.image_to_string(cropped, config='--psm 6').strip()

    def extract(self, pdf_path: str, regions: List[Dict[str, Any]], **kwargs) -> List[Dict[str, Any]]:
        extracted_data = []
        pdf = pdfplumber.open(pdf_path)
        
        # We group regions by page to avoid reopening/re-rendering
        regions_by_page = defaultdict(list)
        for r in regions:
            regions_by_page[r["page"]].append(r)

        for page_num, page_regions in regions_by_page.items():
            page = pdf.pages[page_num - 1]
            # Use the image from the first region or render it
            img = page_regions[0].get("image")
            
            for region in page_regions:
                # Process the region and its children recursively
                result = self._extract_region_recursive(page, img, region, page_num, **kwargs)
                if result:
                    extracted_data.append(result)

        pdf.close()
        return extracted_data

    def _extract_region_recursive(self, page, img, region, page_num, **kwargs) -> Dict[str, Any]:
        """Recursively extracts a region and its children."""
        label = region["type"]
        bbox_pdf = region["bbox"]
        bbox_pixels = region.get("bbox_pixels")
        conf = region.get("confidence", 0.0)
        
        extracted_item = {
            "type": label,
            "page": page_num,
            "bbox": bbox_pdf,
            "metadata": {"confidence": conf},
            "nested_content": []
        }

        # 1. Extract Parent Content
        if label == "Table":
            x0, y0, x1, y1 = bbox_pdf
            expanded_y0 = max(0, y0 - TABLE_BBOX_Y_PADDING)
            expanded_bbox = (x0, expanded_y0, x1, y1)
            cropped_page = page.crop(expanded_bbox)
            
            grid_rows = self._extract_grid_table(cropped_page)
            flow_rows = self._extract_flow_table(cropped_page)
            
            # Simple selection (can be enhanced with the conflict/variant logic)
            chosen_rows = grid_rows if grid_rows else flow_rows
            if chosen_rows:
                extracted_item["type"] = "table"
                extracted_item["data"] = chosen_rows
                extracted_item["metadata"]["method"] = "grid" if grid_rows else "flow"
        
        elif label in ["Checkbox-Selected", "Checkbox-Unselected"]:
            ocr_text = self.ocr_region(img, bbox_pixels) if img else ""
            extracted_item["type"] = "checkbox"
            extracted_item["checked"] = label == "Checkbox-Selected"
            extracted_item["label"] = ocr_text
            
        else:
            # Standard Text/KV/Form extraction
            ocr_text = self.ocr_region(img, bbox_pixels) if img else ""
            extracted_item["type"] = "text"
            extracted_item["role"] = label.lower()
            extracted_item["data"] = ocr_text

        # 2. Recursively Extract Children
        children = region.get("children", [])
        for child in children:
            child_result = self._extract_region_recursive(page, img, child, page_num, **kwargs)
            if child_result:
                extracted_item["nested_content"].append(child_result)

        return extracted_item

    def _extract_grid_table(self, cropped_page):
        # Implementation using existing process_table logic
        # For brevity, I'll use the version from the user's code
        raw_tables = cropped_page.extract_tables(table_settings=TABLE_SETTINGS)
        if not raw_tables:
            raw_tables = cropped_page.extract_tables(
                table_settings={"vertical_strategy":"text","horizontal_strategy":"text"}
            )
        
        for tbl in raw_tables:
            # check validity (simplified for now, using a helper)
            if self._is_valid_table(tbl):
                return self._process_raw_table(tbl)
        return None

    def _is_valid_table(self, raw_table):
        # Logic from Cell 5
        non_empty = [r for r in raw_table if any(c and str(c).strip() for c in r)]
        if len(non_empty) < 2: return False
        header = non_empty[0]
        if len(header) < 2: return False
        return True

    def _process_raw_table(self, raw_table):
        # Logic from Cell 6
        header_row, data_start = None, 0
        for idx, row in enumerate(raw_table):
            if any(c and str(c).strip() for c in row):
                header_row = row; data_start = idx+1; break
        if not header_row: return []
        
        headers = []
        seen = {}
        for h in header_row:
            name = self._to_snake_case(str(h)) if h else "column"
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else: seen[name] = 0
            headers.append(name)
            
        rows = []
        for ridx, row in enumerate(raw_table[data_start:], 1):
            if not any(c and str(c).strip() for c in row): continue
            cells = list(row) + [None]*max(0, len(headers)-len(row))
            cells = cells[:len(headers)]
            rows.append({"row_id": ridx, "columns": {h: str(v).strip() if v else None for h,v in zip(headers, cells)}})
        return rows

    def _to_snake_case(self, text: str) -> str:
        text = re.sub(r"[\s\-/]+", "_", text.strip().lower())
        return re.sub(r"_+", "_", text)

    def _is_bank_statement(self, text: str) -> bool:
        """Logic from original pipeline."""
        if not text: return False
        text_lower = text.lower()
        bank_keywords = [
            "statement", "transaction", "balance", "withdrawal", "deposit",
            "credit", "debit", "posted", "available balance", "account summary",
            "beginning balance", "ending balance", "checking", "savings",
            "credit card", "payment due", "minimum payment"
        ]
        matches = sum(1 for kw in bank_keywords if kw in text_lower)
        return matches >= 3

    def _headers_similar(self, headers_a: List[str], headers_b: List[str], threshold: float = 0.4) -> bool:
        """Logic from original pipeline."""
        if not headers_a or not headers_b: return False
        def normalize(h: str) -> set:
            cleaned = re.sub(r'[^a-z0-9]+', ' ', h.lower()).strip()
            return set(cleaned.split())
        tokens_a = set().union(*(normalize(h) for h in headers_a))
        tokens_b = set().union(*(normalize(h) for h in headers_b))
        if not tokens_a or not tokens_b: return False
        intersection = tokens_a & tokens_b
        union = tokens_a | tokens_b
        return (len(intersection) / len(union)) >= threshold

    def _extract_flow_table(self, cropped_page):
        """Logic from Cell 8: Robust flow-layout table extraction."""
        words = cropped_page.extract_words(
            x_tolerance=TEXT_X_TOLERANCE,
            y_tolerance=TEXT_Y_TOLERANCE,
            keep_blank_chars=False
        )
        if not words:
            return []

        rows = self._cluster_words_to_rows(words, y_tol=6)
        if not rows:
            return []
            
        header_row = self._detect_header_row(rows)
        if header_row is None:
            return []
            
        boundaries = self._get_column_boundaries(header_row)
        header_names = [re.sub(r'[^a-zA-Z0-9]+','_',w['text'].strip().lower()) for w in sorted(header_row, key=lambda w: w['x0'])]
        
        data = [r for r in rows if min(w['top'] for w in r) > min(w['top'] for w in header_row)]
        output = []
        for r in data:
            raw = self._assign_words_to_columns(r, boundaries)
            cols = {}
            for idx in range(len(boundaries)):
                val = raw.get(f"column_{idx+1}","").strip()
                if val:
                    cols[header_names[idx] if idx<len(header_names) else f"col_{idx+1}"] = val
            if len(cols)>=2:
                output.append({"row_id": len(output)+1, "columns": cols})
        
        # Validation: check if at least one row has numeric-like content
        if output and any(re.search(r"[\d,.]+", " ".join(str(v) for v in r["columns"].values())) for r in output):
            return output
        return []

    def _cluster_words_to_rows(self, words, y_tol=6):
        rows = []
        for w in sorted(words, key=lambda w: w['top']):
            placed = False
            for r in rows:
                if abs(r[0]['top'] - w['top']) < y_tol:
                    r.append(w); placed = True; break
            if not placed: rows.append([w])
        for r in rows: r.sort(key=lambda w: w['x0'])
        return rows

    def _detect_header_row(self, rows):
        """Detect best header using role-vocab, penalties, and lookahead evidence."""
        if not rows: return None
        candidates = []
        for idx, row in enumerate(rows):
            if not self._is_candidate_header(row): continue
            score = self._header_score(rows, idx, row)
            candidates.append((idx, row, score))
        if not candidates: return None
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][1]

    def _is_candidate_header(self, row):
        if len(row)<3: return False
        x_range = max(w['x1'] for w in row)-min(w['x0'] for w in row)
        if x_range<120: return False
        texts = [w['text'] for w in row]
        if sum(1 for t in texts if re.fullmatch(r'[\d.,$%-]+',t))/len(texts)>=0.5: return False
        if ":" in " ".join(texts).lower(): return False
        return True

    def _header_score(self, rows, idx, row):
        TABLE_ROLE_TOKENS = {"item","description","qty","quantity","rate","price","amount","total","debit","credit","balance"}
        META_HEADER_TOKENS = {"billed","invoice","issued","issue","date","due","account","address","contact","payment"}
        
        tokens = {re.sub(r"[^a-z0-9]+","",w["text"].lower()) for w in row if re.sub(r"[^a-z0-9]+","",w["text"].lower())}
        row_text = " ".join(w['text'] for w in row).lower()
        score = 0
        score += len(tokens & TABLE_ROLE_TOKENS) * 6
        score -= len(tokens & META_HEADER_TOKENS) * 4
        
        x_range = max(w['x1'] for w in row) - min(w['x0'] for w in row)
        if x_range > 200: score += 2
        
        if self._has_column_structure(rows, idx): score += 8
        else: score -= 6
        
        if re.search(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', row_text): score -= 4
        return score

    def _has_column_structure(self, rows, start_idx, window=6):
        if start_idx+1>=len(rows): return False
        x_pos = []
        for i in range(start_idx+1, min(start_idx+1+window, len(rows))):
            for w in rows[i]: x_pos.append(w['x0'])
        if not x_pos: return False
        x_pos.sort()
        clusters = []; cur = [x_pos[0]]
        for x in x_pos[1:]:
            if x - cur[-1] <= 25: cur.append(x)
            else: clusters.append(cur); cur = [x]
        if cur: clusters.append(cur)
        return len(clusters)>=2

    def _get_column_boundaries(self, header_row):
        hr = sorted(header_row, key=lambda w: w['x0'])
        bounds = []
        for i,w in enumerate(hr):
            left = w['x0']
            right = (w['x1']+hr[i+1]['x0'])/2 if i+1<len(hr) else w['x1']+50
            bounds.append((left, right))
        return bounds

    def _assign_words_to_columns(self, row, boundaries):
        cols = defaultdict(str)
        if not boundaries: return cols
        for w in row:
            cx = (w['x0']+w['x1'])/2
            idx = next((i for i,(l,r) in enumerate(boundaries) if l<=cx<r), None)
            if idx is None: idx = min(range(len(boundaries)), key=lambda i: abs((boundaries[i][0]+boundaries[i][1])/2 - cx))
            key = f"column_{idx+1}"
            if cols[key]: cols[key] += " "
            cols[key] += w['text']
        return cols
