# Multi-stage Dockerfile for UrbanMove FastAPI application
# Optimized for AWS ECS/Docker container deployment in Private Subnet

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage (minimal image)
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY ./app ./app
COPY ./app/main.py .

# Health check (ALB will use this)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health').read()"

# Environment variables for cloud deployment
ENV PYTHONUNBUFFERED=1
ENV DATABASE_URL=postgresql://urbanmove:urbanmove_pass@postgres:5432/urbanmove_db
ENV ENVIRONMENT=production
ENV AWS_REGION=us-east-1

# Expose port (ALB will forward traffic)
EXPOSE 8000

# Run FastAPI application with Uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
