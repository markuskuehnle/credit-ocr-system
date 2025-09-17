"""
Concrete adapters implementing DMS interfaces: Azure Blob storage and Postgres metadata.
"""

from __future__ import annotations

from typing import Optional, List, Dict, Any

from azure.storage.blob import BlobServiceClient

from .interfaces import StorageClient, MetadataRepository


class AzureBlobStorageClient(StorageClient):
    """Azure Blob implementation of StorageClient."""

    def __init__(self, blob_service_client: BlobServiceClient) -> None:
        self._client = blob_service_client

    def upload_bytes(self, container: str, blob_name: str, data: bytes) -> None:
        container_client = self._client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def download_bytes(self, container: str, blob_name: str) -> Optional[bytes]:
        container_client = self._client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        try:
            stream = blob_client.download_blob()
            return stream.readall()
        except Exception:
            return None


class PostgresMetadataRepository(MetadataRepository):
    """PostgreSQL implementation of MetadataRepository."""

    def __init__(self, connection) -> None:
        self._conn = connection
        try:
            # Enable autocommit to avoid lingering aborted transactions during notebooks/tests
            self._conn.autocommit = True
        except Exception:
            pass

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
        # Current schema has table 'documents' with columns: id, filename, file_path, file_size, mime_type
        # Map our fields accordingly; store blob path and filename, derive size and mime_type is not known here
        file_size: Optional[int] = None
        mime_type: Optional[str] = None
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO documents (id, filename, file_path, file_size, mime_type)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    document_id,
                    source_filename,
                    dms_path,
                    file_size,
                    mime_type,
                ),
            )
            self._conn.commit()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, file_path, filename, created_at, mime_type, file_size, 
                       text_extraction_status, processing_status
                FROM documents WHERE id = %s
                """,
                (document_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id": row[0],
                "blob_path": row[1],
                "document_type": None,
                "uploaded_at": row[3],
                "hash_sha256": None,
                "source_filename": row[2],
                "linked_entity": None,
                "linked_entity_id": None,
                "textextraction_status": row[6],
                "processing_status": row[7],
                "mime_type": row[4],
                "file_size": row[5],
            }

    def list_documents_by_type(self, document_type: str) -> List[Dict[str, Any]]:
        # Not supported by current schema; return latest documents instead
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, file_path, filename, created_at, mime_type, file_size,
                       text_extraction_status, processing_status
                FROM documents ORDER BY created_at DESC
                """
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "blob_path": row[1],
                    "document_type": None,
                    "uploaded_at": row[3],
                    "hash_sha256": None,
                    "source_filename": row[2],
                    "linked_entity": None,
                    "linked_entity_id": None,
                    "textextraction_status": row[6],
                    "processing_status": row[7],
                    "mime_type": row[4],
                    "file_size": row[5],
                }
                for row in rows
            ]

    def update_document_status(self, document_id: str, status: str) -> bool:
        # Update status if column exists (schema adds it)
        with self._conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    UPDATE documents
                    SET text_extraction_status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, document_id),
                )
                updated = cursor.rowcount > 0
                self._conn.commit()
                return updated
            except Exception:
                self._conn.rollback()
                return False

    def update_processing_status(self, document_id: str, status: str) -> bool:
        with self._conn.cursor() as cursor:
            try:
                cursor.execute(
                    """
                    UPDATE documents
                    SET processing_status = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (status, document_id),
                )
                updated = cursor.rowcount > 0
                self._conn.commit()
                return updated
            except Exception:
                self._conn.rollback()
                return False

    def insert_extraction_job(self, job_id: str, document_id: str, status: str) -> None:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO extraction_jobs (id, document_id, status)
                VALUES (%s, %s, %s)
                """,
                (job_id, document_id, status),
            )
            self._conn.commit()

    def update_extraction_job(self, job_id: str, status: str, error_message: Optional[str]) -> bool:
        with self._conn.cursor() as cursor:
            if error_message is not None:
                cursor.execute(
                    """
                    UPDATE extraction_jobs
                    SET status = %s,
                        error_message = %s,
                        completed_at = CASE WHEN %s IN ('done', 'failed', 'finished') THEN NOW() ELSE completed_at END
                    WHERE id = %s
                    """,
                    (status, error_message, status, job_id),
                )
            else:
                cursor.execute(
                    """
                    UPDATE extraction_jobs
                    SET status = %s,
                        completed_at = CASE WHEN %s IN ('done', 'failed', 'finished') THEN NOW() ELSE completed_at END
                    WHERE id = %s
                    """,
                    (status, status, job_id),
                )
            updated = cursor.rowcount > 0
            self._conn.commit()
            return updated

    def list_extraction_jobs(self, document_id: str) -> List[Dict[str, Any]]:
        with self._conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, document_id, created_at, completed_at, status, error_message
                FROM extraction_jobs
                WHERE document_id = %s
                ORDER BY created_at DESC
                """,
                (document_id,),
            )
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "document_id": row[1],
                    "created_at": row[2],
                    "completed_at": row[3],
                    "status": row[4],
                    "error_message": row[5],
                }
                for row in rows
            ]


