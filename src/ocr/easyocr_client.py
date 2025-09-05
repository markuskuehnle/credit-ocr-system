"""
EasyOCR client for text extraction with bounding boxes.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from pdf2image import convert_from_path
import easyocr


def extract_text_bboxes_with_ocr(pdf_input) -> Tuple[List[Dict[str, Any]], List[Any]]:
    """
    Extract text, bounding boxes, confidence scores, and page number using EasyOCR.
    
    Args:
        pdf_input: Either a path to the PDF file (str) or PDF bytes
        
    Returns:
        Tuple of (ocr_results, pdf_images)
        - ocr_results: List of dictionaries with text, bbox, confidence, page_num
        - pdf_images: List of PIL images for visualization
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Initialize EasyOCR reader for English
    reader = easyocr.Reader(['en'])
    
    # Handle both file path and bytes input
    if isinstance(pdf_input, str):
        # File path
        logger.info(f"Processing PDF from file path: {pdf_input}")
        pdf_images: List[Any] = convert_from_path(pdf_input, dpi=150)
    else:
        # PDF bytes - save to temporary file
        import tempfile
        import os
        logger.info(f"Processing PDF from bytes (size: {len(pdf_input)} bytes)")
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_path = temp_file.name
        temp_file.write(pdf_input)
        temp_file.close()
        
        try:
            pdf_images: List[Any] = convert_from_path(temp_path, dpi=150)
            logger.info(f"Successfully converted PDF to {len(pdf_images)} images")
        except Exception as e:
            logger.error(f"Failed to convert PDF: {e}")
            raise
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    all_results: List[Dict[str, Any]] = []
    
    for page_index, image in enumerate(pdf_images):
        # Convert PIL image to numpy array
        image_array = np.array(image)
        
        # Extract text with EasyOCR
        ocr_results = reader.readtext(image_array)
        
        for result in ocr_results:
            bbox_points = result[0]  # List of 4 corner points
            text = result[1]
            confidence = result[2]
            
            # Convert bbox points to x1, y1, x2, y2 format
            x_coords = [point[0] for point in bbox_points]
            y_coords = [point[1] for point in bbox_points]
            x1, x2 = min(x_coords), max(x_coords)
            y1, y2 = min(y_coords), max(y_coords)
            
            all_results.append({
                "page_num": page_index + 1,
                "text": text,
                "confidence": confidence,
                "bbox": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "width": x2 - x1,
                    "height": y2 - y1
                }
            })
    
    return all_results, pdf_images
