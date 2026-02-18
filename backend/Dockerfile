# ============================================================================
# Backend Dockerfile - FastAPI + Python 3.13
# ============================================================================
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies (g++ required to compile chroma-hnswlib)
RUN apt-get update && apt-get install -y \
    curl \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies
RUN uv sync --no-dev

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Ensure DB schema is ready, then start server
CMD ["sh", "-c", "python -m uv run python startup.py && python -m uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
