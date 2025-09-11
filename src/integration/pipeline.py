import logging
from typing import Dict, Any
from ..ocr.easyocr_client import extract_text_bboxes_with_ocr
from ..ocr.postprocess import normalize_ocr_lines, convert_numpy_types
from ..llm.field_extractor import extract_fields_with_llm
from ..llm.config import load_document_config, DocumentTypeConfig
from ..llm.client import OllamaClient
from ..llm.client import GenerativeLlm
from ..storage.storage import get_storage, Stage
from ..config.system import load_system_config

logger = logging.getLogger(__name__)


async def process_document_with_ocr(document_id: str, pdf_data: bytes) -> Dict[str, Any]:
    """
    Process document with OCR and save results to blob storage.
    
    Args:
        document_id: Unique identifier for the document
        pdf_data: PDF file data as bytes
        
    Returns:
        Dictionary containing OCR processing results
    """
    print(f"Processing document {document_id} with OCR...")
    
    # Step 1: OCR Processing
    print("  - Extracting text with OCR...")
    ocr_results, pdf_images = extract_text_bboxes_with_ocr(pdf_data)
    print(f"  - Extracted {len(ocr_results)} text elements")
    
    # Step 2: Normalize OCR results
    print("  - Normalizing OCR results...")
    normalized_results = normalize_ocr_lines(ocr_results)
    print(f"  - Normalized to {len(normalized_results)} structured items")
    
    # Step 3: Convert NumPy types
    print("  - Converting NumPy types...")
    ocr_results_converted = convert_numpy_types(ocr_results)
    normalized_results_converted = convert_numpy_types(normalized_results)
    
    # Step 4: Prepare OCR results
    ocr_processing_results = {
        "document_id": document_id,
        "processing_timestamp": "2024-01-01T00:00:00Z",  # This would be dynamic in production
        "processing_metadata": {
            "total_elements": len(ocr_results_converted),
            "normalized_elements": len(normalized_results_converted),
            "processing_method": "easyocr"
        },
        "normalized_lines": normalized_results_converted,
        "original_lines": ocr_results_converted
    }
    
    # Step 5: Save to blob storage
    print("  - Saving OCR results to blob storage...")
    storage_client = get_storage()
    storage_client.upload_document_data(
        uuid=document_id,
        stage=Stage.OCR,
        ext=".json",
        data=ocr_processing_results,
        metadata={
            "stage": "ocr",
            "notebook": "04_integration",
            "processing_method": "easyocr"
        }
    )
    
    print(f"  - OCR processing completed for document {document_id}")
    return ocr_processing_results


async def process_document_with_llm(document_id: str, ocr_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process document with LLM field extraction and save results to blob storage.
    
    Args:
        document_id: Unique identifier for the document
        ocr_results: OCR processing results from process_document_with_ocr
        
    Returns:
        Dictionary containing LLM processing results
    """
    print(f"Processing document {document_id} with LLM...")
    
    # Step 1: Load system configuration
    system_config = load_system_config()
    if not system_config:
        raise ValueError("Failed to load system configuration")
    
    # Step 2: Load document configuration
    doc_config = load_document_config("config/document_types.conf")
    
    # Step 3: Initialize LLM client
    llm_config = GenerativeLlm(
        url=system_config['llm']['url'],
        model_name=system_config['llm']['model_name']
    )
    llm_client = OllamaClient(llm_config.url, llm_config.model_name)
    
    # Step 4: Extract fields using LLM
    print("  - Extracting fields with LLM...")
    extraction_result = await extract_fields_with_llm(
        ocr_lines=ocr_results["normalized_lines"],
        doc_config=doc_config["credit_request"],
        original_ocr_lines=ocr_results["original_lines"]
    )
    
    # Step 5: Prepare LLM results
    llm_processing_results = {
        "document_id": document_id,
        "processing_timestamp": "2024-01-01T00:00:00Z",  # This would be dynamic in production
        "processing_metadata": {
            "model_name": system_config['llm']['model_name'],
            "model_url": system_config['llm']['url'],
            "processing_method": "llama3.1:8b"
        },
        "extraction_results": extraction_result
    }
    
    # Step 6: Save to blob storage
    print("  - Saving LLM results to blob storage...")
    storage_client = get_storage()
    storage_client.upload_document_data(
        uuid=document_id,
        stage=Stage.LLM,
        ext=".json",
        data=llm_processing_results,
        metadata={
            "stage": "llm",
            "notebook": "04_integration",
            "processing_method": "llama3.1:8b"
        }
    )
    
    print(f"  - LLM processing completed for document {document_id}")
    return llm_processing_results
