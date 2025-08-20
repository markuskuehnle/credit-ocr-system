# Credit OCR System for Credit Evaluation

*Transform manual credit document processing into intelligent, automated workflows using local AI and microservices architecture.*

---

## Quick Start

**Ready to build? Start here:**

1. **Setup Infrastructure** → [`notebooks/1-setup/`](./notebooks/1-setup/)
   - **Executable Guide**: [`01_setup.ipynb`](./notebooks/1-setup/01_setup.ipynb) - Step-by-step setup
   - **Deep Dive**: [`README.md`](./notebooks/1-setup/README.md) - Architecture & learning resources

2. **OCR Text Extraction** → [`notebooks/2-ocr-based-text-extraction/`](./notebooks/2-ocr-based-text-extraction/)
   - **Executable Guide**: [`02_ocr_text_extraction.ipynb`](./notebooks/2-ocr-based-text-extraction/02_ocr_text_extraction.ipynb) - EasyOCR implementation with spatial analysis
   - **Deep Dive**: [`README.md`](./notebooks/2-ocr-based-text-extraction/README.md) - OCR theory, spatial reconstruction, and production considerations

3. **Next Steps** → Continue with subsequent notebooks for LLM integration and document analysis

---

## What This System Does

The Credit OCR System automates the processing of credit-related documents:

- **Extracts** key financial data from PDFs and scanned documents
- **Analyzes** information using local AI models (no external APIs)
- **Validates** data across multiple document types
- **Stores** results securely in local databases
- **Processes** documents asynchronously for scale

### Real-World Impact

**Before:** Loan officers manually review 15-20 page applications, taking hours per case  
**After:** Automated processing extracts and analyzes key data in under 10 minutes

## System Architecture

### Core Services

| Service      | Purpose                                   | Technology            |
|--------------|-------------------------------------------|-----------------------|
| **PostgreSQL** | Document metadata & extracted data storage | Relational database   |
| **Redis**      | Message broker for background job processing | In-memory data store  |
| **Ollama**     | Local AI model hosting (Llama3.1:8b)        | LLM inference server  |
| **Azurite**    | Document file storage (Azure Blob emulator) | Object storage        |

### Key Design Principles

- **Local-First**: All processing happens on your infrastructure
- **Privacy-Focused**: No external AI APIs or data sharing
- **Microservices**: Each service scales independently
- **Production-Ready**: Docker Compose orchestration with health checks

## Learning Path

### For Beginners
Start with the tutorial in [`notebooks/1-setup/README.md`](./notebooks/1-setup/README.md) which explains:
- Why microservices architecture
- How document processing pipelines work
- Technology choices and alternatives
- Real-world enterprise patterns

### For Practitioners
Jump straight to [`notebooks/1-setup/01_setup.ipynb`](./notebooks/1-setup/01_setup.ipynb) for:
- Executable setup steps
- Service validation
- Health monitoring
- Configuration management

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
├── README.md                 # This file - project overview
├── compose.yml              # Docker services orchestration
├── pyproject.toml           # Python dependencies
├── config/                  # Configuration files
├── notebooks/               # Learning & development notebooks
│   ├── 1-setup/            # Infrastructure setup tutorial
│   │   ├── README.md       # Architecture deep dive
│   │   └── 01_setup.ipynb  # Executable setup guide
│   └── 2-ocr-based-text-extraction/  # OCR text extraction tutorial
│       ├── README.md       # OCR theory & spatial analysis guide
│       └── 02_ocr_text_extraction.ipynb  # EasyOCR implementation
├── src/                    # Application source code (future)
└── tests/                  # Test suites (future)
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
