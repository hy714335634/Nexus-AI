FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (matching local environment)
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    graphviz \
    git \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
# Build context is project root, so api/requirements.txt
COPY api/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files (matching local environment structure)
# Build context is project root (.), so we copy specific directories
COPY api/ /app/api/
COPY nexus_utils/ /app/nexus_utils/
COPY agents/ /app/agents/
COPY tools/ /app/tools/
COPY config/ /app/config/
COPY prompts/ /app/prompts/
COPY requirements.txt /app/requirements.txt
COPY pyproject.toml /app/pyproject.toml
# Note: projects/ directory is mounted via EFS, not copied to image

# Install nexus_utils as a package (matching local: uv pip install -e .)
RUN if [ -f /app/nexus_utils/setup.py ]; then \
      pip install --no-cache-dir -e /app/nexus_utils || \
      (cd /app && pip install --no-cache-dir -e ./nexus_utils) || \
      echo "Warning: nexus_utils installation failed, but continuing..."; \
    fi

# Install the entire project as editable package (matching local: uv pip install -e .)
# This ensures all modules (agents, tools, etc.) are available in the same way as local
RUN cd /app && \
    if [ -f pyproject.toml ]; then \
      pip install --no-cache-dir -e . || \
      echo "Warning: Project editable install failed, using PYTHONPATH fallback..."; \
    fi

# Set PYTHONPATH to include /app so Python can find all modules
# This matches the local environment where the project root is in PYTHONPATH
ENV PYTHONPATH=/app:/app/nexus_utils

# Create non-root user with UID/GID 1000 to match EFS permissions
# First create group with GID 1000, then create user with UID 1000
RUN groupadd --gid 1000 app \
    && useradd --create-home --shell /bin/bash --uid 1000 --gid 1000 app \
    && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]