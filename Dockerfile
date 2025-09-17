FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Default command (can be overridden in compose.yml)
CMD ["celery", "-A", "src.celery_app", "worker", "--loglevel=info"]


