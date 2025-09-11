import matplotlib.pyplot as plt
import matplotlib.patches as patches
from typing import List, Dict, Any
from io import BytesIO
from pdf2image import convert_from_bytes
from ..storage.storage import get_storage, Stage


def visualize_ocr_results(document_id: str, ocr_results: List[Dict[str, Any]]) -> None:
    """
    Visualize OCR bounding boxes, text, and confidence on images and save to blob storage.
    
    Args:
        document_id: Unique identifier for the document
        ocr_results: List of OCR results with bounding boxes and confidence scores
    """
    # Download PDF from blob storage
    storage_client = get_storage()
    pdf_data = storage_client.download_blob(document_id, Stage.RAW, ".pdf")
    if pdf_data is None:
        raise FileNotFoundError(f"PDF not found in blob storage: {document_id}")
    
    # Convert PDF to images with SAME DPI as OCR processing (150)
    print("  - Converting PDF to images for visualization...")
    pdf_images = convert_from_bytes(pdf_data, dpi=150)
    print(f"  - Converted PDF to {len(pdf_images)} images")
    
    # Group OCR results by page
    page_to_elements: Dict[int, List[Dict[str, Any]]] = {}
    for result in ocr_results:
        page_num: int = result["page_num"]
        if page_num not in page_to_elements:
            page_to_elements[page_num] = []
        page_to_elements[page_num].append(result)
    
    # Create visualizations for each page
    for page_num, elements in page_to_elements.items():
        image = pdf_images[page_num - 1]
        fig, ax = plt.subplots(1, 1, figsize=(15, 20))
        ax.imshow(image)
        ax.set_title(f'Page {page_num} - OCR Text Extraction', fontsize=16)
        
        for element in elements:
            bbox = element['bbox']
            text = element['text']
            confidence = element['confidence']
            color = 'green' if confidence >= 0.9 else 'orange' if confidence >= 0.7 else 'red'
            
            rect = patches.Rectangle(
                (bbox['x1'], bbox['y1']),
                bbox['width'],
                bbox['height'],
                linewidth=1.5,
                edgecolor=color,
                facecolor='none',
                alpha=0.8
            )
            ax.add_patch(rect)
            
            display_text = text[:30] + ('...' if len(text) > 30 else '')
            label = f"{display_text} ({confidence*100:.1f}%)"
            ax.annotate(
                label,
                (bbox['x1'], bbox['y1'] - 5),
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor=color, alpha=0.9),
                fontsize=7,
                color='black',
                ha='left',
                va='bottom'
            )
        
        legend_elements = [
            patches.Patch(color='green', label='High (≥90%)'),
            patches.Patch(color='orange', label='Med (70-89%)'),
            patches.Patch(color='red', label='Low (<70%)')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        ax.set_xlim(0, image.width)
        ax.set_ylim(image.height, 0)
        ax.axis('off')
        plt.tight_layout()
        
        # Save visualization to blob storage
        buffer = BytesIO()
        plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
        buffer.seek(0)
        
        # Upload to blob storage with ANNOTATED stage
        storage_client.upload_blob(
            uuid=document_id,
            stage=Stage.ANNOTATED,
            ext=f"_page_{page_num}.png",
            data=buffer.getvalue(),
            overwrite=True
        )
        
        annotated_blob_path = storage_client.blob_path(document_id, Stage.ANNOTATED, f"_page_{page_num}.png")
        print(f"  - Visualization saved to: {Stage.ANNOTATED.value}/{annotated_blob_path}")
        
        plt.show()
        plt.close()
        
        high = sum(1 for e in elements if e['confidence'] >= 0.9)
        med = sum(1 for e in elements if 0.7 <= e['confidence'] < 0.9)
        low = sum(1 for e in elements if e['confidence'] < 0.7)
        avg = sum(e['confidence'] for e in elements) / len(elements) if elements else 0
        print(f"Page {page_num}: {len(elements)} elements | Avg: {avg*100:.1f}% | H:{high} M:{med} L:{low}")
