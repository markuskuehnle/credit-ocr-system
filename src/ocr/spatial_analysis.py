"""
Spatial analysis functions for OCR text reconstruction.
"""

from typing import List, Dict, Any


def detect_lines_on_same_row(ocr_lines: List[Dict[str, Any]], tolerance: float = 15.0) -> List[List[Dict[str, Any]]]:
    """
    Simple and conservative row detection to avoid mixing up table structure.
    
    Args:
        ocr_lines: List of OCR results with bbox information
        tolerance: Maximum vertical distance for same-row detection
        
    Returns:
        List of grouped lines, where each group contains elements on the same row
    """
    grouped_lines = []
    remaining_lines = ocr_lines.copy()
    
    while remaining_lines:
        current_line = remaining_lines.pop(0)
        current_group = [current_line]
        current_y_center = (current_line['bbox']['y1'] + current_line['bbox']['y2']) / 2
        current_height = current_line['bbox']['y2'] - current_line['bbox']['y1']
        
        # Find lines that are clearly on the same row (conservative approach)
        lines_to_remove = []
        for i, line in enumerate(remaining_lines):
            line_y_center = (line['bbox']['y1'] + line['bbox']['y2']) / 2
            line_height = line['bbox']['y2'] - line['bbox']['y1']
            
            # Conservative same-row criteria
            center_distance = abs(current_y_center - line_y_center)
            avg_height = (current_height + line_height) / 2
            
            # Only group if centers are very close
            if center_distance < tolerance and center_distance < avg_height * 0.5:
                current_group.append(line)
                lines_to_remove.append(i)
        
        # Remove grouped lines
        for i in reversed(lines_to_remove):
            remaining_lines.pop(i)
        
        # Sort by x-coordinate
        current_group.sort(key=lambda x: x['bbox']['x1'])
        grouped_lines.append(current_group)
    
    return grouped_lines


def reconstruct_split_text_elements(row_elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Carefully reconstruct only clearly split text elements (very conservative approach).
    
    Args:
        row_elements: List of OCR elements on the same row
        
    Returns:
        List of reconstructed elements with merged text where appropriate
    """
    if len(row_elements) <= 1:
        return row_elements
    
    reconstructed = []
    i = 0
    
    while i < len(row_elements):
        current_element = row_elements[i]
        current_text = current_element['text'].strip()
        
        # Only look at the immediate next element (no long chains)
        if i + 1 < len(row_elements):
            next_element = row_elements[i + 1]
            next_text = next_element['text'].strip()
            
            # Calculate horizontal gap between elements
            horizontal_gap = next_element['bbox']['x1'] - current_element['bbox']['x2']
            
            # Very conservative merging - only for obvious splits
            should_merge = (
                horizontal_gap < 20 and  # Very close horizontally
                len(current_text) >= 3 and len(next_text) >= 3 and  # Both have meaningful length
                not any(char in current_text for char in '€$£¥0123456789') and  # Neither is a value
                not any(char in next_text for char in '€$£¥0123456789') and
                # Additional conservative check: avoid merging if elements are too far apart vertically
                abs(current_element['bbox']['y1'] - next_element['bbox']['y1']) < 5
            )
            
            if should_merge:
                # Merge only these two elements
                combined_text = f"{current_text} / {next_text}"
                
                combined_bbox = {
                    'x1': min(current_element['bbox']['x1'], next_element['bbox']['x1']),
                    'y1': min(current_element['bbox']['y1'], next_element['bbox']['y1']),
                    'x2': max(current_element['bbox']['x2'], next_element['bbox']['x2']),
                    'y2': max(current_element['bbox']['y2'], next_element['bbox']['y2']),
                }
                combined_bbox['width'] = combined_bbox['x2'] - combined_bbox['x1']
                combined_bbox['height'] = combined_bbox['y2'] - combined_bbox['y1']
                
                reconstructed_element = {
                    'text': combined_text,
                    'confidence': (current_element['confidence'] + next_element['confidence']) / 2,
                    'bbox': combined_bbox,
                    'page_num': current_element['page_num'],
                    'original_elements': [current_element, next_element],
                    'type': 'reconstructed'
                }
                
                reconstructed.append(reconstructed_element)
                i += 2  # Skip both elements
            else:
                # No merge, keep original
                reconstructed.append(current_element)
                i += 1
        else:
            # Last element, keep as is
            reconstructed.append(current_element)
            i += 1
    
    return reconstructed
