# Async Document Processing with Celery

*Transform synchronous document processing into scalable, asynchronous workflows using Celery workers*

---

## What You'll Learn

This notebook demonstrates how to implement asynchronous document

---

## Core Problem

**Synchronous Processing Limitations:**
- Documents processed one at a time
- Main application blocks during processing
- No horizontal scaling capability
- Poor user experience with long wait times
- Resource underutilization

**Solution: Asynchronous Processing with Celery**
- Background task execution
- Concurrent document processing
- Non-blocking user interactions
- Horizontal scaling with multiple workers
- Real-time status monitoring

## What You'll Build

### 1. Celery Configuration
- Redis broker and result backend
- Task serialization and routing
- Worker configuration and scaling

### 2. Async Processing Pipeline
- Document upload triggers background processing
- OCR and LLM tasks run asynchronously
- Status updates throughout the pipeline
- Error handling and retry mechanisms

### 3. Monitoring & Status Tracking
- Real-time processing status updates
- Task progress monitoring
- Error reporting and logging
- Job completion notifications

---

## Task Status Flow

Here's how documents flow through the async processing pipeline:

```
pending → ocr_running → llm_running → done
     ↓         ↓           ↓         ↓
   failed ← failed ← failed ← failed
```

**Status Transitions:**
- `pending`: Document uploaded, waiting for worker pickup
- `ocr_running`: Celery worker processing OCR extraction
- `llm_running`: Celery worker processing LLM field extraction
- `done`: All processing completed successfully
- `failed`: Processing failed at any stage (with error details)

## Core Concepts

### 1. Celery Architecture
- **Broker**: Redis for message queuing
- **Workers**: Background task processors
- **Tasks**: Individual processing units
- **Results**: Task outcome storage

### 2. Task Chaining
- Sequential task execution
- Error propagation
- Status updates between tasks
- Pipeline orchestration

### 3. Async Benefits
- **Scalability**: Multiple workers process documents concurrently
- **Reliability**: Failed tasks can be retried
- **Monitoring**: Real-time status tracking
- **Performance**: Non-blocking operations

## Learning Resources

### Celery Documentation
- [Celery User Guide](https://docs.celeryproject.org/en/stable/userguide/index.html)
- [Celery Best Practices](https://docs.celeryproject.org/en/stable/userguide/tasks.html#best-practices)
- [Celery Monitoring](https://docs.celeryproject.org/en/stable/userguide/monitoring.html)

### Redis Integration
- [Redis as Celery Broker](https://docs.celeryproject.org/en/stable/getting-started/brokers/redis.html)
- [Redis Configuration](https://redis.io/docs/manual/config/)

### Production Considerations
- [Celery in Production](https://docs.celeryproject.org/en/stable/userguide/optimizing.html)
- [Worker Scaling](https://docs.celeryproject.org/en/stable/userguide/workers.html#concurrency)
- [Task Routing](https://docs.celeryproject.org/en/stable/userguide/routing.html)

---

## System Architecture Integration

### Docker Compose Services
- **Redis**: Message broker and result backend
- **Celery Worker**: Background task processor
- **PostgreSQL**: Document metadata and status
- **Azurite**: Document storage

### Task Flow
1. **Document Upload** → DMS creates document record
2. **Task Trigger** → Async processor starts Celery task
3. **OCR Processing** → Background OCR task execution
4. **LLM Processing** → Background LLM task execution
5. **Status Updates** → Real-time status monitoring
6. **Completion** → Final status and result storage

## Implementation Walkthrough

### 1. Celery App Configuration
```python
celery_app = Celery(
    "credit_ocr",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["src.tasks.pipeline_tasks"],
)
```

### 2. Task Definition
```python
@celery_app.task(bind=True)
def process_ocr_task(self, document_id: str) -> str:
    # OCR processing logic
    return document_id
```

### 3. Async Processing Trigger
```python
task = process_document_async.delay(document_id)
```

### 4. Status Monitoring
```python
status = async_processor.get_processing_status(document_id)
```

---

## Expected Results

### Processing Flow
1. Document uploaded to DMS
2. Async processing triggered
3. Celery worker picks up task
4. OCR processing in background
5. LLM processing in background
6. Status updates throughout
7. Final completion notification

### Status Transitions
- `pending extraction` → `ocr running` → `llm running` → `done`
- Real-time status updates via database
- Error handling with failed status
- Job completion timestamps

## Common Issues & Solutions

### Worker Not Starting
- Check Redis connection
- Verify Celery app configuration
- Check Docker Compose services

### Tasks Not Processing
- Verify worker is running
- Check task routing
- Monitor Redis queue

### Status Not Updating
- Check database connections
- Verify status update calls
- Monitor task execution

## Extending the Solution

### Multiple Workers
- Scale horizontally with more workers
- Load balancing across workers
- Worker specialization (OCR vs LLM)

### Task Prioritization
- High-priority document processing
- Queue routing and priorities
- SLA-based processing

### Advanced Monitoring
- Celery Flower for task monitoring
- Prometheus metrics integration
- Custom dashboards

## Production Considerations

### Scaling
- **Horizontal Scaling**: Add more Celery workers
- **Vertical Scaling**: Increase worker concurrency
- **Queue Management**: Separate queues for different task types

### Reliability
- **Task Retries**: Automatic retry on failure
- **Dead Letter Queues**: Failed task handling
- **Health Checks**: Worker and broker monitoring

### Performance
- **Connection Pooling**: Database and Redis connections
- **Task Optimization**: Efficient task design
- **Resource Management**: Memory and CPU limits

### Security
- **Task Serialization**: Secure task data
- **Worker Isolation**: Sandboxed task execution
- **Access Control**: Worker authentication

## Next Steps

1. **Scale Testing**: Test with multiple documents
2. **Error Scenarios**: Test failure handling
3. **Performance Tuning**: Optimize worker configuration
4. **Monitoring Setup**: Implement production monitoring
5. **Load Testing**: Test under high document volume

---

## Getting Started

**Prerequisites:**
- Docker services running (`docker compose up -d`)
- Celery worker running (`docker compose up celery-worker`)
- Completed notebooks 1-6

**Run the notebook:**
```bash
cd notebooks/7-async-processing
jupyter notebook 07_async_processing.ipynb
```

Transform your document processing from blocking to scalable, asynchronous workflows.
