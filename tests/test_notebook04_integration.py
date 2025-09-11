import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import Dict, Any

# Import the functions from src that notebook 04 uses
from src.integration.orchestration import integrated_pipeline
from src.integration.pipeline import process_document_with_ocr, process_document_with_llm
from src.visualization.ocr_visualization import visualize_ocr_results
from src.config.system import load_system_config
from src.storage.storage import get_storage, Stage


class TestNotebook04Integration:
    """Test the exact logic from notebook 04 using src functions."""
    
    @pytest.fixture
    def sample_pdf_data(self):
        """Sample PDF data for testing."""
        return b"sample pdf data for testing"
    
    @pytest.fixture
    def document_metadata(self):
        """Document metadata as used in notebook 04."""
        return {
            "document_id": "test-document-001",
            "filename": "loan_application.pdf",
            "blob_path": "raw/test-document-001.pdf"
        }
    
    @pytest.mark.asyncio
    async def test_document_upload_to_blob_storage(self, sample_pdf_data, document_metadata):
        """Test document upload to blob storage (Step 1 from notebook 04)."""
        with patch('src.storage.storage.get_storage') as mock_get_storage:
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            
            # Simulate document upload
            mock_storage.upload_blob.return_value = None
            
            # Upload document (as done in notebook 04)
            storage_client = get_storage()
            storage_client.upload_blob(
                uuid=document_metadata["document_id"],
                stage=Stage.RAW,
                ext=".pdf",
                data=sample_pdf_data,
                overwrite=True
            )
            
            # Verify upload was called
            mock_storage.upload_blob.assert_called_once_with(
                uuid=document_metadata["document_id"],
                stage=Stage.RAW,
                ext=".pdf",
                data=sample_pdf_data,
                overwrite=True
            )
    
    @pytest.mark.asyncio
    async def test_ocr_processing_step(self, sample_pdf_data, document_metadata):
        """Test OCR processing step (Step 2 from notebook 04)."""
        with patch('src.integration.pipeline.get_storage') as mock_get_storage, \
             patch('src.integration.pipeline.extract_text_bboxes_with_ocr') as mock_extract, \
             patch('src.integration.pipeline.normalize_ocr_lines') as mock_normalize, \
             patch('src.integration.pipeline.convert_numpy_types') as mock_convert:
            
            # Setup mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            
            mock_extract.return_value = ([{"text": "Company Name: Test Corp", "bbox": {}, "confidence": 0.95, "page_num": 1}], [])
            mock_normalize.return_value = [{"text": "Company Name: Test Corp", "type": "label_value"}]
            mock_convert.return_value = [{"text": "Company Name: Test Corp", "type": "label_value"}]
            
            # Run OCR processing (as done in notebook 04)
            ocr_results = await process_document_with_ocr(document_metadata["document_id"], sample_pdf_data)
            
            # Verify results structure
            assert ocr_results["document_id"] == document_metadata["document_id"]
            assert "normalized_lines" in ocr_results
            assert "original_lines" in ocr_results
            assert "processing_metadata" in ocr_results
            
            # Verify storage was called
            mock_storage.upload_document_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_processing_step(self, document_metadata):
        """Test LLM processing step (Step 3 from notebook 04)."""
        # Mock OCR results
        mock_ocr_results = {
            "document_id": document_metadata["document_id"],
            "normalized_lines": [{"text": "Company Name: Test Corp", "type": "label_value"}],
            "original_lines": [{"text": "Company Name: Test Corp", "bbox": {}, "confidence": 0.95, "page_num": 1}]
        }
        
        with patch('src.integration.pipeline.get_storage') as mock_get_storage, \
             patch('src.integration.pipeline.load_system_config') as mock_sys_config, \
             patch('src.integration.pipeline.load_document_config') as mock_doc_config, \
             patch('src.integration.pipeline.extract_fields_with_llm') as mock_extract:
            
            # Setup mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            
            mock_sys_config.return_value = {
                'llm': {'url': 'http://localhost:11435', 'model_name': 'llama3.1:8b'}
            }
            mock_doc_config.return_value = {"credit_request": Mock()}
            mock_extract.return_value = {
                "extracted_fields": {"company_name": "Test Corp"},
                "missing_fields": [],
                "validation_results": {}
            }
            
            # Run LLM processing (as done in notebook 04)
            llm_results = await process_document_with_llm(document_metadata["document_id"], mock_ocr_results)
            
            # Verify results structure
            assert llm_results["document_id"] == document_metadata["document_id"]
            assert "extraction_results" in llm_results
            assert "processing_metadata" in llm_results
            
            # Verify storage was called
            mock_storage.upload_document_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_visualization_step(self, document_metadata):
        """Test visualization step (Step 4 from notebook 04)."""
        # Mock OCR results
        mock_ocr_results = [
            {"text": "Company Name: Test Corp", "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20}, "confidence": 0.95, "page_num": 1}
        ]
        
        with patch('src.visualization.ocr_visualization.get_storage') as mock_get_storage, \
             patch('src.visualization.ocr_visualization.convert_from_bytes') as mock_convert, \
             patch('src.visualization.ocr_visualization.plt') as mock_plt:
            
            # Setup mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            mock_storage.download_blob.return_value = b"mock pdf data"
            
            mock_image = Mock()
            mock_image.width = 800
            mock_image.height = 600
            mock_convert.return_value = [mock_image]
            
            # Mock plt.subplots to return fig and ax
            mock_fig = Mock()
            mock_ax = Mock()
            mock_plt.subplots.return_value = (mock_fig, mock_ax)
            
            # Run visualization (as done in notebook 04)
            visualize_ocr_results(document_metadata["document_id"], mock_ocr_results)
            
            # Verify storage was called for visualization upload
            mock_storage.upload_blob.assert_called()
    
    @pytest.mark.asyncio
    async def test_complete_integrated_pipeline(self, sample_pdf_data, document_metadata):
        """Test the complete integrated pipeline (as executed in notebook 04)."""
        with patch('src.integration.orchestration.get_storage') as mock_get_storage, \
             patch('src.integration.orchestration.process_document_with_ocr') as mock_ocr, \
             patch('src.integration.orchestration.process_document_with_llm') as mock_llm, \
             patch('src.integration.orchestration.visualize_ocr_results') as mock_viz:
            
            # Setup mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            mock_storage.download_blob.return_value = sample_pdf_data
            
            # Mock OCR results
            mock_ocr_results = {
                "document_id": document_metadata["document_id"],
                "normalized_lines": [{"text": "Company Name: Test Corp", "type": "label_value"}],
                "original_lines": [{"text": "Company Name: Test Corp", "bbox": {}, "confidence": 0.95, "page_num": 1}]
            }
            mock_ocr.return_value = mock_ocr_results
            
            # Mock LLM results
            mock_llm_results = {
                "document_id": document_metadata["document_id"],
                "extraction_results": {
                    "extracted_fields": {"company_name": "Test Corp"},
                    "missing_fields": [],
                    "validation_results": {}
                }
            }
            mock_llm.return_value = mock_llm_results
            
            # Run the complete pipeline (as done in notebook 04)
            results = await integrated_pipeline(
                document_metadata["document_id"],
                document_metadata["filename"],
                document_metadata["blob_path"]
            )
            
            # Verify complete results structure
            assert results["document_id"] == document_metadata["document_id"]
            assert results["filename"] == document_metadata["filename"]
            assert results["blob_path"] == document_metadata["blob_path"]
            assert "ocr_results" in results
            assert "llm_results" in results
            assert "processing_summary" in results
            
            # Verify processing summary (as shown in notebook 04)
            summary = results["processing_summary"]
            assert "total_ocr_elements" in summary
            assert "normalized_elements" in summary
            assert "extracted_fields" in summary
            assert "validation_errors" in summary
            
            # Verify all processing steps were called
            mock_ocr.assert_called_once_with(document_metadata["document_id"], sample_pdf_data)
            mock_llm.assert_called_once_with(document_metadata["document_id"], mock_ocr_results)
            mock_viz.assert_called_once_with(document_metadata["document_id"], mock_ocr_results["original_lines"])
    
    def test_system_config_loading(self):
        """Test system configuration loading (as used in notebook 04)."""
        config_content = '''
generative_llm {
    url = "http://localhost:11435"
    model_name = "llama3.1:8b"
}
'''
        with patch('builtins.open', mock_open(read_data=config_content)):
            config = load_system_config()
            
            assert 'llm' in config
            assert config['llm']['url'] == 'http://localhost:11435'
            assert config['llm']['model_name'] == 'llama3.1:8b'


class TestNotebook04Workflow:
    """Test the exact workflow sequence from notebook 04."""
    
    @pytest.mark.asyncio
    async def test_notebook04_exact_workflow(self):
        """Test the exact workflow as executed in notebook 04."""
        # This mirrors the exact sequence from notebook 04
        
        # Step 1: Document setup (as in notebook 04)
        document_id = "test-document-001"
        filename = "loan_application.pdf"
        blob_path = f"raw/{document_id}.pdf"
        
        # Step 2: Upload document to blob storage (as in notebook 04)
        with patch('src.storage.storage.get_storage') as mock_get_storage:
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            
            # Upload document
            storage_client = get_storage()
            storage_client.upload_blob(
                uuid=document_id,
                stage=Stage.RAW,
                ext=".pdf",
                data=b"mock pdf data",
                overwrite=True
            )
            
            # Verify upload
            mock_storage.upload_blob.assert_called_once()
        
        # Step 3: Run integrated pipeline (as in notebook 04)
        with patch('src.integration.orchestration.get_storage') as mock_get_storage, \
             patch('src.integration.orchestration.process_document_with_ocr') as mock_ocr, \
             patch('src.integration.orchestration.process_document_with_llm') as mock_llm, \
             patch('src.integration.orchestration.visualize_ocr_results') as mock_viz:
            
            # Setup mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            mock_storage.download_blob.return_value = b"mock pdf data"
            
            mock_ocr.return_value = {"document_id": document_id, "normalized_lines": [], "original_lines": []}
            mock_llm.return_value = {"document_id": document_id, "extraction_results": {"extracted_fields": {}, "missing_fields": [], "validation_results": {}}}
            mock_viz.return_value = None
            
            # Execute pipeline (as in notebook 04)
            results = await integrated_pipeline(document_id, filename, blob_path)
            
            # Verify results (as expected in notebook 04)
            assert results["document_id"] == document_id
            assert results["filename"] == filename
            assert results["blob_path"] == blob_path
            
            # Verify all steps were executed
            mock_ocr.assert_called_once()
            mock_llm.assert_called_once()
            mock_viz.assert_called_once()


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
