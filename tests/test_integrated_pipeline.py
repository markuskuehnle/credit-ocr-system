import pytest
import asyncio
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import Dict, Any

# Import the functions we want to test
from src.integration.orchestration import integrated_pipeline
from src.integration.pipeline import process_document_with_ocr, process_document_with_llm
from src.visualization.ocr_visualization import visualize_ocr_results
from src.config.system import load_system_config
from src.storage.storage import get_storage, Stage


class TestIntegratedPipeline:
    """Test the complete integrated pipeline functionality."""
    
    @pytest.fixture
    def mock_pdf_data(self):
        """Mock PDF data for testing."""
        return b"mock pdf data for testing"
    
    @pytest.fixture
    def mock_ocr_results(self):
        """Mock OCR results for testing."""
        return {
            "document_id": "test-doc-001",
            "processing_timestamp": "2024-01-01T00:00:00Z",
            "processing_metadata": {
                "total_elements": 10,
                "normalized_elements": 8,
                "processing_method": "easyocr"
            },
            "normalized_lines": [
                {
                    "text": "Company Name: DemoTech Solutions GmbH",
                    "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20},
                    "confidence": 0.95,
                    "page_num": 1,
                    "type": "label_value"
                }
            ],
            "original_lines": [
                {
                    "text": "Company Name: DemoTech Solutions GmbH",
                    "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20},
                    "confidence": 0.95,
                    "page_num": 1
                }
            ]
        }
    
    @pytest.fixture
    def mock_llm_results(self):
        """Mock LLM results for testing."""
        return {
            "document_id": "test-doc-001",
            "processing_timestamp": "2024-01-01T00:00:00Z",
            "processing_metadata": {
                "model_name": "llama3.1:8b",
                "model_url": "http://localhost:11435",
                "processing_method": "llama3.1:8b"
            },
            "extraction_results": {
                "extracted_fields": {
                    "company_name": {
                        "value": "DemoTech Solutions GmbH",
                        "confidence": 0.95,
                        "source_text": "Company Name: DemoTech Solutions GmbH"
                    }
                },
                "missing_fields": [],
                "validation_results": {}
            }
        }
    
    @pytest.fixture
    def mock_storage_client(self):
        """Mock storage client for testing."""
        mock_client = Mock()
        mock_client.download_blob.return_value = b"mock pdf data"
        mock_client.upload_document_data.return_value = None
        mock_client.upload_blob.return_value = None
        mock_client.blob_path.return_value = "test/path"
        return mock_client
    
    @pytest.mark.asyncio
    async def test_process_document_with_ocr(self, mock_pdf_data, mock_ocr_results, mock_storage_client):
        """Test OCR processing function."""
        with patch('src.integration.pipeline.get_storage', return_value=mock_storage_client), \
             patch('src.integration.pipeline.extract_text_bboxes_with_ocr') as mock_extract, \
             patch('src.integration.pipeline.normalize_ocr_lines') as mock_normalize, \
             patch('src.integration.pipeline.convert_numpy_types') as mock_convert:
            
            # Setup mocks
            mock_extract.return_value = ([{"text": "test", "bbox": {}, "confidence": 0.9, "page_num": 1}], [])
            mock_normalize.return_value = [{"text": "test", "type": "label_value"}]
            mock_convert.return_value = [{"text": "test", "type": "label_value"}]
            
            # Test the function
            result = await process_document_with_ocr("test-doc-001", mock_pdf_data)
            
            # Assertions
            assert result["document_id"] == "test-doc-001"
            assert "normalized_lines" in result
            assert "original_lines" in result
            assert "processing_metadata" in result
            
            # Verify storage was called
            mock_storage_client.upload_document_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_document_with_llm(self, mock_ocr_results, mock_llm_results, mock_storage_client):
        """Test LLM processing function."""
        with patch('src.integration.pipeline.get_storage', return_value=mock_storage_client), \
             patch('src.integration.pipeline.load_system_config') as mock_sys_config, \
             patch('src.integration.pipeline.load_document_config') as mock_doc_config, \
             patch('src.integration.pipeline.OllamaClient') as mock_llm_client, \
             patch('src.integration.pipeline.extract_fields_with_llm') as mock_extract:
            
            # Setup mocks
            mock_sys_config.return_value = {
                'llm': {'url': 'http://localhost:11435', 'model_name': 'llama3.1:8b'}
            }
            mock_doc_config.return_value = {"credit_request": Mock()}
            mock_extract.return_value = mock_llm_results["extraction_results"]
            
            # Test the function
            result = await process_document_with_llm("test-doc-001", mock_ocr_results)
            
            # Assertions
            assert result["document_id"] == "test-doc-001"
            assert "extraction_results" in result
            assert "processing_metadata" in result
            
            # Verify storage was called
            mock_storage_client.upload_document_data.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_visualize_ocr_results(self, mock_ocr_results, mock_storage_client):
        """Test OCR visualization function."""
        with patch('src.visualization.ocr_visualization.get_storage', return_value=mock_storage_client), \
             patch('src.visualization.ocr_visualization.convert_from_bytes') as mock_convert, \
             patch('src.visualization.ocr_visualization.plt') as mock_plt:
            
            # Setup mocks
            mock_image = Mock()
            mock_image.width = 800
            mock_image.height = 600
            mock_convert.return_value = [mock_image]
            
            # Mock plt.subplots to return fig and ax
            mock_fig = Mock()
            mock_ax = Mock()
            mock_plt.subplots.return_value = (mock_fig, mock_ax)
            
            # Test the function
            visualize_ocr_results("test-doc-001", mock_ocr_results["original_lines"])
            
            # Verify storage was called for visualization upload
            mock_storage_client.upload_blob.assert_called()
    
    @pytest.mark.asyncio
    async def test_integrated_pipeline_success(self, mock_pdf_data, mock_ocr_results, mock_llm_results, mock_storage_client):
        """Test complete integrated pipeline."""
        with patch('src.integration.orchestration.get_storage', return_value=mock_storage_client), \
             patch('src.integration.orchestration.process_document_with_ocr') as mock_ocr, \
             patch('src.integration.orchestration.process_document_with_llm') as mock_llm, \
             patch('src.integration.orchestration.visualize_ocr_results') as mock_viz:
            
            # Setup mocks
            mock_ocr.return_value = mock_ocr_results
            mock_llm.return_value = mock_llm_results
            mock_viz.return_value = None
            
            # Test the function
            result = await integrated_pipeline("test-doc-001", "test.pdf", "raw/test-doc-001.pdf")
            
            # Assertions
            assert result["document_id"] == "test-doc-001"
            assert result["filename"] == "test.pdf"
            assert result["blob_path"] == "raw/test-doc-001.pdf"
            assert "ocr_results" in result
            assert "llm_results" in result
            assert "processing_summary" in result
            
            # Verify all processing steps were called
            mock_ocr.assert_called_once_with("test-doc-001", mock_pdf_data)
            mock_llm.assert_called_once_with("test-doc-001", mock_ocr_results)
            mock_viz.assert_called_once_with("test-doc-001", mock_ocr_results["original_lines"])
    
    @pytest.mark.asyncio
    async def test_integrated_pipeline_document_not_found(self, mock_storage_client):
        """Test integrated pipeline when document is not found."""
        with patch('src.integration.orchestration.get_storage', return_value=mock_storage_client):
            # Setup mock to return None (document not found)
            mock_storage_client.download_blob.return_value = None
            
            # Test that FileNotFoundError is raised
            with pytest.raises(FileNotFoundError):
                await integrated_pipeline("nonexistent-doc", "test.pdf", "raw/nonexistent-doc.pdf")
    
    def test_load_system_config_success(self):
        """Test system configuration loading."""
        config_content = '''
generative_llm {
    url = "http://localhost:11435"
    model_name = "llama3.1:8b"
}
'''
        with patch('builtins.open', mock_open(read_data=config_content)):
            result = load_system_config()
            
            assert 'llm' in result
            assert result['llm']['url'] == 'http://localhost:11435'
            assert result['llm']['model_name'] == 'llama3.1:8b'
    
    def test_load_system_config_file_not_found(self):
        """Test system configuration loading when file doesn't exist."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                load_system_config()


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_mock(self):
        """Test complete end-to-end pipeline with mocked dependencies."""
        # This test simulates the complete workflow from notebook 04
        document_id = "integration-test-001"
        filename = "loan_application.pdf"
        blob_path = "raw/integration-test-001.pdf"
        
        with patch('src.integration.orchestration.get_storage') as mock_storage, \
             patch('src.integration.pipeline.extract_text_bboxes_with_ocr') as mock_extract, \
             patch('src.integration.pipeline.normalize_ocr_lines') as mock_normalize, \
             patch('src.integration.pipeline.convert_numpy_types') as mock_convert, \
             patch('src.integration.pipeline.load_system_config') as mock_sys_config, \
             patch('src.integration.pipeline.load_document_config') as mock_doc_config, \
             patch('src.integration.pipeline.extract_fields_with_llm') as mock_llm_extract, \
             patch('src.visualization.ocr_visualization.convert_from_bytes') as mock_convert_viz, \
             patch('src.visualization.ocr_visualization.plt') as mock_plt:
            
            # Setup all mocks
            mock_storage.return_value.download_blob.return_value = b"mock pdf data"
            mock_extract.return_value = ([{"text": "test", "bbox": {}, "confidence": 0.9, "page_num": 1}], [])
            mock_normalize.return_value = [{"text": "test", "type": "label_value"}]
            mock_convert.return_value = [{"text": "test", "type": "label_value"}]
            mock_sys_config.return_value = {'llm': {'url': 'http://localhost:11435', 'model_name': 'llama3.1:8b'}}
            mock_doc_config.return_value = {"credit_request": Mock()}
            mock_llm_extract.return_value = {"extracted_fields": {"test": "value"}, "missing_fields": [], "validation_results": {}}
            
            mock_image = Mock()
            mock_image.width = 800
            mock_image.height = 600
            mock_convert_viz.return_value = [mock_image]
            
            # Run the complete pipeline
            result = await integrated_pipeline(document_id, filename, blob_path)
            
            # Verify the complete workflow
            assert result["document_id"] == document_id
            assert result["filename"] == filename
            assert result["blob_path"] == blob_path
            assert "ocr_results" in result
            assert "llm_results" in result
            assert "processing_summary" in result
            
            # Verify processing summary
            summary = result["processing_summary"]
            assert "total_ocr_elements" in summary
            assert "normalized_elements" in summary
            assert "extracted_fields" in summary
            assert "validation_errors" in summary


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
