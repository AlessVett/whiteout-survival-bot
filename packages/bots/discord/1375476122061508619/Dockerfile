FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for microservice
RUN pip install --no-cache-dir \
    fastapi==0.115.5 \
    uvicorn[standard]==0.34.0 \
    python-consul==1.1.0 \
    aio-pika==9.5.1 \
    httpx==0.27.2

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose service port
EXPOSE 8001

# Run the microservice wrapper
CMD ["uvicorn", "microservice:app", "--host", "0.0.0.0", "--port", "8001"]