"""
Async document processing service using Celery.
"""

import logging
from typing import Optional
from src.dms.service import DmsService
from src.dms.adapters import AzureBlobStorageClient, PostgresMetadataRepository
from src.config import AppConfig
import psycopg2
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

# Load configuration
app_config = AppConfig()


class AsyncDocumentProcessor:
    """Service for triggering async document processing."""
    
    def __init__(self):
        """Initialize the async processor with DMS service."""
        # Initialize clients
        connection_string = (
            "DefaultEndpointsProtocol=http;"
            f"AccountName={app_config.azure.storage.account_name};"
            f"AccountKey={app_config.azure.storage.account_key};"
            f"BlobEndpoint=http://localhost:10000/devstoreaccount1;"
        )
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        pg_conn = psycopg2.connect(
            host=app_config.database.host,
            port=app_config.database.port,
            database=app_config.database.name,
            user=app_config.database.user,
            password=app_config.database.password,
        )
        
        storage_client = AzureBlobStorageClient(blob_service_client)
        metadata_repo = PostgresMetadataRepository(pg_conn)
        
        self.dms_service = DmsService(storage_client=storage_client, metadata_repository=metadata_repo)
    
    def trigger_processing(self, document_id: str) -> Optional[str]:
        """
        Trigger async processing for a document.
        
        Args:
            document_id: The document ID to process
            
        Returns:
            Task ID if successful, None if failed
        """
        try:
            # Verify document exists and is ready for processing
            document = self.dms_service.get_document(document_id)
            if not document:
                logger.error(f"Document {document_id} not found")
                return None
            
            if document.get('textextraction_status') != 'ready':
                logger.warning(f"Document {document_id} is not ready for processing (status: {document.get('textextraction_status')})")
                return None
            
            # Import task dynamically to avoid circular imports
            from src.tasks.pipeline_tasks import process_document_async
            
            # Trigger async processing
            task = process_document_async.delay(document_id)
            logger.info(f"Triggered async processing for document {document_id}, task ID: {task.id}")
            
            return task.id
            
        except Exception as e:
            logger.error(f"Failed to trigger processing for document {document_id}: {e}")
            return None
    
    def get_processing_status(self, document_id: str) -> dict:
        """
        Get the current processing status for a document.
        
        Args:
            document_id: The document ID to check
            
        Returns:
            Dictionary with status information
        """
        try:
            document = self.dms_service.get_document(document_id)
            if not document:
                return {"error": "Document not found"}
            
            jobs = self.dms_service.get_extraction_jobs(document_id)
            
            return {
                "document_id": document_id,
                "text_extraction_status": document.get('textextraction_status'),
                "processing_status": document.get('processing_status'),
                "extraction_jobs": jobs,
            }
            
        except Exception as e:
            logger.error(f"Failed to get status for document {document_id}: {e}")
            return {"error": str(e)}
