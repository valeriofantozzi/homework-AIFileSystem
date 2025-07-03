# MCP Server Integration Guide

## Quick Start

1. **Build and run the MCP server:**

   ```bash
   # Build Docker image
   ./server/deploy.sh build

   # Run with Docker (recommended)
   docker run -d --name mcp-server-test -p 8000:8000 \
     -v "$(pwd)/workspace:/app/workspace" \
     -e PYTHONPATH=/app -e LOG_LEVEL=info \
     ai-filesystem-mcp:latest
   ```

2. **Verify server is running:**

   ```bash
   curl http://localhost:8000/health
   ```

3. **Run integration tests:**
   ```bash
   python tests/integration/test_mcp_integration.py
   ```

## Client Integration

### Claude Desktop

1. Copy configuration:

   ```bash
   cp server/config/claude_desktop_config.json ~/.claude/mcp-servers/ai-filesystem.json
   ```

2. Enable in Claude Desktop → Settings → Model Context Protocol

### Cursor IDE

1. The project includes `.cursor/settings.json` with MCP server configuration
2. Ask Cursor: "List the files in my workspace"

## Available Tools

The MCP server exposes 8 file system tools:

- `list_files()` - List all files (sorted by mtime)
- `read_file(filename)` - Read file content
- `write_file(filename, content, mode)` - Write/append to file
- `delete_file(filename)` - Delete file
- `list_directories()` - List directories
- `list_all()` - List files and directories
- `list_tree()` - Generate tree view
- `answer_question_about_files(query)` - Analyze files

## Test Commands

```bash
# Health check
curl http://localhost:8000/health

# Metrics
curl http://localhost:8000/metrics

# Diagnostics
curl http://localhost:8000/diagnostics

# MCP protocol test
curl -X POST http://localhost:8000/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": "test"}'
```

## Architecture Notes

- **High cohesion**: MCP server has single responsibility for file system tool exposure
- **Low coupling**: Depends only on workspace tool abstractions, not SecureAgent
- **Clean separation**: Presentation (FastAPI) → Application (MCP handlers) → Domain (file tools)
- **Security**: Runs as non-root user in Docker with workspace sandboxing

## Success Criteria ✅

- [x] MCP server responds correctly to JSON-RPC 2.0 requests
- [x] All 8 file system tools working via MCP protocol
- [x] Docker deployment with health monitoring
- [x] Integration tests passing for all operations
- [x] Client configurations ready for Claude Desktop and Cursor IDE

**Implementation Status**: Task 2 completed - Ready for production monitoring and security hardening.
