import uuid
import logging
from typing import List, Optional
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Response
from fastapi.responses import StreamingResponse

from .models import (
    DocumentUploadResponse, DocumentStatusResponse, DocumentResultsResponse,
    ProcessingStatus, ErrorResponse, HealthCheckResponse, OcrElementData,
    ExtractedFieldData, ProcessingSummaryData, BoundingBoxData
)
from ..async_processing import AsyncDocumentProcessor
from ..storage.storage import get_storage, Stage
from ..dms.service import DmsService
from ..dms.adapters import AzureBlobStorageClient, PostgresMetadataRepository
from ..config import AppConfig
import psycopg2
from azure.storage.blob import BlobServiceClient

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize configuration and services
app_config = AppConfig()


def get_dms_service() -> DmsService:
    """Create and return DMS service instance."""
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
    metadata_repository = PostgresMetadataRepository(pg_conn)
    
    return DmsService(storage_client=storage_client, metadata_repository=metadata_repository)


async def process_document_background(document_id: str, filename: str, file_data: bytes):
    """Background task to process uploaded document."""
    try:
        logger.info(f"Starting background processing for document {document_id}")
        
        # Store raw PDF in blob storage
        storage_client = get_storage()
        storage_client.upload_blob(
            uuid=document_id,
            stage=Stage.RAW,
            ext=".pdf",
            data=file_data
        )
        
        # Initialize async processor and trigger processing
        async_processor = AsyncDocumentProcessor()
        task_id = async_processor.trigger_processing(document_id)
        
        if task_id:
            logger.info(f"Successfully triggered async processing for document {document_id}, task ID: {task_id}")
        else:
            logger.error(f"Failed to trigger async processing for document {document_id}")
            
    except Exception as e:
        logger.error(f"Error in background processing for document {document_id}: {e}")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
) -> DocumentUploadResponse:
    """
    Upload a PDF document for processing.
    
    Args:
        file: PDF file to process
        
    Returns:
        DocumentUploadResponse with document ID and status
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Read file data
        file_data = await file.read()
        if len(file_data) == 0:
            raise HTTPException(status_code=400, detail="Empty file uploaded")
        
        # Store document in DMS
        dms_service = get_dms_service()
        dms_service.store_document(
            document_id=document_id,
            filename=file.filename,
            file_data=file_data
        )
        
        # Schedule background processing
        background_tasks.add_task(
            process_document_background,
            document_id,
            file.filename,
            file_data
        )
        
        logger.info(f"Document uploaded successfully: {document_id} ({file.filename})")
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status=ProcessingStatus.PENDING,
            message="Document uploaded successfully and processing started"
        )
        
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")


@router.get("/status/{document_id}", response_model=DocumentStatusResponse)
async def get_document_status(document_id: str) -> DocumentStatusResponse:
    """
    Get processing status for a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        DocumentStatusResponse with current status
    """
    try:
        dms_service = get_dms_service()
        document = dms_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Map DMS status to API status - prioritize processing_status if available
        processing_status = document.get('processing_status')
        textextraction_status = document.get('textextraction_status', 'ready')
        
        status_mapping = {
            'ready': ProcessingStatus.PENDING,
            'ocr_running': ProcessingStatus.OCR_RUNNING,
            'ocr running': ProcessingStatus.OCR_RUNNING,
            'llm_running': ProcessingStatus.LLM_RUNNING,  
            'llm running': ProcessingStatus.LLM_RUNNING,
            'done': ProcessingStatus.COMPLETED,
            'completed': ProcessingStatus.COMPLETED,
            'error': ProcessingStatus.FAILED,
            'failed': ProcessingStatus.FAILED
        }
        
        # Use processing_status if available, otherwise fallback to textextraction_status
        status_to_map = processing_status if processing_status else textextraction_status
        api_status = status_mapping.get(status_to_map, ProcessingStatus.PENDING)
        
        return DocumentStatusResponse(
            document_id=document_id,
            status=api_status,
            filename=document.get('filename'),
            upload_timestamp=document.get('upload_timestamp'),
            processing_started=document.get('processing_started'),
            processing_completed=document.get('processing_completed'),
            error_message=document.get('error_message')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document status: {str(e)}")


@router.get("/results/{document_id}", response_model=DocumentResultsResponse)
async def get_document_results(document_id: str) -> DocumentResultsResponse:
    """
    Get complete processing results for a document.
    
    Args:
        document_id: Document identifier
        
    Returns:
        DocumentResultsResponse with complete results
    """
    try:
        # Get document metadata
        dms_service = get_dms_service()
        document = dms_service.get_document(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if processing is complete
        processing_status = document.get('processing_status')
        textextraction_status = document.get('textextraction_status')
        
        is_complete = (processing_status == 'done') or (textextraction_status == 'done')
        if not is_complete:
            raise HTTPException(
                status_code=202,
                detail="Document processing not yet complete"
            )
        
        # Get processing results from blob storage
        storage_client = get_storage()
        
        # Load OCR results
        ocr_data = storage_client.download_blob(document_id, Stage.OCR, ".json")
        llm_data = storage_client.download_blob(document_id, Stage.LLM, ".json")
        
        ocr_elements = []
        extracted_fields = []
        processing_summary = None
        ocr_results = None
        llm_results = None
        
        if ocr_data:
            import json
            ocr_results = json.loads(ocr_data.decode('utf-8'))
            # Check if data is nested under 'data' key
            if 'data' in ocr_results:
                ocr_data_content = ocr_results['data']
            else:
                ocr_data_content = ocr_results
            
            if 'original_lines' in ocr_data_content:
                for element in ocr_data_content['original_lines']:
                    ocr_elements.append(OcrElementData(
                        text=element['text'],
                        confidence=element['confidence'],
                        bbox=BoundingBoxData(**element['bbox']),
                        page_num=element['page_num']
                    ))
        
        if llm_data:
            llm_results = json.loads(llm_data.decode('utf-8'))
            # Check if data is nested under 'data' key
            if 'data' in llm_results:
                llm_data_content = llm_results['data']
            else:
                llm_data_content = llm_results
            
            extraction_results = llm_data_content.get('extraction_results', {})
            
            if 'extracted_fields' in extraction_results:
                for field_name, field_data in extraction_results['extracted_fields'].items():
                    # Convert value to string, handling different data types
                    raw_value = field_data.get('value')
                    if raw_value is not None:
                        extracted_value = str(raw_value)
                    else:
                        extracted_value = None
                        
                    extracted_fields.append(ExtractedFieldData(
                        field_name=field_name,
                        extracted_value=extracted_value,
                        confidence_score=field_data.get('confidence'),
                        source_ocr_elements=field_data.get('source_ocr_elements', [])
                    ))
        
        # Check if visualization exists (check for page 1)
        try:
            has_visualization = storage_client.blob_exists(document_id, Stage.ANNOTATED, "_page_1.png")
            logger.info(f"Visualization check for {document_id}: {has_visualization}")
        except Exception as e:
            logger.warning(f"Error checking visualization for {document_id}: {e}")
            has_visualization = False
        
        # Create processing summary
        if ocr_data and llm_data:
            normalized_count = 0
            validation_errors_count = 0
            
            if ocr_results and 'data' in ocr_results:
                normalized_count = len(ocr_results['data'].get('normalized_lines', []))
            elif ocr_results:
                normalized_count = len(ocr_results.get('normalized_lines', []))
                
            if llm_results and 'data' in llm_results:
                llm_content = llm_results['data']
                validation_errors_count = len(llm_content.get('extraction_results', {}).get('validation_results', []))
            elif llm_results:
                validation_errors_count = len(llm_results.get('extraction_results', {}).get('validation_results', []))
            
            processing_summary = ProcessingSummaryData(
                total_ocr_elements=len(ocr_elements),
                normalized_elements=normalized_count,
                extracted_fields=len(extracted_fields),
                validation_errors=validation_errors_count
            )
        
        # Map status
        status_mapping = {
            'done': ProcessingStatus.COMPLETED,
            'completed': ProcessingStatus.COMPLETED,
            'error': ProcessingStatus.FAILED,
            'failed': ProcessingStatus.FAILED
        }
        
        processing_status = document.get('processing_status')
        textextraction_status = document.get('textextraction_status')
        status_to_map = processing_status if processing_status else textextraction_status
        
        api_status = status_mapping.get(status_to_map, ProcessingStatus.COMPLETED)
        
        return DocumentResultsResponse(
            document_id=document_id,
            filename=document.get('filename', 'unknown'),
            status=api_status,
            processing_summary=processing_summary,
            extracted_fields=extracted_fields,
            ocr_elements=ocr_elements,
            has_visualization=has_visualization
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get document results: {str(e)}")


@router.get("/visualization/{document_id}")
async def get_document_visualization(document_id: str, page: int = 1) -> StreamingResponse:
    """
    Get visualization image with OCR bounding boxes for a document page.
    
    Args:
        document_id: Document identifier
        page: Page number (default 1)
        
    Returns:
        PNG image with OCR overlays
    """
    try:
        storage_client = get_storage()
        
        # Check if document exists
        dms_service = get_dms_service()
        document = dms_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get visualization image
        visualization_data = storage_client.download_blob(
            document_id, Stage.ANNOTATED, f"_page_{page}.png"
        )
        
        if not visualization_data:
            raise HTTPException(
                status_code=404,
                detail=f"Visualization not found for document {document_id}, page {page}"
            )
        
        # Return image as streaming response
        return StreamingResponse(
            BytesIO(visualization_data),
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename=visualization_{document_id}_page_{page}.png"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting document visualization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get visualization: {str(e)}")


@router.get("/documents", response_model=List[DocumentStatusResponse])
async def list_documents(limit: int = 50, offset: int = 0) -> List[DocumentStatusResponse]:
    """
    List all documents with their processing status.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        
    Returns:
        List of DocumentStatusResponse objects
    """
    try:
        dms_service = get_dms_service()
        documents = dms_service.list_documents(limit=limit, offset=offset)
        
        result = []
        for doc in documents:
            # Map DMS status to API status
            status_mapping = {
                'ready': ProcessingStatus.PENDING,
                'ocr_running': ProcessingStatus.OCR_RUNNING,
                'ocr running': ProcessingStatus.OCR_RUNNING,
                'llm_running': ProcessingStatus.LLM_RUNNING,
                'llm running': ProcessingStatus.LLM_RUNNING,
                'done': ProcessingStatus.COMPLETED,
                'completed': ProcessingStatus.COMPLETED,
                'error': ProcessingStatus.FAILED,
                'failed': ProcessingStatus.FAILED
            }
            
            processing_status = doc.get('processing_status')
            textextraction_status = doc.get('textextraction_status', 'ready')
            status_to_map = processing_status if processing_status else textextraction_status
            
            api_status = status_mapping.get(status_to_map, ProcessingStatus.PENDING)
            
            result.append(DocumentStatusResponse(
                document_id=doc['document_id'],
                status=api_status,
                filename=doc.get('filename'),
                upload_timestamp=doc.get('upload_timestamp'),
                processing_started=doc.get('processing_started'),
                processing_completed=doc.get('processing_completed'),
                error_message=doc.get('error_message')
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """
    Health check endpoint to verify service status.
    
    Returns:
        HealthCheckResponse with service status
    """
    services = {}
    overall_status = "healthy"
    
    # Check database connection
    try:
        dms_service = get_dms_service()
        # Try a simple operation to verify connection
        dms_service.list_documents(limit=1)
        services["database"] = "healthy"
    except Exception as e:
        services["database"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # Check blob storage
    try:
        storage_client = get_storage()
        storage_client.ensure_all_containers_ready()
        services["blob_storage"] = "healthy"
    except Exception as e:
        services["blob_storage"] = f"unhealthy: {str(e)}"
        overall_status = "unhealthy"
    
    # Check Redis/Celery (basic connection test)
    try:
        from ..celery_app import celery_app
        # Try to inspect active workers
        celery_app.control.inspect().active()
        services["celery"] = "healthy"
    except Exception as e:
        services["celery"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"  # Celery issues don't make the whole service unhealthy
    
    # Check Ollama service and model availability
    try:
        import requests
        response = requests.get('http://127.0.0.1:11435/api/tags', timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            llama_models = [m for m in models if 'llama3.1:8b' in m.get('name', '')]
            
            if llama_models:
                services["ollama"] = "healthy"
            else:
                services["ollama"] = "downloading: Model llama3.1:8b not found, likely downloading"
                overall_status = "degraded"
        else:
            services["ollama"] = f"unhealthy: HTTP {response.status_code}"
            overall_status = "degraded"
    except Exception as e:
        if "connection" in str(e).lower():
            services["ollama"] = "starting: Service not ready"
        else:
            services["ollama"] = f"unhealthy: {str(e)}"
        overall_status = "degraded"  # Ollama issues don't make the whole service unhealthy
    
    return HealthCheckResponse(
        status=overall_status,
        timestamp=datetime.now(),
        services=services
    )
