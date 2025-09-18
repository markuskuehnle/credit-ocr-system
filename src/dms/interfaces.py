"""
Interfaces for DMS components: storage client and metadata repository.
"""

from __future__ import annotations

from typing import Protocol, Optional, List, Dict, Any


class StorageClient(Protocol):
    """Abstraction over blob storage operations used by the DMS service."""

    def upload_bytes(self, container: str, blob_name: str, data: bytes) -> None:
        """Upload a blob to the specified container and blob name."""

    def download_bytes(self, container: str, blob_name: str) -> Optional[bytes]:
        """Download a blob as bytes if it exists, otherwise None."""


class MetadataRepository(Protocol):
    """Abstraction over metadata persistence for documents and extraction jobs."""

    def insert_document(
        self,
        document_id: str,
        dms_path: str,
        document_type: str,
        hash_sha256: str,
        source_filename: str,
        linked_entity: Optional[str],
        linked_entity_id: Optional[str],
        textextraction_status: str,
    ) -> None:
        """Insert a new document record."""

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document record by ID."""

    def list_documents_by_type(self, document_type: str) -> List[Dict[str, Any]]:
        """List documents filtered by type."""

    def update_document_status(self, document_id: str, status: str) -> bool:
        """Update document text extraction status."""

    def update_processing_status(self, document_id: str, status: str) -> bool:
        """Update overall document processing status (ocr running, llm running, done)."""

    def insert_extraction_job(self, job_id: str, document_id: str, status: str) -> None:
        """Insert a new extraction job."""

    def update_extraction_job(self, job_id: str, status: str, error_message: Optional[str]) -> bool:
        """Update an existing extraction job."""

    def list_extraction_jobs(self, document_id: str) -> List[Dict[str, Any]]:
        """List extraction jobs for a document."""

    def list_documents_paginated(self, limit: int, offset: int) -> List[Dict[str, Any]]:
        """List documents with pagination."""


