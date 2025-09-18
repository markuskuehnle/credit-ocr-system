# Credit OCR System API

A FastAPI-based REST API for processing credit documents with OCR and LLM field extraction.

## Features

- **Document Upload**: Upload PDF documents via REST API or web interface
- **Async Processing**: Documents are processed asynchronously using Celery workers
- **Status Tracking**: Real-time status updates for document processing
- **Field Extraction**: Automated extraction of structured fields from credit documents
- **Visualization**: OCR results with bounding boxes overlaid on original documents
- **Modern UI**: Beautiful web interface for document upload and results viewing

## API Endpoints

### Document Operations

- `POST /api/v1/upload` - Upload a PDF document for processing
- `GET /api/v1/status/{document_id}` - Get processing status for a document
- `GET /api/v1/results/{document_id}` - Get complete processing results
- `GET /api/v1/documents` - List all documents with pagination
- `GET /api/v1/visualization/{document_id}?page={page}` - Get visualization image

### System Operations

- `GET /api/v1/health` - Health check endpoint
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

### Web Interface

- `GET /` - Upload and view documents via web interface

## Quick Start

### 1. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 2. Start Services

Make sure the required services are running:

```bash
# Start infrastructure services
docker-compose up -d postgres redis azurite ollama
```

### 3. Run the API

```bash
# Development mode
python run_api.py

# Or using uvicorn directly
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/api/v1/health

## Configuration

The API can be configured using environment variables:

### API Settings
- `API_HOST` - Host to bind to (default: 0.0.0.0)
- `API_PORT` - Port to listen on (default: 8000)
- `API_DEBUG` - Enable debug mode (default: false)
- `API_RELOAD` - Enable auto-reload in development (default: true)
- `ENVIRONMENT` - Environment mode: development/production (default: development)

### CORS Settings
- `CORS_ORIGINS` - Allowed CORS origins, comma-separated (default: *)

### File Upload Settings
- `MAX_FILE_SIZE` - Maximum file size in MB (default: 50)
- `ENABLE_BACKGROUND_PROCESSING` - Enable async processing (default: true)

### Database & Storage
- `DATABASE_HOST` - PostgreSQL host (default: postgres in Docker, localhost otherwise)
- `REDIS_HOST` - Redis host (default: redis in Docker, localhost otherwise)
- `OLLAMA_URL` - Ollama LLM service URL

## Usage Examples

### Upload a Document (cURL)

```bash
curl -X POST "http://localhost:8000/api/v1/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/document.pdf"
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "pending",
  "message": "Document uploaded successfully and processing started"
}
```

### Check Processing Status

```bash
curl "http://localhost:8000/api/v1/status/550e8400-e29b-41d4-a716-446655440000"
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "filename": "document.pdf",
  "upload_timestamp": "2024-01-01T12:00:00Z",
  "processing_completed": "2024-01-01T12:05:00Z"
}
```

### Get Processing Results

```bash
curl "http://localhost:8000/api/v1/results/550e8400-e29b-41d4-a716-446655440000"
```

Response:
```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "document.pdf",
  "status": "completed",
  "processing_summary": {
    "total_ocr_elements": 156,
    "normalized_elements": 89,
    "extracted_fields": 12,
    "validation_errors": 0
  },
  "extracted_fields": [
    {
      "field_name": "applicant_name",
      "extracted_value": "John Doe",
      "confidence_score": 0.95,
      "source_ocr_elements": ["elem_1", "elem_2"]
    }
  ],
  "has_visualization": true
}
```

## Processing Pipeline

1. **Upload**: PDF document is uploaded and stored in blob storage
2. **OCR Processing**: EasyOCR extracts text with bounding boxes
3. **Normalization**: OCR results are structured and normalized
4. **LLM Extraction**: Ollama LLM extracts specific fields based on document type
5. **Visualization**: OCR results are overlaid on the original document
6. **Storage**: All results are stored in blob storage and metadata in database

## Status Values

- `pending` - Document uploaded, waiting for processing
- `processing` - General processing state
- `ocr_running` - OCR text extraction in progress
- `llm_running` - LLM field extraction in progress
- `completed` - All processing completed successfully
- `failed` - Processing failed with error

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `202` - Accepted (processing not complete yet)
- `400` - Bad Request (invalid file, parameters)
- `404` - Not Found (document doesn't exist)
- `500` - Internal Server Error

Error responses follow this format:
```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "detail": "Additional technical details (optional)"
}
```

## Development

### Project Structure

```
src/api/
├── __init__.py
├── main.py          # FastAPI application
├── routes.py        # API route handlers
├── models.py        # Pydantic response models
├── config.py        # API configuration
├── templates/       # Web interface templates
│   └── index.html
└── README.md        # This file
```

### Running Tests

```bash
# Run API-specific tests
pytest tests/test_api.py -v

# Run all tests
pytest tests/ -v
```

### Code Style

The API follows these conventions:
- Type hints on all functions and variables
- Pydantic models for request/response validation
- Descriptive variable names over comments
- Comprehensive error handling and logging
- RESTful URL design

## Deployment

### Production Considerations

1. **Environment Variables**: Set `ENVIRONMENT=production`
2. **CORS**: Configure specific allowed origins instead of "*"
3. **File Limits**: Adjust `MAX_FILE_SIZE` based on requirements
4. **Logging**: Configure structured logging for production
5. **Health Checks**: Use `/api/v1/health` endpoint for load balancer health checks
6. **Reverse Proxy**: Run behind nginx or similar for SSL termination

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build api

# Or run standalone
docker build -t credit-ocr-api .
docker run -p 8000:8000 credit-ocr-api
```

## Monitoring

The API provides several monitoring endpoints:

- Health checks at `/api/v1/health`
- Structured JSON logs for processing events
- FastAPI automatic metrics (enable with middleware)
- Celery task monitoring via Celery Flower (if enabled)

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the logs for error details
3. Verify all required services are running
4. Check environment variable configuration
