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

# Install Python dependencies directly (avoids requirements.txt copy issues)
RUN pip install --no-cache-dir \
    "fastapi>=0.110.0" \
    "uvicorn[standard]>=0.29.0" \
    "pydantic>=2.12.0" \
    "pydantic-settings>=2.6.0" \
    "python-dotenv>=1.0.0" \
    "pyyaml>=6.0" \
    "sqlalchemy>=2.0.25" \
    "aiosqlite>=0.19.0" \
    "asyncpg>=0.29.0" \
    "python-multipart>=0.0.9" \
    "aiofiles>=23.2.1" \
    "httpx>=0.27.0" \
    "aiohttp>=3.9.0" \
    "beautifulsoup4>=4.12.0" \
    "lxml>=4.9.0" \
    "pandas>=2.0.0" \
    "openpyxl>=3.1.0" \
    "python-docx>=1.1.0" \
    "playwright>=1.40.0" \
    "tenacity>=8.3.0" \
    "python-dateutil>=2.8.0" \
    "rich>=13.7.0" \
    "typer>=0.9.0" \
    "boto3>=1.34.0" \
    "supabase>=2.3.0" \
    "openai>=1.0.0" && \
    python -c "import uvicorn; print('uvicorn OK:', uvicorn.__version__)" && \
    python -c "import fastapi; print('fastapi OK:', fastapi.__version__)"

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p backend/data/master_resume backend/logs

# Install Playwright browsers (if playwright is used)
RUN python -m playwright install --with-deps chromium 2>/dev/null || true

# Run the API server using python -m uvicorn (not the bare uvicorn binary)
# The build context is backend/, so api.main:app loads backend/api/main.py
# Using shell form so ${PORT:-8000} is expanded by the shell at runtime
ENV PYTHONPATH=/app
CMD python -m uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
