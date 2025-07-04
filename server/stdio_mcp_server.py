#!/usr/bin/env python3
"""
Stdio MCP server wrapper for VSCode integration.

This module provides a stdin/stdout interface for MCP protocol communication,
bridging VSCode's expected interface with our existing HTTP-based server.
Follows Clean Architecture with single responsibility for protocol translation.
"""

import asyncio
import json
import sys
import logging
from typing import Any, Dict, List, Optional
import structlog

from server.api_mcp.models import (
    InitializeResponse,
    MCPError,
    MCPErrorCode,
    MCPResponse,
    ToolsListResponse,
    ToolDefinition,
)
from tools.workspace_fs.src.workspace_fs import Workspace
from tools.crud_tools.src.crud_tools import create_file_tools, answer_question_about_files

# Configure structured logging for stdio mode
logger = structlog.get_logger(__name__)


class StdioMCPServer:
    """
    Stdio-based MCP server for VSCode integration.
    
    Handles JSON-RPC communication over stdin/stdout while maintaining
    high cohesion (single responsibility: protocol translation) and 
    low coupling (depends on workspace abstractions, not concrete implementations).
    """
    
    def __init__(self, workspace_path: str):
        """Initialize with workspace dependency injection."""
        self.workspace = Workspace(workspace_path)
        self.file_tools = create_file_tools(self.workspace)
        
    def get_available_tools(self) -> List[ToolDefinition]:
        """Get available file system tools with proper abstractions."""
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
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute tool with proper error handling and abstraction."""
        try:
            if tool_name == "list_files":
                result = self.file_tools["list_files"]()
            elif tool_name == "read_file":
                result = self.file_tools["read_file"](arguments["filename"])
            elif tool_name == "write_file":
                mode = arguments.get("mode", "w")
                result = self.file_tools["write_file"](
                    arguments["filename"], 
                    arguments["content"], 
                    mode
                )
            elif tool_name == "delete_file":
                result = self.file_tools["delete_file"](arguments["filename"])
            elif tool_name == "list_directories":
                result = self.file_tools["list_directories"]()
            elif tool_name == "list_all":
                result = self.file_tools["list_all"]()
            elif tool_name == "list_tree":
                result = self.file_tools["tree"]()
            elif tool_name == "answer_question_about_files":
                # Special case for async tool - use await
                query = arguments.get("query", "")
                result = await answer_question_about_files(self.workspace, query)
            else:
                return {
                    "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
                    "isError": True
                }
            
            return {
                "content": [{"type": "text", "text": str(result)}],
                "isError": False
            }
            
        except Exception as e:
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle MCP request with proper protocol compliance.
        
        Single responsibility: translate JSON-RPC to internal tool calls.
        Low coupling: depends on tool abstractions, not implementations.
        """
        try:
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})
            
            # Handle MCP initialize - critical for VSCode handshake
            if method == "initialize":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": InitializeResponse().model_dump()
                }
            
            # Handle tools discovery
            elif method == "tools/list":
                tools = self.get_available_tools()
                return {
                    "jsonrpc": "2.0", 
                    "id": request_id,
                    "result": ToolsListResponse(tools=tools).model_dump()
                }
            
            # Handle tool execution
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                
                if not tool_name:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": MCPError(
                            code=MCPErrorCode.INVALID_PARAMS,
                            message="Missing tool name"
                        ).model_dump()
                    }
                
                result = await self.execute_tool(tool_name, arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id, 
                    "result": result
                }
            
            # Handle resources (not implemented yet)
            elif method == "resources/list":
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"resources": []}
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": MCPError(
                        code=MCPErrorCode.METHOD_NOT_FOUND,
                        message=f"Method '{method}' not found"
                    ).model_dump()
                }
                
        except Exception as e:
            logger.error("Request handling failed", error=str(e))
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR,
                    message=f"Internal error: {str(e)}"
                ).model_dump()
            }
    
    async def run(self):
        """
        Main event loop for stdio communication.
        
        High cohesion: focused solely on input/output protocol handling.
        Clean separation from business logic in workspace tools.
        """
        logger.info("Starting MCP stdio server", workspace=str(self.workspace.root))
        
        while True:
            try:
                # Read line from stdin (why: VSCode sends one JSON-RPC per line)
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                    
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    # Return parse error per JSON-RPC spec
                    error_response = {
                        "jsonrpc": "2.0", 
                        "id": None,
                        "error": MCPError(
                            code=MCPErrorCode.PARSE_ERROR,
                            message=f"Parse error: {str(e)}"
                        ).model_dump()
                    }
                    print(json.dumps(error_response), flush=True)
                    continue
                
                # Handle request and send response
                response = await self.handle_request(request)
                print(json.dumps(response), flush=True)
                
            except KeyboardInterrupt:
                logger.info("Shutting down MCP stdio server")
                break
            except Exception as e:
                logger.error("Unexpected error in main loop", error=str(e))
                

async def main():
    """Entry point with dependency injection for workspace path."""
    import os
    
    workspace_path = os.getenv("WORKSPACE_PATH", "/app/workspace")
    server = StdioMCPServer(workspace_path)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
