FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    graphviz \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
# Build context is project root, so api/requirements.txt
COPY api/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary directories for API service
# Build context is project root (.), so we copy specific directories
COPY api/ /app/api/
COPY nexus_utils/ /app/nexus_utils/
COPY agents/ /app/agents/
COPY tools/ /app/tools/
COPY config/ /app/config/
COPY prompts/ /app/prompts/
# Note: projects/ directory is mounted via EFS, not copied to image

# Install nexus_utils as a package (if setup.py exists)
RUN if [ -f /app/nexus_utils/setup.py ]; then \
      pip install --no-cache-dir -e /app/nexus_utils || \
      (cd /app && pip install --no-cache-dir -e ./nexus_utils) || \
      echo "Warning: nexus_utils installation failed, but continuing..."; \
    fi

# Set PYTHONPATH to include /app so Python can find all modules
ENV PYTHONPATH=/app:/app/nexus_utils

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]