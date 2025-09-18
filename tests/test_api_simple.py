import pytest
import uuid
from io import BytesIO
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client(setup_test_database, setup_test_storage):
    """Create a test client for the FastAPI app with real services."""
    return TestClient(app)


@pytest.fixture
def mock_pdf_content():
    """Mock PDF file content for testing."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n%%EOF"


@pytest.fixture
def unique_document_id():
    """Generate a unique document ID for each test."""
    return str(uuid.uuid4())


class TestAPIBasicFunctionality:
    """Test basic API functionality with real infrastructure."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        
        # Check that we can connect to real services
        assert "database" in data["services"]
        assert "blob_storage" in data["services"]
    
    def test_upload_pdf_file(self, client, mock_pdf_content):
        """Test uploading a PDF file."""
        files = {"file": ("test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
        
        response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.pdf"
        assert data["status"] == "pending"
        assert "processing started" in data["message"].lower()
        
        # Document uploaded successfully
        assert len(data["document_id"]) > 0
    
    def test_upload_invalid_file_type(self, client):
        """Test uploading a non-PDF file fails."""
        files = {"file": ("test.txt", BytesIO(b"test content"), "text/plain")}
        
        response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        assert "Only PDF files are allowed" in response.json()["detail"]
    
    def test_upload_empty_file(self, client):
        """Test uploading an empty file fails."""
        files = {"file": ("test.pdf", BytesIO(b""), "application/pdf")}
        
        response = client.post("/api/v1/upload", files=files)
        
        assert response.status_code == 400
        assert "Empty file uploaded" in response.json()["detail"]
    
    def test_get_status_after_upload(self, client, mock_pdf_content):
        """Test getting status for a newly uploaded document."""
        # First upload a document
        files = {"file": ("test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
        upload_response = client.post("/api/v1/upload", files=files)
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # Then check its status
        status_response = client.get(f"/api/v1/status/{document_id}")
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["document_id"] == document_id
        assert data["filename"] == "test.pdf"
        assert data["status"] in ["pending", "processing", "ocr_running", "llm_running"]
    
    def test_get_status_nonexistent_document(self, client):
        """Test getting status for a non-existent document."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/status/{fake_id}")
        
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]
    
    def test_list_documents_empty(self, client):
        """Test listing documents when none exist."""
        response = client.get("/api/v1/documents")
        
        assert response.status_code == 200
        documents = response.json()
        assert isinstance(documents, list)
        # Should be empty or only contain documents from other tests
    
    def test_list_documents_after_upload(self, client, mock_pdf_content):
        """Test listing documents after uploading one."""
        # Upload a document
        files = {"file": ("test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
        upload_response = client.post("/api/v1/upload", files=files)
        assert upload_response.status_code == 200
        document_id = upload_response.json()["document_id"]
        
        # List documents
        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        
        documents = list_response.json()
        assert isinstance(documents, list)
        assert len(documents) >= 1
        
        # Find our uploaded document
        uploaded_doc = next((doc for doc in documents if doc["document_id"] == document_id), None)
        assert uploaded_doc is not None
        assert uploaded_doc["filename"] == "test.pdf"
    
    def test_web_interface_accessible(self, client):
        """Test that the web interface is accessible."""
        response = client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
    
    def test_api_documentation_accessible(self, client):
        """Test that API documentation is accessible."""
        docs_response = client.get("/docs")
        assert docs_response.status_code == 200
        
        redoc_response = client.get("/redoc")
        assert redoc_response.status_code == 200


class TestAPIErrorHandling:
    """Test API error handling scenarios."""
    
    def test_invalid_endpoint(self, client):
        """Test accessing a non-existent endpoint."""
        response = client.get("/api/v1/nonexistent")
        
        assert response.status_code == 404
    
    def test_invalid_document_id_format(self, client):
        """Test using an invalid document ID format."""
        response = client.get("/api/v1/status/invalid-id-format")
        
        # Should still return 404 since document doesn't exist
        assert response.status_code == 404


class TestIntegrationWorkflow:
    """Test complete workflow from upload to status tracking."""
    
    def test_complete_upload_and_tracking_workflow(self, client, mock_pdf_content):
        """Test the complete workflow of uploading and tracking a document."""
        # Step 1: Upload document
        files = {"file": ("integration_test.pdf", BytesIO(mock_pdf_content), "application/pdf")}
        upload_response = client.post("/api/v1/upload", files=files)
        
        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        document_id = upload_data["document_id"]
        
        # Step 2: Verify document appears in listing
        list_response = client.get("/api/v1/documents")
        assert list_response.status_code == 200
        documents = list_response.json()
        uploaded_doc = next((doc for doc in documents if doc["document_id"] == document_id), None)
        assert uploaded_doc is not None
        
        # Step 3: Check status
        status_response = client.get(f"/api/v1/status/{document_id}")
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert status_data["document_id"] == document_id
        assert status_data["filename"] == "integration_test.pdf"
        
        # Step 4: Try to get results (should return 202 since processing isn't complete)
        results_response = client.get(f"/api/v1/results/{document_id}")
        # For a real integration test, we'd wait for processing to complete
        # For now, we expect either 202 (not ready) or 200 (ready)
        assert results_response.status_code in [200, 202]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
