import json
from typing import Dict, Any, Optional
from datetime import datetime

from .storage import get_storage, Stage


def delete_ocr_results_from_bucket(document_uuid: str) -> bool:
    """
    Delete OCR results from blob storage bucket.
    
    Args:
        document_uuid: Unique identifier for the document
        
    Returns:
        True if deleted successfully, False otherwise
    """
    storage_client = get_storage()
    
    success = storage_client.delete_blob(document_uuid, Stage.OCR, ".json")
    
    if success:
        print(f"OCR results deleted from bucket for document: {document_uuid}")
    else:
        print(f"OCR results not found for deletion: {document_uuid}")
    
    return success


def list_ocr_results_in_bucket() -> list[str]:
    """
    List all OCR result files in the bucket.
    
    Returns:
        List of document UUIDs that have OCR results
    """
    storage_client = get_storage()
    
    try:
        blob_names = storage_client.list_blobs_in_stage(Stage.OCR)
        
        # Extract UUIDs from blob names (remove .json extension)
        document_uuids = []
        for blob_name in blob_names:
            if blob_name.endswith('.json'):
                uuid_part = blob_name.replace('.json', '')
                document_uuids.append(uuid_part)
        
        print(f"Found {len(document_uuids)} OCR result files in bucket")
        return document_uuids
    except Exception as e:
        print(f"Failed to list OCR results in bucket: {e}")
        return []
