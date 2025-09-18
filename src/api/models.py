from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    """Document processing status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    OCR_RUNNING = "ocr_running"
    LLM_RUNNING = "llm_running"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: ProcessingStatus = Field(..., description="Initial processing status")
    message: str = Field(..., description="Response message")


class BoundingBoxData(BaseModel):
    """Bounding box coordinates."""
    x1: float = Field(..., description="Left x coordinate")
    y1: float = Field(..., description="Top y coordinate")
    width: float = Field(..., description="Width of bounding box")
    height: float = Field(..., description="Height of bounding box")


class OcrElementData(BaseModel):
    """OCR element with text, confidence, and bounding box."""
    text: str = Field(..., description="Extracted text")
    confidence: float = Field(..., description="OCR confidence score")
    bbox: BoundingBoxData = Field(..., description="Bounding box coordinates")
    page_num: int = Field(..., description="Page number")


class ExtractedFieldData(BaseModel):
    """Extracted field with LLM result."""
    field_name: str = Field(..., description="Name of the extracted field")
    extracted_value: Optional[str] = Field(None, description="Extracted value")
    confidence_score: Optional[float] = Field(None, description="Confidence score")
    source_ocr_elements: List[str] = Field(default_factory=list, description="Source OCR element IDs")


class ProcessingSummaryData(BaseModel):
    """Summary of document processing results."""
    total_ocr_elements: int = Field(..., description="Total OCR elements extracted")
    normalized_elements: int = Field(..., description="Number of normalized elements")
    extracted_fields: int = Field(..., description="Number of fields extracted")
    validation_errors: int = Field(..., description="Number of validation errors")


class DocumentStatusResponse(BaseModel):
    """Response model for document processing status."""
    document_id: str = Field(..., description="Document identifier")
    status: ProcessingStatus = Field(..., description="Current processing status")
    filename: Optional[str] = Field(None, description="Original filename")
    upload_timestamp: Optional[datetime] = Field(None, description="Upload timestamp")
    processing_started: Optional[datetime] = Field(None, description="Processing start time")
    processing_completed: Optional[datetime] = Field(None, description="Processing completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class DocumentResultsResponse(BaseModel):
    """Response model for complete document processing results."""
    document_id: str = Field(..., description="Document identifier")
    filename: str = Field(..., description="Original filename")
    status: ProcessingStatus = Field(..., description="Processing status")
    processing_summary: Optional[ProcessingSummaryData] = Field(None, description="Processing summary")
    extracted_fields: List[ExtractedFieldData] = Field(default_factory=list, description="Extracted fields")
    ocr_elements: List[OcrElementData] = Field(default_factory=list, description="OCR elements")
    has_visualization: bool = Field(False, description="Whether visualization is available")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: Dict[str, str] = Field(..., description="Individual service statuses")
