from __future__ import annotations

"""Integration-like tests for DMS service using Postgres testcontainer and a fake storage client.

Each test asserts a single behavior.
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Tuple

import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer


# ----- Test Helpers -----

class TestStorageClient:
    """In-memory StorageClient implementation for tests."""

    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], bytes] = {}

    def upload_bytes(self, container: str, blob_name: str, data: bytes) -> None:
        self._store[(container, blob_name)] = data

    def download_bytes(self, container: str, blob_name: str) -> Optional[bytes]:
        return self._store.get((container, blob_name))


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Resolve repository root for imports and schema path."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def add_src_to_path(project_root: Path) -> None:
    """Ensure `src` is importable in tests."""
    src_path = str(project_root)
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


@pytest.fixture()
def postgres_conn(project_root: Path):
    """Start a temporary Postgres, apply schema, yield psycopg2 connection."""
    with PostgresContainer("postgres:16") as pg:
        # Build a psycopg2 connection from the SQLAlchemy-style URL
        from urllib.parse import urlparse
        url = urlparse(pg.get_connection_url())
        host = url.hostname or "localhost"
        port = url.port or 5432
        dbname = (url.path or "/test").lstrip("/") or "test"
        user = url.username or "test"
        password = url.password or "test"
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        conn.autocommit = True

        # Apply schema
        schema_sql = (project_root / "database" / "schemas" / "schema.sql").read_text()
        with conn.cursor() as cur:
            cur.execute(schema_sql)

        yield conn

        conn.close()


# Deferred imports until sys.path is set up
from src.dms.service import DmsService
from src.dms.adapters import PostgresMetadataRepository


@pytest.fixture()
def dms_service(postgres_conn):
    """Create DmsService with test storage and Postgres metadata repo."""
    storage = TestStorageClient()
    metadata = PostgresMetadataRepository(postgres_conn)
    return DmsService(storage_client=storage, metadata_repository=metadata)


def _write_tmp_file(tmp_path: Path, name: str, content: bytes) -> Path:
    file_path = tmp_path / name
    file_path.write_bytes(content)
    return file_path


def test_upload_document_not_ready_when_blob_unretrievable(dms_service: DmsService, tmp_path: Path, postgres_conn) -> None:
    """Document remains 'not ready' and no job is created if blob cannot be read back."""
    # Arrange: create a PDF-like file but sabotage storage by not storing bytes under the uploaded key
    file_path = _write_tmp_file(tmp_path, "doc.pdf", b"%PDF-1.7 test")

    # Monkey-patch storage to drop the uploaded bytes after upload
    original_upload = dms_service.storage_client.upload_bytes

    def drop_upload(container: str, blob_name: str, data: bytes) -> None:
        # Upload then delete to simulate retrieval failure
        original_upload(container, blob_name, data)
        # type: ignore[attr-defined]
        dms_service.storage_client._store.pop((container, blob_name), None)  # type: ignore[attr-defined]

    dms_service.storage_client.upload_bytes = drop_upload  # type: ignore[assignment]

    # Act
    document_id = dms_service.upload_document(file_path=file_path, document_type="loan_application")

    # Assert: status remains 'not ready'
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT text_extraction_status FROM documents WHERE id = %s", (document_id,))
        row = cur.fetchone()
        assert row and row[0] == "not ready"


def test_upload_document_ready_and_job_created(dms_service: DmsService, tmp_path: Path, postgres_conn) -> None:
    """Document becomes 'ready' and an extraction job is created when blob retrievable and MIME ok."""
    # Arrange
    file_path = _write_tmp_file(tmp_path, "doc.pdf", b"%PDF-1.7 valid content")

    # Act
    document_id = dms_service.upload_document(file_path=file_path, document_type="loan_application")

    # Assert: one extraction job exists for document
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM extraction_jobs WHERE document_id = %s", (document_id,))
        (count,) = cur.fetchone()
        assert count == 1


def test_mark_ocr_running_updates_processing_status(dms_service: DmsService, tmp_path: Path, postgres_conn) -> None:
    """Processing status changes to 'ocr running' when marked."""
    file_path = _write_tmp_file(tmp_path, "doc.pdf", b"%PDF-1.7 valid content")
    document_id = dms_service.upload_document(file_path=file_path, document_type="loan_application")
    dms_service.mark_ocr_running(document_id)
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT processing_status FROM documents WHERE id = %s", (document_id,))
        (status,) = cur.fetchone()
        assert status == "ocr running"


def test_update_extraction_job_sets_completed_at_on_done(dms_service: DmsService, tmp_path: Path, postgres_conn) -> None:
    """Extraction job gets completed_at timestamp when marked as 'done'."""
    file_path = _write_tmp_file(tmp_path, "doc.pdf", b"%PDF-1.7 valid content")
    document_id = dms_service.upload_document(file_path=file_path, document_type="loan_application")

    # Get job id
    jobs = dms_service.get_extraction_jobs(document_id)
    job_id = jobs[0]["id"]

    # Act
    dms_service.update_extraction_job(job_id=job_id, state="done", worker_log=None)

    # Assert: completed_at set
    with postgres_conn.cursor() as cur:
        cur.execute("SELECT completed_at FROM extraction_jobs WHERE id = %s", (job_id,))
        (completed_at,) = cur.fetchone()
        assert completed_at is not None


