# OCR System for Credit Evaluation

*Transform manual credit document processing into intelligent, automated workflows using local AI and microservices architecture.*

This project is a comprehensive tutorial that guides you through building a scalable OCR system for credit request document processing. You'll learn how to extract, analyze, and validate financial data from PDFs and scanned documents using local AI models and microservices architecture. The tutorial covers everything from infrastructure setup to advanced spatial analysis techniques, providing you with the skills to build production-ready document processing systems.

![Credit OCR System Architecture](docs/imgs/architecture.png)

---

## What This System Does

The Credit OCR System automates the processing of credit-related documents:

- **Extracts** key financial data from PDFs and scanned documents
- **Analyzes** information using local AI models (no external APIs)
- **Validates** data across multiple document types
- **Stores** results securely in local databases
- **Processes** documents asynchronously for scale

### Document Processing Pipeline

1. **Document Upload** → Documents are uploaded to a Document Management System (DMS)
2. **OCR Processing** → EasyOCR extracts text with spatial analysis and bounding boxes
3. **LLM Field Extraction** → Local AI models extract and validate structured business data
4. **Data Validation** → Business rules validate extracted information with confidence scores
5. **Database Storage** → Extracted data is stored in PostgreSQL for quick retrieval
6. **API Access** → Frontend applications can access the processed data via API
7. **User Review** → Credit officers can review extracted information, confidence scores, and document overlays
8. **Manual Correction** → Users can correct any inaccuracies in the extracted data

### Real-World Impact

**Before:** Loan officers manually review 15-20 page applications, taking hours per case  
**After:** Automated processing extracts and analyzes key data in under 10 minutes, with human oversight for accuracy

## System Architecture

### Core Services

| Service      | Purpose                                   | Technology            |
|--------------|-------------------------------------------|-----------------------|
| **PostgreSQL** | Document metadata & extracted data storage | Relational database   |
| **Redis**      | Message broker for background job processing | In-memory data store  |
| **Ollama**     | Local LLM model hosting (Llama3.1:8b)        | LLM inference server  |
| **Azurite**    | Document file storage (Azure Blob emulator) | Object storage        |

### Key Design Principles

- **Local-First**: All processing happens on your infrastructure
- **Privacy-Focused**: No external AI APIs or data sharing
- **Microservices**: Each service scales independently
- **Production-Ready**: Docker Compose orchestration with health checks

---

## Quick Start

**Ready to build? Start here:**

1. **Setup Infrastructure** → [`notebooks/1-setup/`](./notebooks/1-setup/)
   - **Executable Guide**: [`01_setup.ipynb`](./notebooks/1-setup/01_setup.ipynb) - Step-by-step setup
   - **Deep Dive**: [`README.md`](./notebooks/1-setup/README.md) - Architecture & learning resources

2. **OCR Text Extraction** → [`notebooks/2-ocr-based-text-extraction/`](./notebooks/2-ocr-based-text-extraction/)
   - **Executable Guide**: [`02_ocr_text_extraction.ipynb`](./notebooks/2-ocr-based-text-extraction/02_ocr_text_extraction.ipynb) - EasyOCR implementation with spatial analysis
   - **Deep Dive**: [`README.md`](./notebooks/2-ocr-based-text-extraction/README.md) - OCR theory, spatial reconstruction, and production considerations

3. **LLM Field Extraction** → [`notebooks/3-llm-field-extraction/`](./notebooks/3-llm-field-extraction/)
   - **Executable Guide**: [`03_llm_field_extraction.ipynb`](./notebooks/3-llm-field-extraction/03_llm_field_extraction.ipynb) - Local LLM processing with llama3.1:8b model
   - **Deep Dive**: [`README.md`](./notebooks/3-llm-field-extraction/README.md) - LLM integration, prompt engineering, and field validation

4. **Next Steps** → Continue with subsequent notebooks for advanced document analysis

## Development Workflow

### Initial Setup
```bash
# Clone and setup
git clone https://github.com/markuskuehnle/credit-ocr-system
cd credit-ocr-system

# Create environment and install dependencies
uv venv && uv sync

# Start services
docker compose up -d

# Launch development environment
uv run jupyter notebook
```

### Daily Development
```bash
# Check service status
docker compose ps

# View logs
docker compose logs [service-name]

# Restart if needed
docker compose restart [service-name]
```

## Prerequisites

### Required Software
- **Python 3.10+** - Runtime environment
- **Docker Desktop** - Container orchestration
- **UV Package Manager** - Dependency management
- **Git** - Version control (optional)

### System Requirements
- **Minimum**: 8GB RAM, 15GB disk space
- **Recommended**: 16GB RAM, 25GB disk space
- **CPU**: Multi-core processor (Intel/AMD x64 or Apple Silicon)

## Beyond Credit Processing

This system demonstrates architectural patterns used in:

- **RAG Systems** - Document preprocessing → Vector databases → AI generation
- **AI Agent Architectures** - Microservices → Multi-agent communication
- **Enterprise Document Intelligence** - Legal, medical, research document processing
- **Compliance Systems** - Automated document analysis and validation

The patterns you'll learn here are foundational for building any modern document-based AI system.

## Project Structure

```
credit-ocr-system/
├── README.md                             # This file - project overview
├── compose.yml                           # Docker services orchestration
├── pyproject.toml                        # Python dependencies
├── config/                               # Configuration files
├── notebooks/                            # Learning & development notebooks
│   ├── 1-setup/                          # Infrastructure setup tutorial
│   │   ├── README.md                     # Architecture deep dive
│   │   └── 01_setup.ipynb                # Executable setup guide
│   ├── 2-ocr-based-text-extraction/      # OCR text extraction tutorial
│   │   ├── README.md                     # OCR theory & spatial analysis guide
│   │   └── 02_ocr_text_extraction.ipynb  # EasyOCR implementation
│   └── 3-llm-field-extraction/           # LLM field extraction tutorial
│       ├── README.md                     # LLM integration & prompt engineering guide
│       └── 03_llm_field_extraction.ipynb # Local LLM processing implementation
├── src/                                  # Application source code (future)
└── tests/                                # Test suites (future)
```

## Configuration

The system uses a layered configuration approach:

- **Development**: Simple constants in notebooks
- **Production**: Configuration files in `config/`
- **Deployment**: Docker Compose environment variables

## Troubleshooting

### Common Issues

**Services won't start**
```bash
# Check Docker Desktop is running
docker info

# View service logs
docker compose logs [service-name]

# Reset everything
docker compose down && docker compose up -d
```

**Port conflicts**
- PostgreSQL (5432), Redis (6379), Ollama (11435), Azurite (10000)
- Stop conflicting services or modify ports in `compose.yml`

**Resource issues**
- Increase Docker Desktop memory allocation (Settings → Resources)
- Close unnecessary applications
- Ensure sufficient disk space

---

## Ready to Start?

**👉 Begin with the setup tutorial: [`notebooks/1-setup/README.md`](./notebooks/1-setup/README.md)**

Transform your document processing workflows from manual to intelligent in under 30 minutes.
