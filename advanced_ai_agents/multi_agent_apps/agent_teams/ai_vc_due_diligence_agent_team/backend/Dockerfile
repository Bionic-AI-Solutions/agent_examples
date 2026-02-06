FROM python:3.11-slim-bookworm AS builder

# Install uv package manager for faster dependency installation
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files
COPY backend/requirements.txt ./backend_requirements.txt
COPY requirements.txt ./agent_requirements.txt

# Combine and install all dependencies
RUN cat backend_requirements.txt agent_requirements.txt > all_requirements.txt && \
    uv pip install --system -r all_requirements.txt

# ============================================================================
# Final image
# ============================================================================
FROM python:3.11-slim-bookworm

# Install runtime dependencies (including WeasyPrint requirements for PDF generation)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    libpq-dev \
    postgresql-client \
    # WeasyPrint dependencies for PDF generation
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fonts-dejavu-core \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install gunicorn and psycopg2-binary
RUN pip install --no-cache-dir gunicorn psycopg2-binary

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set working directory
WORKDIR /app

# Copy application code
# Copy parent directory files (agent.py, tools.py, __init__.py)
COPY agent.py tools.py __init__.py ./
COPY requirements.txt ./

# Copy backend application
COPY backend/ ./backend/

# Create necessary directories
RUN mkdir -p outputs artifacts logs && \
    chmod 777 outputs artifacts logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')"

# Use gunicorn with uvicorn workers for production
CMD ["gunicorn", "backend.main:app", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "300", \
     "--keep-alive", "5", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
