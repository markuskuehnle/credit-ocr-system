"""
Label-value pair extraction from OCR results.
"""

from typing import List, Dict, Any
from .spatial_analysis import detect_lines_on_same_row, reconstruct_split_text_elements


def extract_label_value_pairs(ocr_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract label-value pairs from OCR lines by detecting text on the same row.
    
    Args:
        ocr_lines: List of OCR results with bbox information
        
    Returns:
        List of label-value pairs with metadata
    """
    pairs = []
    
    # Group lines by row using improved spatial analysis
    row_groups = detect_lines_on_same_row(ocr_lines)
    
    for group in row_groups:
        # First, try to reconstruct split text elements in this row
        reconstructed_group = reconstruct_split_text_elements(group)
        
        if len(reconstructed_group) == 2:
            # Potential label-value pair
            left_item = reconstructed_group[0]  # Already sorted by x-coordinate
            right_item = reconstructed_group[1]
            
            # Simple heuristic: if left item ends with colon or is shorter, it's likely a label
            left_text = left_item['text'].strip()
            right_text = right_item['text'].strip()
            
            # Enhanced label detection - consider reconstructed elements as labels
            is_label_value = (
                left_text.endswith(':') or 
                left_text.endswith('?') or
                len(left_text) < 30 or  # Short text is more likely to be a label
                '/' in left_text or  # Reconstructed elements with "/" are often labels
                (left_item.get('type') == 'reconstructed' and not any(char in left_text for char in '€$£¥0123456789'))  # Reconstructed non-value text
            )
            
            # Also check if right item looks like a value
            right_looks_like_value = (
                any(char in right_text for char in '€$£¥0123456789') or  # Contains numbers/currency
                len(right_text) > len(left_text)  # Longer text might be a value
            )
            
            if (is_label_value or right_looks_like_value) and len(right_text) > 0:
                # Calculate combined bounding box
                combined_bbox = {
                    'x1': min(left_item['bbox']['x1'], right_item['bbox']['x1']),
                    'y1': min(left_item['bbox']['y1'], right_item['bbox']['y1']),
                    'x2': max(left_item['bbox']['x2'], right_item['bbox']['x2']),
                    'y2': max(left_item['bbox']['y2'], right_item['bbox']['y2']),
                }
                combined_bbox['width'] = combined_bbox['x2'] - combined_bbox['x1']
                combined_bbox['height'] = combined_bbox['y2'] - combined_bbox['y1']
                
                pairs.append({
                    "label": left_text.rstrip(':').rstrip('?').strip(),
                    "value": right_text,
                    "page": left_item['page_num'],
                    "confidence": min(left_item['confidence'], right_item['confidence']),
                    "bounding_box": combined_bbox
                })
        elif len(reconstructed_group) > 2:
            # Multiple items on same line - try to find label-value patterns
            # Strategy 1: Look for traditional label-value pairs
            for i in range(len(reconstructed_group) - 1):
                left_item = reconstructed_group[i]
                right_item = reconstructed_group[i + 1]
                
                left_text = left_item['text'].strip()
                right_text = right_item['text'].strip()
                
                # Enhanced detection for reconstructed elements
                is_valid_label_value = (
                    left_text.endswith(':') or 
                    left_text.endswith('?') or
                    '/' in left_text or  # Reconstructed labels often have "/"
                    (left_item.get('type') == 'reconstructed' and not any(char in left_text for char in '€$£¥0123456789')) or
                    any(char in right_text for char in '€$£¥0123456789')  # Right side has value-like content
                )
                
                if is_valid_label_value and len(right_text) > 0:
                    combined_bbox = {
                        'x1': min(left_item['bbox']['x1'], right_item['bbox']['x1']),
                        'y1': min(left_item['bbox']['y1'], right_item['bbox']['y1']),
                        'x2': max(left_item['bbox']['x2'], right_item['bbox']['x2']),
                        'y2': max(left_item['bbox']['y2'], right_item['bbox']['y2']),
                    }
                    combined_bbox['width'] = combined_bbox['x2'] - combined_bbox['x1']
                    combined_bbox['height'] = combined_bbox['y2'] - combined_bbox['y1']
                    
                    pairs.append({
                        "label": left_text.rstrip(':').rstrip('?').strip(),
                        "value": right_text,
                        "page": left_item['page_num'],
                        "confidence": min(left_item['confidence'], right_item['confidence']),
                        "bounding_box": combined_bbox
                    })
            
            # Strategy 2: Conservative handling of 3+ element rows
            # Only create pairs for clear label-value patterns, avoid complex combinations
            if len(reconstructed_group) == 3:
                # Check if we have a clear pattern: label1 + label2 + value
                last_element = reconstructed_group[-1]
                last_text = last_element['text'].strip()
                
                # Only if the last element clearly looks like a value
                if any(char in last_text for char in '€$£¥0123456789') and len(last_text) > 1:
                    # Combine the first two elements as label
                    first_two = reconstructed_group[:2]
                    label_texts = [elem['text'].strip() for elem in first_two]
                    combined_label = ' / '.join(label_texts)
                    
                    # Create combined bounding box
                    combined_bbox = {
                        'x1': min(elem['bbox']['x1'] for elem in reconstructed_group),
                        'y1': min(elem['bbox']['y1'] for elem in reconstructed_group),
                        'x2': max(elem['bbox']['x2'] for elem in reconstructed_group),
                        'y2': max(elem['bbox']['y2'] for elem in reconstructed_group),
                    }
                    combined_bbox['width'] = combined_bbox['x2'] - combined_bbox['x1']
                    combined_bbox['height'] = combined_bbox['y2'] - combined_bbox['y1']
                    
                    avg_confidence = sum(elem['confidence'] for elem in reconstructed_group) / len(reconstructed_group)
                    
                    pairs.append({
                        "label": combined_label,
                        "value": last_text,
                        "page": reconstructed_group[0]['page_num'],
                        "confidence": avg_confidence,
                        "bounding_box": combined_bbox,
                        "type": "simple_three_element"
                    })
            # For 4+ elements, avoid creating complex combinations that mess up table structure
    
    return pairs
