-- Database schema for DMS (Document Management System)
-- This file contains the initial database structure

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Example table structure (modify as needed for your use case)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optional status columns for processing lifecycle
ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS text_extraction_status VARCHAR(50)
        DEFAULT 'not ready'
        CHECK (text_extraction_status IN ('not ready', 'ready', 'in progress', 'completed', 'failed')),
    ADD COLUMN IF NOT EXISTS processing_status VARCHAR(50)
        DEFAULT 'pending extraction'
        CHECK (processing_status IN ('pending extraction', 'ocr running', 'llm running', 'done'));

CREATE TABLE IF NOT EXISTS ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER,
    text_content TEXT,
    confidence_score DECIMAL(3,2),
    bounding_boxes JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Extraction jobs to track end-to-end processing
CREATE TABLE IF NOT EXISTS extraction_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    status VARCHAR(50) DEFAULT 'pending extraction',
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- Index for better query performance
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_ocr_results_document_id ON ocr_results(document_id);
CREATE INDEX IF NOT EXISTS idx_ocr_results_page_number ON ocr_results(page_number);
CREATE INDEX IF NOT EXISTS idx_extraction_jobs_document_id ON extraction_jobs(document_id);
