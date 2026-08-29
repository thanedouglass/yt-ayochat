# Production-ready Dockerfile for Google Cloud Run
FROM python:3.11-slim

# Set environment variables for Python & Cloud Run
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080 \
    HOST=0.0.0.0

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency specifications first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip and install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and assets
COPY . .

# Expose default Cloud Run port
EXPOSE 8080

# Health check to ensure FastAPI telemetry server is responsive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8080}/api/health || exit 1

# Start the FastAPI Telemetry & Study GUI Server
CMD ["sh", "-c", "uvicorn src.server:app --host 0.0.0.0 --port ${PORT:-8080}"]
