import threading
from pathlib import Path
from typing import Dict, Any, List
# pyrefly: ignore [missing-import]
from core.interfaces import IAnalyzer, IExtractor, IProcessor
class RAGPipelineOrchestrator:
    """
    Orchestrates the modular RAG pipeline blocks.
    """
    _lock = threading.Lock()

    def __init__(
        self, 
        analyzer: IAnalyzer, 
        extractor: IExtractor, 
        processor: IProcessor = None,
        contextualizer: Any = None
    ):
        self.analyzer = analyzer
        self.extractor = extractor
        self.processor = processor
        self.contextualizer = contextualizer

    async def process_pdf(self, pdf_path: str, doc_type: str = "generic") -> Dict[str, Any]:
        pdf_path_obj = Path(pdf_path)
        
        # Step 1: Analyze structure - PROTECTED BY GLOBAL LOCK
        # This prevents shared model/processor state from leaking across documents
        with RAGPipelineOrchestrator._lock:
            print(f"Analyzing layout for {pdf_path_obj.name} (Type: {doc_type})...")
            regions = self.analyzer.analyze(str(pdf_path_obj), doc_type=doc_type)
            
            # Step 2: Build Region Tree (Hierarchy)
            region_tree = self._resolve_region_tree(regions)
            print(f"Built hierarchy: {len(regions)} regions organized into {len(region_tree)} top-level blocks.")
            
            # Step 3: Extract content recursively
            print(f"Extracting content from {len(region_tree)} top-level regions...")
            raw_content = self.extractor.extract(str(pdf_path_obj), region_tree, doc_type=doc_type)
        
        # Step 4: Semantic Processing
        if self.processor:
            return self.processor.process(raw_content)
        
        # Default: group by page
        pages_output = {}
        for item in raw_content:
            page_num = item["page"]
            if page_num not in pages_output:
                pages_output[page_num] = []
            
            # Remove redundant 'page' from item for JSON clarity
            content_item = item.copy()
            del content_item["page"]
            pages_output[page_num].append(content_item)
            
        formatted_pages = []
        for page_num in sorted(pages_output.keys()):
            formatted_pages.append({
                "page_number": page_num,
                "content": pages_output[page_num]
            })
            
        return {
            "document": {
                "metadata": {
                    "source": pdf_path_obj.name,
                    "total_pages": len(formatted_pages)
                },
                "pages": formatted_pages
            }
        }

    def _resolve_region_tree(self, regions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Organizes flat regions into a parent-child tree based on geometric containment.
        Sorts by area (largest first) so parents are processed before their children.
        """
        if not regions:
            return []

        # Sort by area descending (largest boxes first)
        sorted_regions = sorted(
            regions, 
            key=lambda r: (r["bbox"][2] - r["bbox"][0]) * (r["bbox"][3] - r["bbox"][1]), 
            reverse=True
        )

        # Logical parent types that are allowed to contain others
        PARENT_TYPES = {"Key-Value Region", "Table", "Form", "Document Index", "Section-header", "Text"}
        
        roots = []
        consumed_ids = set()

        for i, p_region in enumerate(sorted_regions):
            p_id = id(p_region)
            if p_id in consumed_ids:
                continue
            
            if p_region["type"] not in PARENT_TYPES:
                roots.append(p_region)
                continue

            p_region["children"] = []
            p_bbox = p_region["bbox"]
            p_page = p_region["page"]

            # Look for children among the remaining smaller regions
            for j in range(i + 1, len(sorted_regions)):
                c_region = sorted_regions[j]
                c_id = id(c_region)
                
                if c_id in consumed_ids or c_region["page"] != p_page:
                    continue

                if self._is_contained_in(c_region["bbox"], p_bbox):
                    p_region["children"].append(c_region)
                    consumed_ids.add(c_id)

            roots.append(p_region)

        # Recursively apply to children if needed (currently 1-level deep is usually enough for DINO)
        return roots

    def _is_contained_in(self, inner_bbox: List[float], outer_bbox: List[float], threshold: float = 0.6) -> bool:
        """
        Checks if inner_bbox is significantly contained within outer_bbox.
        Returns True if >60% of inner area is inside outer.
        """
        ix0, iy0, ix1, iy1 = inner_bbox
        ox0, oy0, ox1, oy1 = outer_bbox
        
        # Intersection
        x_overlap = max(0, min(ix1, ox1) - max(ix0, ox0))
        y_overlap = max(0, min(iy1, oy1) - max(iy0, oy0))
        intersection_area = x_overlap * y_overlap
        
        inner_area = (ix1 - ix0) * (iy1 - iy0)
        if inner_area <= 0: return False
            
        return (intersection_area / inner_area) >= threshold
