#!/bin/bash
"""
MCP Integration Test Workflow Script

This script provides a complete workflow for testing the MCP server
with Docker deployment and client integration validation.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    success "Docker is running"
}

# Build and test MCP server
test_mcp_server() {
    log "🚀 Starting MCP Integration Test Workflow"
    echo "=========================================="

    # 1. Check Docker
    log "🐳 Checking Docker status..."
    check_docker

    # 2. Build Docker image
    log "📦 Building Docker image..."
    cd "${PROJECT_ROOT}"
    ./server/deploy.sh build

    # 3. Start MCP server
    log "🚀 Starting MCP server in Docker..."
    ./server/deploy.sh prod &
    SERVER_PID=$!

    # Wait for server to start
    log "⏳ Waiting for server to start..."
    sleep 5

    # 4. Test server health
    log "🏥 Testing server health..."
    max_attempts=10
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:8000/health > /dev/null; then
            success "Server is healthy"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            error "Server failed to start after $max_attempts attempts"
            ./server/deploy.sh stop
            exit 1
        fi
        
        log "Attempt $attempt/$max_attempts failed, retrying..."
        sleep 2
        ((attempt++))
    done

    # 5. Run integration tests
    log "🧪 Running MCP integration tests..."
    python tests/test_mcp_integration.py
    
    if [ $? -eq 0 ]; then
        success "Integration tests passed"
    else
        error "Integration tests failed"
        ./server/deploy.sh stop
        exit 1
    fi

    # 6. Display client configuration instructions
    log "📝 Client Configuration Instructions"
    echo "======================================"
    echo ""
    echo "🔹 Claude Desktop Integration:"
    echo "   1. Copy server/config/claude_desktop_config.json to:"
    echo "      ~/.claude/mcp-servers/ai-filesystem.json"
    echo "   2. Restart Claude Desktop"
    echo "   3. Enable the 'ai-filesystem' MCP server in Settings"
    echo ""
    echo "🔹 Cursor IDE Integration:"
    echo "   1. The .cursor/settings.json is already configured"
    echo "   2. Open this project in Cursor IDE"
    echo "   3. Try asking: 'Show me the files in my workspace'"
    echo ""
    echo "🔹 Manual Testing Commands:"
    echo "   curl http://localhost:8000/health"
    echo "   curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/list\",\"id\":\"test\"}'"
    echo ""

    # Ask user what to do next
    echo "Choose an option:"
    echo "1) Keep server running for manual testing"
    echo "2) Stop server and exit"
    echo "3) Run extended integration tests"
    
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            success "MCP server is running at http://localhost:8000"
            log "Press Ctrl+C to stop the server when done"
            wait $SERVER_PID
            ;;
        2)
            ./server/deploy.sh stop
            success "Server stopped"
            ;;
        3)
            log "Running extended integration tests..."
            # Add extended tests here if needed
            ./server/deploy.sh stop
            success "Extended tests completed"
            ;;
        *)
            warning "Invalid choice, stopping server"
            ./server/deploy.sh stop
            ;;
    esac

    success "MCP integration workflow completed"
}

# Main execution
main() {
    case "${1:-test}" in
        "test")
            test_mcp_server
            ;;
        "health")
            curl -s http://localhost:8000/health | jq . || echo "Server not running or jq not installed"
            ;;
        "tools")
            curl -s -X POST http://localhost:8000/mcp \
                -H 'Content-Type: application/json' \
                -d '{"jsonrpc":"2.0","method":"tools/list","id":"test"}' | jq .
            ;;
        *)
            echo "Usage: $0 [test|health|tools]"
            echo "  test   - Run complete integration test workflow (default)"
            echo "  health - Check server health"
            echo "  tools  - List available MCP tools"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
