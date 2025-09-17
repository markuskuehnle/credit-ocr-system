"""
OCR post-processing functions for normalization and structuring.
"""

from typing import List, Dict, Any
from .label_value_extraction import extract_label_value_pairs


def convert_numpy_types(obj):
    """
    Convert NumPy types to native Python types for JSON serialization.
    
    Args:
        obj: Object that may contain NumPy types
        
    Returns:
        Object with NumPy types converted to Python types
    """
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    elif hasattr(obj, 'item'):  # NumPy types
        return obj.item()
    else:
        return obj


def normalize_ocr_lines(ocr_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Normalize OCR lines into generic structured items.
    
    Returns a list of items like:
    - {'type': 'label_value', 'label': ..., 'value': ..., 'page': ..., 'confidence': ...}
    - {'type': 'text_line', 'text': ..., 'page': ..., 'confidence': ...}
    
    Args:
        ocr_lines: List of OCR results with bbox information
        
    Returns:
        List of normalized structured items
    """
    structured = []

    # First convert EasyOCR format to expected format
    converted_lines = []
    for line in ocr_lines:
        converted_lines.append({
            "type": "line",
            "text": line["text"],
            "page_num": line["page_num"],
            "confidence": float(line["confidence"]) if hasattr(line["confidence"], 'item') else line["confidence"],
            "bbox": line["bbox"]
        })

    # Detect label-value pairs first
    pairs = extract_label_value_pairs(converted_lines)

    # Add label-value pairs
    for p in pairs:
        structured.append({
            "type": "label_value",
            "label": p["label"],
            "value": p["value"],
            "page": p["page"],
            "confidence": p["confidence"],
            "bounding_box": p.get("bounding_box")
        })

    # Add all lines as text lines (excluding those already captured in label-value pairs)
    used_texts = set()
    for pair in pairs:
        used_texts.add(pair["label"])
        used_texts.add(pair["value"])
    
    for line in converted_lines:
        if line["type"] != "line":
            continue
        if line.get("bounding_box") is None:
            continue
        
        # Skip if this text was already used in a label-value pair
        clean_text = line["text"].strip().rstrip(':').rstrip('?').strip()
        if clean_text not in used_texts:
            structured.append({
                "type": "text_line",
                "text": line["text"].strip(),
                "page": line["page_num"],
                "confidence": line.get("confidence"),
                "bounding_box": line.get("bbox")
            })

    # Convert NumPy types to Python types for JSON serialization
    return convert_numpy_types(structured)
