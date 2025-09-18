from __future__ import annotations

import logging
import uuid
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any
import mimetypes

from .interfaces import StorageClient, MetadataRepository

logger = logging.getLogger(__name__)


class DmsService:
    """Service for DMS operations."""

    def __init__(self, storage_client: StorageClient, metadata_repository: MetadataRepository) -> None:
        self.storage_client = storage_client
        self.metadata_repository = metadata_repository

    def _calculate_sha256(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def upload_document(
        self,
        file_path: Path,
        document_type: str,
        source_filename: Optional[str] = None,
        linked_entity: Optional[str] = None,
        linked_entity_id: Optional[str] = None,
    ) -> str:
        """
        Upload a document to the DMS with the specified document type.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        document_id = str(uuid.uuid4())
        file_hash = self._calculate_sha256(file_path)

        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = "application/octet-stream"

        if source_filename is None:
            source_filename = file_path.name

        file_extension = file_path.suffix
        blob_name = f"raw/{document_type}/{document_id}{file_extension}"

        logger.info(
            f"Uploading document {document_id} of type '{document_type}' to blob storage"
        )

        with open(file_path, 'rb') as file_data:
            self.storage_client.upload_bytes("documents", blob_name, file_data.read())

        logger.info(f"File uploaded to blob storage: {blob_name}")

        self.metadata_repository.insert_document(
            document_id=document_id,
            dms_path=blob_name,
            document_type=document_type,
            hash_sha256=file_hash,
            source_filename=source_filename,
            linked_entity=linked_entity,
            linked_entity_id=linked_entity_id,
            textextraction_status="not ready",
        )

        logger.info(f"Document record created in database with ID: {document_id}")
        # Determine readiness and optionally create an extraction job
        allowed_mime_types = {"application/pdf", "image/png", "image/jpeg"}
        is_mime_type_allowed = mime_type in allowed_mime_types

        # Verify blob is retrievable (basic integrity check)
        try:
            downloaded_bytes = self.storage_client.download_bytes("documents", blob_name)
            is_blob_retrievable = downloaded_bytes is not None and len(downloaded_bytes) > 0
        except Exception:
            is_blob_retrievable = False

        is_ready = is_mime_type_allowed and is_blob_retrievable

        if is_ready:
            # Update status to ready and create an initial extraction job
            try:
                self.update_textextraction_status(document_id=document_id, status="ready")
            except Exception:
                logger.warning("Failed to update text extraction status to 'ready' for %s", document_id)

            try:
                self.create_extraction_job(document_id=document_id, state="pending extraction")
            except Exception:
                logger.warning("Failed to create initial extraction job for document %s", document_id)
        else:
            logger.info(
                "Document %s not ready: mime_allowed=%s, blob_retrievable=%s",
                document_id,
                is_mime_type_allowed,
                is_blob_retrievable,
            )

        return document_id

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve document metadata by ID."""
        return self.metadata_repository.get_document(document_id)

    def list_documents_by_type(self, document_type: str) -> List[Dict[str, Any]]:
        """List all documents of a specific type."""
        return self.metadata_repository.list_documents_by_type(document_type)

    def download_document(self, document_id: str) -> Optional[bytes]:
        """Download document content from blob storage."""
        document = self.get_document(document_id)
        if not document:
            return None
        return self.storage_client.download_bytes("documents", document["blob_path"]) 

    def update_textextraction_status(self, document_id: str, status: str) -> bool:
        """Update the text extraction status of a document."""
        valid_statuses = [
            "not ready",
            "ready",
            "in progress",
            "completed",
            "failed",
        ]
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")

        return self.metadata_repository.update_document_status(document_id, status)

    def create_extraction_job(self, document_id: str, state: str = "pending") -> str:
        """Create an extraction job for a document."""
        job_id = str(uuid.uuid4())
        self.metadata_repository.insert_extraction_job(job_id=job_id, document_id=document_id, status=state)
        logger.info(
            f"Extraction job created with ID: {job_id} for document: {document_id}"
        )
        return job_id

    def update_extraction_job(self, job_id: str, state: str, worker_log: Optional[str] = None) -> bool:
        """Update an extraction job."""
        return self.metadata_repository.update_extraction_job(job_id=job_id, status=state, error_message=worker_log)

    def get_extraction_jobs(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all extraction jobs for a document."""
        return self.metadata_repository.list_extraction_jobs(document_id)

    # Processing status helpers for pipeline integration
    def mark_ocr_running(self, document_id: str) -> bool:
        """Set processing_status to 'ocr running'."""
        return self.metadata_repository.update_processing_status(document_id, "ocr running")

    def mark_llm_running(self, document_id: str) -> bool:
        """Set processing_status to 'llm running'."""
        return self.metadata_repository.update_processing_status(document_id, "llm running")

    def mark_processing_done(self, document_id: str) -> bool:
        """Set processing_status to 'done'."""
        return self.metadata_repository.update_processing_status(document_id, "done")

    def store_document(self, document_id: str, filename: str, file_data: bytes) -> str:
        """
        Store a document directly from file data (for API uploads).
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            file_data: File content as bytes
            
        Returns:
            Document ID
        """
        # Determine file extension from filename
        file_extension = Path(filename).suffix.lower()
        if not file_extension:
            file_extension = ".pdf"  # Default to PDF
        
        # Create blob path
        blob_name = f"raw/credit_request/{document_id}{file_extension}"
        
        # Upload to blob storage
        self.storage_client.upload_bytes("documents", blob_name, file_data)
        logger.info(f"File uploaded to blob storage: {blob_name}")
        
        # Calculate hash
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # Determine MIME type
        mime_type, _ = mimetypes.guess_type(filename)
        if not mime_type:
            mime_type = "application/pdf"
        
        # Store metadata
        self.metadata_repository.insert_document(
            document_id=document_id,
            dms_path=blob_name,
            document_type="credit_request",
            hash_sha256=file_hash,
            source_filename=filename,
            linked_entity=None,
            linked_entity_id=None,
            textextraction_status="ready",
        )
        
        logger.info(f"Document record created in database with ID: {document_id}")
        return document_id

    def list_documents(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents with pagination.
        
        Args:
            limit: Maximum number of documents to return
            offset: Number of documents to skip
            
        Returns:
            List of document metadata dictionaries
        """
        return self.metadata_repository.list_documents_paginated(limit, offset)


