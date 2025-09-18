import pytest
import uuid
from io import BytesIO
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.models import ProcessingStatus


@pytest.fixture
def client(setup_test_database, setup_test_storage):
    """Create a test client for the FastAPI app with real services."""
    return TestClient(app)


@pytest.fixture
def mock_pdf_content():
    """Mock PDF file content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def mock_document_id():
    """Fixed document ID for testing."""
    return "test-document-12345"


class TestAPIHealth:
    """Test health check endpoint."""
    
    def test_health_check_success(self, client):
        """Test successful health check."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms, \
             patch('src.api.routes.get_storage') as mock_get_storage:
            
            # Mock successful DMS service
            mock_dms = Mock()
            mock_dms.list_documents.return_value = []
            mock_get_dms.return_value = mock_dms
            
            # Mock successful storage
            mock_storage = Mock()
            mock_storage.ensure_all_containers_ready.return_value = None
            mock_get_storage.return_value = mock_storage
            
            response = client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "services" in data
            assert data["services"]["database"] == "healthy"
            assert data["services"]["blob_storage"] == "healthy"


class TestDocumentUpload:
    """Test document upload functionality."""
    
    def test_upload_pdf_success(self, client, mock_pdf_content, mock_document_id):
        """Test successful PDF upload."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms, \
             patch('src.api.routes.get_storage') as mock_get_storage, \
             patch('uuid.uuid4') as mock_uuid:
            
            # Mock UUID generation
            mock_uuid.return_value = Mock()
            mock_uuid.return_value.__str__ = Mock(return_value=mock_document_id)
            
            # Mock DMS service
            mock_dms = Mock()
            mock_dms.store_document.return_value = mock_document_id
            mock_get_dms.return_value = mock_dms
            
            # Mock storage
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            
            # Create test file
            files = {"file": ("test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
            
            response = client.post("/api/v1/upload", files=files)
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == mock_document_id
            assert data["filename"] == "test.pdf"
            assert data["status"] == ProcessingStatus.PENDING
            assert "processing started" in data["message"].lower()
            
            # Verify DMS service was called
            mock_dms.store_document.assert_called_once()
    
    def test_upload_non_pdf_file(self, client):
        """Test upload of non-PDF file fails."""
        files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
        
        response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_upload_empty_file(self, client):
        """Test upload of empty file fails."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            files = {"file": ("test.pdf", BytesIO(b""), "application/pdf")}
            
            response = client.post("/api/v1/upload", files=files)
            
            assert response.status_code == 400
            assert "Empty file uploaded" in response.json()["detail"]


class TestDocumentStatus:
    """Test document status retrieval."""
    
    def test_get_status_success(self, client, mock_document_id):
        """Test successful status retrieval."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service with document data
            mock_dms = Mock()
            mock_document = {
                'document_id': mock_document_id,
                'filename': 'test.pdf',
                'textextraction_status': 'ready',
                'processing_status': 'done',
                'upload_timestamp': '2024-01-01T12:00:00Z'
            }
            mock_dms.get_document.return_value = mock_document
            mock_get_dms.return_value = mock_dms
            
            response = client.get(f"/api/v1/status/{mock_document_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == mock_document_id
            assert data["status"] == ProcessingStatus.COMPLETED
            assert data["filename"] == "test.pdf"
    
    def test_get_status_not_found(self, client, mock_document_id):
        """Test status retrieval for non-existent document."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service returning None
            mock_dms = Mock()
            mock_dms.get_document.return_value = None
            mock_get_dms.return_value = mock_dms
            
            response = client.get(f"/api/v1/status/{mock_document_id}")
            
            assert response.status_code == 404
            assert "Document not found" in response.json()["detail"]


class TestDocumentResults:
    """Test document results retrieval."""
    
    def test_get_results_success(self, client, mock_document_id):
        """Test successful results retrieval."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms, \
             patch('src.api.routes.get_storage') as mock_get_storage:
            
            # Mock DMS service with completed document
            mock_dms = Mock()
            mock_document = {
                'document_id': mock_document_id,
                'filename': 'test.pdf',
                'processing_status': 'done',
                'textextraction_status': 'done'
            }
            mock_dms.get_document.return_value = mock_document
            mock_get_dms.return_value = mock_dms
            
            # Mock storage with OCR and LLM results
            mock_storage = Mock()
            mock_ocr_data = {
                'original_lines': [
                    {
                        'text': 'Test Text',
                        'confidence': 0.95,
                        'bbox': {'x1': 100, 'y1': 200, 'width': 50, 'height': 20},
                        'page_num': 1
                    }
                ],
                'normalized_lines': []
            }
            mock_llm_data = {
                'extraction_results': {
                    'extracted_fields': {
                        'applicant_name': {
                            'extracted_value': 'John Doe',
                            'confidence_score': 0.9,
                            'source_ocr_elements': ['elem_1']
                        }
                    },
                    'validation_results': []
                }
            }
            
            # Mock storage downloads
            mock_storage.download_blob.side_effect = [mock_ocr_data, mock_llm_data]
            mock_storage.blob_exists.return_value = True
            mock_get_storage.return_value = mock_storage
            
            response = client.get(f"/api/v1/results/{mock_document_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["document_id"] == mock_document_id
            assert data["status"] == ProcessingStatus.COMPLETED
            assert len(data["extracted_fields"]) == 1
            assert data["extracted_fields"][0]["field_name"] == "applicant_name"
            assert data["extracted_fields"][0]["extracted_value"] == "John Doe"
            assert len(data["ocr_elements"]) == 1
            assert data["has_visualization"] is True
    
    def test_get_results_processing_incomplete(self, client, mock_document_id):
        """Test results retrieval for incomplete processing."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service with processing document
            mock_dms = Mock()
            mock_document = {
                'document_id': mock_document_id,
                'filename': 'test.pdf',
                'processing_status': 'ocr_running',
                'textextraction_status': 'in progress'
            }
            mock_dms.get_document.return_value = mock_document
            mock_get_dms.return_value = mock_dms
            
            response = client.get(f"/api/v1/results/{mock_document_id}")
            
            assert response.status_code == 202
            assert "not yet complete" in response.json()["detail"]


class TestDocumentVisualization:
    """Test document visualization endpoint."""
    
    def test_get_visualization_success(self, client, mock_document_id):
        """Test successful visualization retrieval."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms, \
             patch('src.api.routes.get_storage') as mock_get_storage:
            
            # Mock DMS service
            mock_dms = Mock()
            mock_document = {'document_id': mock_document_id}
            mock_dms.get_document.return_value = mock_document
            mock_get_dms.return_value = mock_dms
            
            # Mock storage with visualization data
            mock_storage = Mock()
            mock_image_data = b"fake_png_data"
            mock_storage.download_blob.return_value = mock_image_data
            mock_get_storage.return_value = mock_storage
            
            response = client.get(f"/api/v1/visualization/{mock_document_id}?page=1")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "image/png"
            assert response.content == mock_image_data
    
    def test_get_visualization_not_found(self, client, mock_document_id):
        """Test visualization retrieval when not available."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms, \
             patch('src.api.routes.get_storage') as mock_get_storage:
            
            # Mock DMS service
            mock_dms = Mock()
            mock_document = {'document_id': mock_document_id}
            mock_dms.get_document.return_value = mock_document
            mock_get_dms.return_value = mock_dms
            
            # Mock storage returning None
            mock_storage = Mock()
            mock_storage.download_blob.return_value = None
            mock_get_storage.return_value = mock_storage
            
            response = client.get(f"/api/v1/visualization/{mock_document_id}?page=1")
            
            assert response.status_code == 404
            assert "Visualization not found" in response.json()["detail"]


class TestDocumentListing:
    """Test document listing functionality."""
    
    def test_list_documents_success(self, client):
        """Test successful document listing."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service with document list
            mock_dms = Mock()
            mock_documents = [
                {
                    'document_id': 'doc-1',
                    'filename': 'test1.pdf',
                    'textextraction_status': 'done',
                    'processing_status': 'done',
                    'upload_timestamp': '2024-01-01T12:00:00Z'
                },
                {
                    'document_id': 'doc-2',
                    'filename': 'test2.pdf',
                    'textextraction_status': 'ready',
                    'processing_status': None,
                    'upload_timestamp': '2024-01-01T13:00:00Z'
                }
            ]
            mock_dms.list_documents.return_value = mock_documents
            mock_get_dms.return_value = mock_dms
            
            response = client.get("/api/v1/documents")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["document_id"] == "doc-1"
            assert data[0]["status"] == ProcessingStatus.COMPLETED
            assert data[1]["document_id"] == "doc-2"
            assert data[1]["status"] == ProcessingStatus.PENDING
    
    def test_list_documents_with_pagination(self, client):
        """Test document listing with pagination parameters."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service
            mock_dms = Mock()
            mock_dms.list_documents.return_value = []
            mock_get_dms.return_value = mock_dms
            
            response = client.get("/api/v1/documents?limit=10&offset=5")
            
            assert response.status_code == 200
            # Verify pagination parameters were passed
            mock_dms.list_documents.assert_called_once_with(limit=10, offset=5)


class TestWebInterface:
    """Test web interface endpoints."""
    
    def test_web_interface_loads(self, client):
        """Test that the web interface loads successfully."""
        # Test that the endpoint exists and returns an HTML response
        response = client.get("/")
        
        # Should return 200 for existing template
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")


class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_upload_with_dms_service_error(self, client, mock_pdf_content):
        """Test upload when DMS service fails."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service raising an exception
            mock_dms = Mock()
            mock_dms.store_document.side_effect = Exception("DMS Error")
            mock_get_dms.return_value = mock_dms
            
            files = {"file": ("test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
            
            response = client.post("/api/v1/upload", files=files)
            
            assert response.status_code == 500
            assert "Failed to upload document" in response.json()["detail"]
    
    def test_status_with_service_error(self, client, mock_document_id):
        """Test status endpoint when service fails."""
        with patch('src.api.routes.get_dms_service') as mock_get_dms:
            # Mock DMS service raising an exception
            mock_dms = Mock()
            mock_dms.get_document.side_effect = Exception("Database Error")
            mock_get_dms.return_value = mock_dms
            
            response = client.get(f"/api/v1/status/{mock_document_id}")
            
            assert response.status_code == 500
            assert "Failed to get document status" in response.json()["detail"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
