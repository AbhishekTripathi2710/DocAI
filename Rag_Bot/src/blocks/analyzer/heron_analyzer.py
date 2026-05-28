import threading
import torch
import fitz  # PyMuPDF
from PIL import Image
from typing import List, Dict, Any
from pathlib import Path
from transformers import RTDetrV2ForObjectDetection, RTDetrImageProcessor
from core.interfaces import IAnalyzer

class HeronLayoutAnalyzer(IAnalyzer):
    """
    Analyzes document structure using the ds4sd/docling-layout-heron-101 model.
    """
    
    CLASSES = {
        0: "Caption", 1: "Footnote", 2: "Formula", 3: "List-item",
        4: "Page-footer", 5: "Page-header", 6: "Picture", 7: "Section-header",
        8: "Table", 9: "Text", 10: "Title", 11: "Document Index", 12: "Code",
        13: "Checkbox-Selected", 14: "Checkbox-Unselected", 15: "Form", 16: "Key-Value Region"
    }

    _model = None
    _processor = None
    _lock = threading.Lock()

    def __init__(self, model_name: str = "ds4sd/docling-layout-heron-101", device: str = None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        if HeronLayoutAnalyzer._model is None:
            print(f"Loading Heron model: {model_name} on {self.device}...")
            HeronLayoutAnalyzer._processor = RTDetrImageProcessor.from_pretrained(model_name)
            HeronLayoutAnalyzer._model = RTDetrV2ForObjectDetection.from_pretrained(model_name).to(self.device)
            HeronLayoutAnalyzer._model.eval()

    def pixel_to_pdf_coords(self, box_pixels, img_width, img_height, pdf_width, pdf_height):
        """Convert a bounding box from image pixels [x0,y0,x1,y1] to PDF points."""
        x0, y0, x1, y1 = box_pixels
        scale_x = pdf_width / img_width
        scale_y = pdf_height / img_height
        return [
            x0 * scale_x,
            y0 * scale_y,
            x1 * scale_x,
            y1 * scale_y
        ]

    def analyze(self, pdf_path: str, threshold: float = 0.5, dpi: int = 200, **kwargs) -> List[Dict[str, Any]]:
        doc = fitz.open(pdf_path)
        all_regions = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            # Convert PDF page to image
            matrix = fitz.Matrix(dpi/72, dpi/72)
            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # PDF dimensions
            pdf_w, pdf_h = page.rect.width, page.rect.height
            img_w, img_h = img.size

            # Model inference - Protected by thread lock to prevent cross-document leakage
            with HeronLayoutAnalyzer._lock:
                inputs = self._processor(images=[img], return_tensors="pt").to(self.device)
                with torch.no_grad():
                    outputs = self._model(**inputs)
                
                results = self._processor.post_process_object_detection(
                    outputs, 
                    target_sizes=torch.tensor([img.size[::-1]]), 
                    threshold=threshold
                )[0]

            for score, label_id, box in zip(results["scores"], results["labels"], results["boxes"]):
                box_pixels = [round(i) for i in box.tolist()]
                box_pdf = self.pixel_to_pdf_coords(box_pixels, img_w, img_h, pdf_w, pdf_h)
                class_name = self.CLASSES[label_id.item()]
                
                all_regions.append({
                    "page": page_num + 1,
                    "type": class_name,
                    "bbox": box_pdf,
                    "bbox_pixels": box_pixels,
                    "confidence": round(score.item(), 3),
                    "image": img # Optional: pass the image reference if extractor needs it
                })
        
        doc.close()
        return all_regions
