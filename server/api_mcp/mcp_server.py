"""
FastAPI MCP server implementation.

This module provides a Model Context Protocol (MCP) compliant server using FastAPI.
The server exposes file system tools through MCP endpoints while maintaining
security constraints and proper error handling.
"""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agent.diagnostics import start_operation, end_operation, get_usage_statistics
from tools.workspace_fs.src.workspace_fs import Workspace
from tools.crud_tools.src.crud_tools import create_file_tools, answer_question_about_files

from .models import (
    ConversationContext,
    DiagnosticsResponse,
    HealthStatus,
    MCPError,
    MCPErrorCode,
    MCPRequest,
    MCPResponse,
    MetricsResponse,
    ResourceContent,
    ResourceDefinition,
    ResourceReadRequest,
    ResourcesListResponse,
    ToolCallRequest,
    ToolDefinition,
    ToolResult,
    ToolsListResponse,
)

# Configure structured logging
logger = structlog.get_logger(__name__)

# Global server metrics
SERVER_METRICS = {
    "start_time": time.time(),
    "total_requests": 0,
    "tool_calls": {},
    "error_count": 0,
    "response_times": [],
}

# Active conversation contexts
CONVERSATION_CONTEXTS: Dict[str, ConversationContext] = {}


class MCPServer:
    """
    MCP server implementation with direct file system tool integration.
    
    This server provides a clean MCP interface for file system operations
    without depending on the agent architecture. It directly uses workspace
    tools for maximum performance and simplicity.
    """
    
    def __init__(self, workspace_path: str):
        """
        Initialize MCP server with workspace constraints.
        
        Args:
            workspace_path: Base directory for all file operations
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.workspace = Workspace(str(self.workspace_path))
        self.file_tools = create_file_tools(self.workspace)
        
        logger.info(
            "Initializing MCP server",
            workspace_path=str(self.workspace_path)
        )
    
    async def initialize(self) -> None:
        """Initialize the MCP server components."""
        try:
            # Ensure workspace directory exists
            self.workspace_path.mkdir(parents=True, exist_ok=True)
            logger.info("MCP server initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize MCP server", error=str(e))
            raise
    
    def get_available_tools(self) -> List[ToolDefinition]:
        """
        Get list of available file system tools.
        
        Returns:
            List of tool definitions with schemas
        """
        return [
            ToolDefinition(
                name="list_files",
                description="List all files in the workspace directory (sorted by modification time)",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="read_file",
                description="Read content from a specific file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to read"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            ToolDefinition(
                name="write_file",
                description="Write or append content to a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to write"
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write to the file"
                        },
                        "mode": {
                            "type": "string",
                            "enum": ["w", "a"],
                            "default": "w",
                            "description": "Write mode: 'w' for overwrite, 'a' for append"
                        }
                    },
                    "required": ["filename", "content"]
                }
            ),
            ToolDefinition(
                name="delete_file",
                description="Delete a file from the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the file to delete"
                        }
                    },
                    "required": ["filename"]
                }
            ),
            ToolDefinition(
                name="list_directories",
                description="List all directories in the workspace",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="list_all",
                description="List all files and directories (directories marked with '/')",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="list_tree",
                description="Generate a tree view of the workspace structure",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            ),
            ToolDefinition(
                name="answer_question_about_files",
                description="Analyze files to answer questions about their content",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Question about the files in the workspace"
                        }
                    },
                    "required": ["query"]
                }
            ),
        ]
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """
        Execute a file system tool with the given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        operation_id = start_operation("tool_execution", {"tool": tool_name})
        
        try:
            # Update metrics
            SERVER_METRICS["tool_calls"][tool_name] = (
                SERVER_METRICS["tool_calls"].get(tool_name, 0) + 1
            )
            
            # Execute tool directly from file_tools
            if tool_name == "answer_question_about_files":
                # Special case for the async question answering tool
                query = arguments.get("query", "")
                result = await answer_question_about_files(self.workspace, query)
            elif tool_name in self.file_tools:
                # Execute synchronous file system tools
                tool_func = self.file_tools[tool_name]
                result = tool_func(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
            
            end_operation(operation_id, {"success": True})
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": str(result)
                }],
                isError=False
            )
            
        except Exception as e:
            end_operation(operation_id, {"success": False, "error": str(e)})
            SERVER_METRICS["error_count"] += 1
            
            logger.error(
                "Tool execution failed",
                tool_name=tool_name,
                arguments=arguments,
                error=str(e)
            )
            
            return ToolResult(
                content=[{
                    "type": "text",
                    "text": f"Error executing {tool_name}: {str(e)}"
                }],
                isError=True
            )


# Global server instance
mcp_server: Optional[MCPServer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    global mcp_server
    
    # Startup
    workspace_path = Path.cwd() / "workspace"  # Default workspace
    workspace_path.mkdir(exist_ok=True)
    
    mcp_server = MCPServer(str(workspace_path))
    await mcp_server.initialize()
    
    logger.info("MCP server started", workspace_path=str(workspace_path))
    
    yield
    
    # Shutdown
    logger.info("MCP server shutting down")


# Create FastAPI application
app = FastAPI(
    title="AI File System MCP Server",
    description="Model Context Protocol server for secure file system operations",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to track request metrics."""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Update metrics
    process_time = time.time() - start_time
    SERVER_METRICS["total_requests"] += 1
    SERVER_METRICS["response_times"].append(process_time)
    
    # Keep only last 1000 response times for average calculation
    if len(SERVER_METRICS["response_times"]) > 1000:
        SERVER_METRICS["response_times"] = SERVER_METRICS["response_times"][-1000:]
    
    # Add response time header
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


@app.post("/mcp", response_model=MCPResponse)
async def mcp_endpoint(request: MCPRequest) -> MCPResponse:
    """
    Main MCP endpoint for JSON-RPC 2.0 communication.
    
    This endpoint handles all MCP protocol requests including tool discovery
    and execution while maintaining security constraints.
    """
    if not mcp_server:
        return MCPResponse(
            id=request.id,
            error=MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message="Server not initialized"
            )
        )
    
    try:
        # Handle different MCP methods
        if request.method == "tools/list":
            tools = mcp_server.get_available_tools()
            return MCPResponse(
                id=request.id,
                result=ToolsListResponse(tools=tools).model_dump()
            )
        
        elif request.method == "tools/call":
            if not request.params:
                return MCPResponse(
                    id=request.id,
                    error=MCPError(
                        code=MCPErrorCode.INVALID_PARAMS,
                        message="Missing tool call parameters"
                    )
                )
            
            tool_request = ToolCallRequest(**request.params)
            result = await mcp_server.execute_tool(
                tool_request.name,
                tool_request.arguments
            )
            
            return MCPResponse(
                id=request.id,
                result=result.model_dump()
            )
        
        elif request.method == "resources/list":
            # Return empty resources list (not implemented in this phase)
            return MCPResponse(
                id=request.id,
                result=ResourcesListResponse(resources=[]).model_dump()
            )
        
        else:
            return MCPResponse(
                id=request.id,
                error=MCPError(
                    code=MCPErrorCode.METHOD_NOT_FOUND,
                    message=f"Method '{request.method}' not found"
                )
            )

    except Exception as e:
        logger.error("Unexpected error in MCP endpoint", error=str(e))
        return MCPResponse(
            id=request.id,
            error=MCPError(
                code=MCPErrorCode.INTERNAL_ERROR,
                message=f"Internal server error: {str(e)}"
            )
        )


@app.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Health check endpoint for service monitoring."""
    uptime = time.time() - SERVER_METRICS["start_time"]
    
    return HealthStatus(
        status="healthy" if mcp_server else "unhealthy",
        version="1.0.0",
        uptime=uptime,
        workspace_path=str(mcp_server.workspace_path) if mcp_server else None
    )


@app.get("/metrics", response_model=MetricsResponse)
async def metrics_endpoint() -> MetricsResponse:
    """Metrics endpoint for performance tracking."""
    response_times = SERVER_METRICS["response_times"]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
    
    return MetricsResponse(
        total_requests=SERVER_METRICS["total_requests"],
        tool_calls=SERVER_METRICS["tool_calls"],
        error_count=SERVER_METRICS["error_count"],
        average_response_time=avg_response_time,
        uptime=time.time() - SERVER_METRICS["start_time"]
    )


@app.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics_endpoint() -> DiagnosticsResponse:
    """Diagnostics endpoint for comprehensive system status."""
    try:
        system_metrics = get_usage_statistics()
        
        workspace_info = {}
        if mcp_server:
            try:
                workspace_info = {
                    "path": str(mcp_server.workspace_path),
                    "exists": mcp_server.workspace_path.exists(),
                    "is_directory": mcp_server.workspace_path.is_dir(),
                    "permissions": oct(mcp_server.workspace_path.stat().st_mode)[-3:] if mcp_server.workspace_path.exists() else None
                }
            except Exception as e:
                workspace_info = {"error": str(e)}
        
        server_status = {
            "initialized": mcp_server is not None,
            "workspace_tools_available": len(mcp_server.file_tools) if mcp_server else 0
        }
        
        return DiagnosticsResponse(
            system_info=system_metrics,
            agent_status=server_status,
            workspace_info=workspace_info,
            recent_errors=[],  # Would be populated from log analysis
            performance_metrics={
                "total_requests": SERVER_METRICS["total_requests"],
                "tool_calls": SERVER_METRICS["tool_calls"],
                "error_rate": SERVER_METRICS["error_count"] / max(SERVER_METRICS["total_requests"], 1),
                "uptime": time.time() - SERVER_METRICS["start_time"]
            }
        )
    
    except Exception as e:
        logger.error("Error generating diagnostics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate diagnostics: {str(e)}"
        )


def main():
    """Main entry point for the MCP server."""
    import uvicorn
    
    uvicorn.run(
        "server.api_mcp.mcp_server:app",
        host="127.0.0.1",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )


if __name__ == "__main__":
    main()
