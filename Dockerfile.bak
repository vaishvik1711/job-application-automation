FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements
COPY backend/requirements.txt .
COPY backend/api/requirements.txt ./api-requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api-requirements.txt

# Copy backend code
COPY backend/ ./

# Create necessary directories
RUN mkdir -p data/master_resume logs

# Expose port for the FastAPI server
EXPOSE 8000

# Run the API server (use $PORT on Railway, fallback to 8000)
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
