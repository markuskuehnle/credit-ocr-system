import pytest
from unittest.mock import Mock, patch
import asyncio

# Import the functions from src that notebook 04 uses
from src.integration.orchestration import integrated_pipeline
from src.integration.pipeline import process_document_with_ocr, process_document_with_llm
from src.visualization.ocr_visualization import visualize_ocr_results
from src.config.system import load_system_config
from src.storage.storage import get_storage, Stage


class TestNotebook04Workflow:
    """Simple test of the exact workflow from notebook 04."""
    
    @pytest.mark.asyncio
    async def test_notebook04_workflow(self):
        """Test the exact workflow as executed in notebook 04."""
        
        # Step 1: Document setup (as in notebook 04)
        document_id = "test-document-001"
        filename = "loan_application.pdf"
        blob_path = f"raw/{document_id}.pdf"
        
        # Mock all the dependencies to avoid real service calls
        with patch('src.storage.storage.get_storage') as mock_get_storage, \
             patch('src.integration.pipeline.extract_text_bboxes_with_ocr') as mock_extract, \
             patch('src.integration.pipeline.normalize_ocr_lines') as mock_normalize, \
             patch('src.integration.pipeline.convert_numpy_types') as mock_convert, \
             patch('src.integration.pipeline.load_system_config') as mock_sys_config, \
             patch('src.integration.pipeline.load_document_config') as mock_doc_config, \
             patch('src.integration.pipeline.extract_fields_with_llm') as mock_llm_extract, \
             patch('src.visualization.ocr_visualization.convert_from_bytes') as mock_convert_viz, \
             patch('src.visualization.ocr_visualization.plt') as mock_plt:
            
            # Setup all mocks
            mock_storage = Mock()
            mock_get_storage.return_value = mock_storage
            mock_storage.download_blob.return_value = b"mock pdf data"
            
            # Mock OCR processing
            mock_extract.return_value = ([{"text": "Company Name: Test Corp", "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20}, "confidence": 0.95, "page_num": 1}], [])
            mock_normalize.return_value = [{"text": "Company Name: Test Corp", "type": "label_value", "page_num": w1, "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20}, "confidence": 0.95}]
            mock_convert.return_value = [{"text": "Company Name: Test Corp", "type": "label_value", "page_num": 1, "bbox": {"x1": 100, "y1": 200, "x2": 300, "y2": 220, "width": 200, "height": 20}, "confidence": 0.95}]
            
            # Mock LLM processing
            mock_sys_config.return_value = {'llm': {'url': 'http://localhost:11435', 'model_name': 'llama3.1:8b'}}
            mock_doc_config.return_value = {"credit_request": Mock()}
            mock_llm_extract.return_value = {"extracted_fields": {"company_name": "Test Corp"}, "missing_fields": [], "validation_results": {}}
            
            # Mock visualization
            mock_image = Mock()
            mock_image.width = 800
            mock_image.height = 600
            mock_convert_viz.return_value = [mock_image]
            mock_fig = Mock()
            mock_ax = Mock()
            mock_plt.subplots.return_value = (mock_fig, mock_ax)
            
            # Step 2: Upload document to blob storage (as in notebook 04)
            storage_client = get_storage()
            storage_client.upload_blob(
                uuid=document_id,
                stage=Stage.RAW,
                ext=".pdf",
                data=b"mock pdf data",
                overwrite=True
            )
            
            # Step 3: Run integrated pipeline (as in notebook 04)
            results = await integrated_pipeline(document_id, filename, blob_path)
            
            # Verify results (as expected in notebook 04)
            assert results["document_id"] == document_id
            assert results["filename"] == filename
            assert results["blob_path"] == blob_path
            assert "ocr_results" in results
            assert "llm_results" in results
            assert "processing_summary" in results
            
            # Verify processing summary
            summary = results["processing_summary"]
            assert "total_ocr_elements" in summary
            assert "normalized_elements" in summary
            assert "extracted_fields" in summary
            assert "validation_errors" in summary
            
            print("✅ Notebook 04 workflow test passed!")
            print(f"   - Document ID: {results['document_id']}")
            print(f"   - OCR elements: {summary['total_ocr_elements']}")
            print(f"   - Extracted fields: {summary['extracted_fields']}")


if __name__ == "__main__":
    # Run test if executed directly
    pytest.main([__file__, "-v"])
