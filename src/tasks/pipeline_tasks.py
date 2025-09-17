"""
Celery tasks for document processing pipeline.
"""

import asyncio
import logging
import traceback
from celery import chain
from src.celery_app import celery_app
from src.integration.pipeline import process_document_with_ocr, process_document_with_llm
from src.dms.service import DmsService
from src.dms.adapters import AzureBlobStorageClient, PostgresMetadataRepository
from src.config import AppConfig
import psycopg2
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)

# Load configuration
app_config = AppConfig()


def _get_dms_service() -> DmsService:
    """Get DMS service instance for task execution."""
    # Use environment-aware storage configuration
    from src.storage.storage import get_storage
    
    # Initialize database connection
    pg_conn = psycopg2.connect(
        host=app_config.database.host,
        port=app_config.database.port,
        database=app_config.database.name,
        user=app_config.database.user,
        password=app_config.database.password,
    )
    
    # Use the singleton storage instance
    storage = get_storage()
    storage_client = AzureBlobStorageClient(storage.blob_service_client)
    metadata_repo = PostgresMetadataRepository(pg_conn)
    
    return DmsService(storage_client=storage_client, metadata_repository=metadata_repo)


def handle_extraction_error(document_id: str, exception: Exception, task_name: str) -> None:
    """
    Handle extraction errors by logging and updating status.
    
    Args:
        document_id: The document ID that failed
        exception: The exception that occurred
        task_name: Name of the task that failed
    """
    error_message = f"Task {task_name} failed for document {document_id}: {str(exception)}"
    logger.error(error_message, exc_info=True)
    
    # Update extraction job status to "failed" and store error message
    try:
        dms_service = _get_dms_service()
        jobs = dms_service.get_extraction_jobs(document_id)
        if jobs:
            job_id = jobs[0]['id']  # Get the most recent job
            dms_service.update_extraction_job(job_id, "failed", error_message)
        
        logger.info(f"Updated status to 'failed' for document {document_id}")
    except Exception as status_update_error:
        logger.error(f"Failed to update status for document {document_id}: {status_update_error}")


@celery_app.task(bind=True)
def process_ocr_task(self, document_id: str) -> str:
    """Celery task to perform OCR processing."""
    task_name = "process_ocr"
    logger.info(f"Starting {task_name} for document {document_id}")
    
    try:
        # Get document from DMS
        dms_service = _get_dms_service()
        document = dms_service.get_document(document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        
        # Download document content
        blob_data = dms_service.download_document(document_id)
        if not blob_data:
            raise ValueError(f"Could not download document {document_id}")
        
        # Process with OCR
        asyncio.run(process_document_with_ocr(document_id, blob_data, dms_service))
        
        logger.info(f"Successfully completed {task_name} for document {document_id}")
        return document_id
    except Exception as e:
        handle_extraction_error(document_id, e, task_name)
        # Re-raise the exception to mark the task as failed
        raise


@celery_app.task(bind=True)
def process_llm_task(self, document_id: str) -> str:
    """Celery task to perform LLM processing."""
    task_name = "process_llm"
    logger.info(f"Starting {task_name} for document {document_id}")
    
    try:
        # Get OCR results from storage
        from src.storage.storage import get_storage, Stage
        
        storage = get_storage()
        ocr_document_data = storage.download_document_data(document_id, Stage.OCR, ".json")
        
        if not ocr_document_data:
            raise ValueError(f"OCR results not found for document {document_id}")
        
        # Extract the actual OCR processing results from the document data structure
        ocr_results = ocr_document_data.get("data", {})
        if not ocr_results:
            raise ValueError(f"Invalid OCR data structure for document {document_id}")
        
        # Process with LLM
        dms_service = _get_dms_service()
        asyncio.run(process_document_with_llm(document_id, ocr_results, dms_service))
        
        logger.info(f"Successfully completed {task_name} for document {document_id}")
        return document_id
    except Exception as e:
        handle_extraction_error(document_id, e, task_name)
        # Re-raise the exception to mark the task as failed
        raise


@celery_app.task(bind=True)
def run_full_pipeline_task(self, document_id: str) -> str:
    """Celery task to run the full extraction pipeline."""
    task_name = "run_full_pipeline"
    logger.info(f"Starting {task_name} for document {document_id}")
    
    try:
        # Create a chain of tasks
        pipeline = chain(
            process_ocr_task.s(document_id=document_id),
            process_llm_task.s(),
        )
        
        # Execute the pipeline
        result = pipeline.apply_async()
        
        logger.info(f"Successfully initiated {task_name} for document {document_id}")
        return document_id
    except Exception as e:
        handle_extraction_error(document_id, e, task_name)
        # Re-raise the exception to mark the task as failed
        raise


@celery_app.task(bind=True)
def process_document_async(self, document_id: str) -> str:
    """Main entry point for async document processing."""
    task_name = "process_document_async"
    logger.info(f"Starting {task_name} for document {document_id}")
    
    try:
        # Update document status to indicate processing has started
        dms_service = _get_dms_service()
        dms_service.mark_ocr_running(document_id)
        
        # Start the full pipeline
        pipeline_result = run_full_pipeline_task.delay(document_id)
        
        logger.info(f"Successfully initiated async processing for document {document_id}")
        return document_id
    except Exception as e:
        handle_extraction_error(document_id, e, task_name)
        # Re-raise the exception to mark the task as failed
        raise


