import logging
from typing import Dict, Any
from .pipeline import process_document_with_ocr, process_document_with_llm
from ..visualization.ocr_visualization import visualize_ocr_results
from ..storage.storage import get_storage, Stage

logger = logging.getLogger(__name__)


async def integrated_pipeline(document_id: str, filename: str, blob_path: str) -> Dict[str, Any]:
    """
    Complete integrated pipeline combining document loading from blob storage, OCR and LLM processing.
    
    Args:
        document_id: Unique identifier for the document
        filename: Original filename of the document
        blob_path: Path to the document in blob storage
        
    Returns:
        Dictionary containing complete processing results
    """
    print(f"Starting integrated pipeline for document: {document_id}")
    print(f"  - Filename: {filename}")
    print(f"  - Blob path: {blob_path}")
    
    # Step 1: Load document from blob storage
    print("Step 1: Loading document from blob storage...")
    storage_client = get_storage()
    pdf_data = storage_client.download_blob(document_id, Stage.RAW, ".pdf")
    if pdf_data is None:
        raise FileNotFoundError(f"Document not found in blob storage: {document_id}")
    print(f"  - Loaded document: {len(pdf_data)} bytes")
    
    # Step 2: Process with OCR
    print("Step 2: Processing document with OCR...")
    ocr_results = await process_document_with_ocr(document_id, pdf_data)
    print(f"  - OCR processing completed: {len(ocr_results['normalized_lines'])} normalized elements")
    
    # Step 3: Process with LLM
    print("Step 3: Processing document with LLM...")
    llm_results = await process_document_with_llm(document_id, ocr_results)
    print(f"  - LLM processing completed: {len(llm_results['extraction_results']['extracted_fields'])} fields extracted")
    
    # Step 4: Generate visualizations
    print("Step 4: Generating OCR visualizations...")
    visualize_ocr_results(document_id, ocr_results["original_lines"])
    print("  - Visualizations generated and saved to blob storage")
    
    # Step 5: Compile final results
    print("Step 5: Pipeline completed successfully!")
    final_results = {
        "document_id": document_id,
        "filename": filename,
        "blob_path": blob_path,
        "ocr_results": ocr_results,
        "llm_results": llm_results,
        "processing_summary": {
            "total_ocr_elements": len(ocr_results['original_lines']),
            "normalized_elements": len(ocr_results['normalized_lines']),
            "extracted_fields": len(llm_results['extraction_results']['extracted_fields']),
            "validation_errors": len(llm_results['extraction_results']['validation_results'])
        }
    }
    
    return final_results
