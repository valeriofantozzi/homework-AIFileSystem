# Multi-stage build for optimal image size and security
FROM python:3.12-slim AS builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy the complete application structure (needed for local dependencies)
COPY . .

# Install Poetry and dependencies with proper local package handling
RUN pip install poetry==1.8.4 && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-interaction

# Production stage
FROM python:3.12-slim AS production

# Create non-root user for security
RUN groupadd --gid 1000 mcp && \
    useradd --uid 1000 --gid mcp --shell /bin/bash --create-home mcp

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Set work directory
WORKDIR /app

# Copy application code with proper ownership
COPY --chown=mcp:mcp . .

# Create workspace directory with proper permissions
RUN mkdir -p /app/workspace && chown -R mcp:mcp /app/workspace

# Switch to non-root user
USER mcp

# Expose MCP server port
EXPOSE 8000

# Health check endpoint for container orchestration
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command with production settings
CMD ["uvicorn", "server.api_mcp.mcp_server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
