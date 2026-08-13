FROM python:3.12-slim

# Install system dependencies required by some Python packages (lxml, psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    libxml2 \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Python requirements and install dependencies first (better layer caching)
# Also install API-specific requirements to ensure fastapi/uvicorn are present
COPY requirements.txt .
COPY backend/api/requirements.txt ./api-requirements.txt
RUN echo "=== ROOT requirements.txt ===" && \
    cat requirements.txt && \
    echo "=== API requirements.txt ===" && \
    cat api-requirements.txt && \
    echo "=== Installing... ===" && \
    pip install --no-cache-dir -r api-requirements.txt -r requirements.txt && \
    python -c "import uvicorn; print('uvicorn OK:', uvicorn.__version__)" && \
    python -c "import fastapi; print('fastapi OK:', fastapi.__version__)"

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p backend/data/master_resume backend/logs

# Install Playwright browsers (if playwright is used)
RUN python -m playwright install --with-deps chromium 2>/dev/null || true

# Run the API server using python -m uvicorn (not the bare uvicorn binary)
# Using $PORT so Railway can set the port at runtime
ENV PYTHONPATH=/app
CMD python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
