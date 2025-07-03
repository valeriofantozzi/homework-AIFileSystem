#!/bin/bash
# Build and deployment script for AI File System MCP Server
#
# This script provides commands for building, testing, and deploying
# the MCP server in both development and production environments.

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DOCKER_DIR="${PROJECT_ROOT}/server/docker"
IMAGE_NAME="ai-filesystem-mcp"
CONTAINER_NAME="ai-filesystem-mcp-server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Build Docker image
build() {
    log "Building Docker image: ${IMAGE_NAME}"
    
    cd "${PROJECT_ROOT}"
    docker build -f server/docker/Dockerfile -t "${IMAGE_NAME}:latest" .
    
    success "Docker image built successfully"
}

# Run development server
dev() {
    log "Starting development server"
    
    cd "${PROJECT_ROOT}"
    export PYTHONPATH="${PROJECT_ROOT}"
    python server/deployment/start_server.py
}

# Run production server with Docker
prod() {
    log "Starting production server with Docker"
    
    cd "${DOCKER_DIR}"
    docker-compose up -d
    
    success "Production server started"
    log "Server running at: http://localhost:8000"
    log "Health check: http://localhost:8000/health"
}

# Stop production server
stop() {
    log "Stopping production server"
    
    cd "${DOCKER_DIR}"
    docker-compose down
    
    success "Production server stopped"
}

# Health check
health() {
    log "Performing health check"
    
    cd "${PROJECT_ROOT}"
    python server/deployment/health_check.py comprehensive
}

# Run tests
test() {
    log "Running MCP server tests"
    
    cd "${PROJECT_ROOT}"
    python dev/testing/test_mcp_server.py
    
    if command -v python -c "import httpx" &> /dev/null; then
        python dev/testing/test_mcp_http.py
    else
        warning "httpx not installed, skipping HTTP tests"
    fi
}

# Clean up Docker resources
clean() {
    log "Cleaning up Docker resources"
    
    # Stop and remove containers
    docker stop "${CONTAINER_NAME}" 2>/dev/null || true
    docker rm "${CONTAINER_NAME}" 2>/dev/null || true
    
    # Remove images
    docker rmi "${IMAGE_NAME}:latest" 2>/dev/null || true
    
    # Clean up volumes
    cd "${DOCKER_DIR}"
    docker-compose down -v 2>/dev/null || true
    
    success "Cleanup completed"
}

# Show logs
logs() {
    cd "${DOCKER_DIR}"
    docker-compose logs -f
}

# Show usage
usage() {
    echo "Usage: $0 {build|dev|prod|stop|health|test|clean|logs}"
    echo ""
    echo "Commands:"
    echo "  build   Build Docker image"
    echo "  dev     Run development server (local)"
    echo "  prod    Run production server (Docker)"
    echo "  stop    Stop production server"
    echo "  health  Perform health check"
    echo "  test    Run tests"
    echo "  clean   Clean up Docker resources"
    echo "  logs    Show server logs"
}

# Main command dispatcher
case "${1:-}" in
    build)
        build
        ;;
    dev)
        dev
        ;;
    prod)
        build
        prod
        ;;
    stop)
        stop
        ;;
    health)
        health
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    logs)
        logs
        ;;
    *)
        usage
        exit 1
        ;;
esac
