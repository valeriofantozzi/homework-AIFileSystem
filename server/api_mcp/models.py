"""
MCP protocol request and response models.

This module defines Pydantic models for MCP (Model Context Protocol) communication
following JSON-RPC 2.0 specification. These models ensure type safety and proper
validation for client-server communication.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MCPMethod(str, Enum):
    """Supported MCP methods for file system operations."""
    
    # Protocol initialization
    INITIALIZE = "initialize"
    
    # Tool discovery and execution
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # Resource operations
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"


class MCPErrorCode(int, Enum):
    """Standard JSON-RPC 2.0 error codes plus MCP-specific codes."""
    
    # JSON-RPC 2.0 standard errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific error codes
    TOOL_ERROR = -32000
    RESOURCE_ERROR = -32001
    SECURITY_ERROR = -32002
    TIMEOUT_ERROR = -32003


class MCPError(BaseModel):
    """JSON-RPC 2.0 error object."""
    
    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    data: Optional[Any] = Field(None, description="Additional error data")


class MCPRequest(BaseModel):
    """JSON-RPC 2.0 request object for MCP communication."""
    
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(None, description="Request identifier")
    method: str = Field(..., description="Method name to invoke")
    params: Optional[Dict[str, Any]] = Field(None, description="Method parameters")


class MCPResponse(BaseModel):
    """JSON-RPC 2.0 response object for MCP communication."""
    
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Optional[Union[str, int]] = Field(None, description="Request identifier")
    result: Optional[Any] = Field(None, description="Method result")
    error: Optional[MCPError] = Field(None, description="Error information")


class ToolDefinition(BaseModel):
    """Definition of an available tool."""
    
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="JSON schema for tool input")


class ToolsListResponse(BaseModel):
    """Response for tools/list method."""
    
    tools: List[ToolDefinition] = Field(..., description="Available tools")


class ToolCallRequest(BaseModel):
    """Parameters for tools/call method."""
    
    name: str = Field(..., description="Tool name to call")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")


class ToolResult(BaseModel):
    """Result of a tool execution."""
    
    content: List[Dict[str, Any]] = Field(..., description="Tool execution results")
    isError: bool = Field(False, description="Whether execution resulted in error")


class ResourceDefinition(BaseModel):
    """Definition of an available resource."""
    
    uri: str = Field(..., description="Resource URI")
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    mimeType: Optional[str] = Field(None, description="Resource MIME type")


class ResourcesListResponse(BaseModel):
    """Response for resources/list method."""
    
    resources: List[ResourceDefinition] = Field(..., description="Available resources")


class ResourceReadRequest(BaseModel):
    """Parameters for resources/read method."""
    
    uri: str = Field(..., description="Resource URI to read")


class ResourceContent(BaseModel):
    """Content of a resource."""
    
    uri: str = Field(..., description="Resource URI")
    mimeType: Optional[str] = Field(None, description="Content MIME type")
    text: Optional[str] = Field(None, description="Text content")
    blob: Optional[str] = Field(None, description="Base64 encoded binary content")


class ConversationContext(BaseModel):
    """Context for maintaining conversation state across requests."""
    
    conversation_id: Optional[str] = Field(None, description="Unique conversation identifier")
    workspace_path: Optional[str] = Field(None, description="Base workspace directory")
    last_activity: Optional[str] = Field(None, description="Timestamp of last activity")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class HealthStatus(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime: float = Field(..., description="Uptime in seconds")
    workspace_path: Optional[str] = Field(None, description="Current workspace path")


class MetricsResponse(BaseModel):
    """Metrics endpoint response model."""
    
    total_requests: int = Field(..., description="Total number of requests processed")
    tool_calls: Dict[str, int] = Field(..., description="Tool usage statistics")
    error_count: int = Field(..., description="Total number of errors")
    average_response_time: float = Field(..., description="Average response time in seconds")
    uptime: float = Field(..., description="Uptime in seconds")


class InitializeResponse(BaseModel):
    """MCP initialize method response model."""
    
    protocolVersion: str = Field("2024-11-05", description="MCP protocol version")
    capabilities: Dict[str, Any] = Field(
        default_factory=lambda: {
            "tools": {},
            "resources": {}
        }, 
        description="Server capabilities"
    )
    serverInfo: Dict[str, str] = Field(
        default_factory=lambda: {
            "name": "AI FileSystem MCP Server",
            "version": "1.0.0"
        },
        description="Server information"
    )


class DiagnosticsResponse(BaseModel):
    """Diagnostics endpoint response model."""
    
    system_info: Dict[str, Any] = Field(..., description="System information")
    agent_status: Dict[str, Any] = Field(..., description="Agent status and configuration")
    workspace_info: Dict[str, Any] = Field(..., description="Workspace information")
    recent_errors: List[Dict[str, Any]] = Field(..., description="Recent error events")
    performance_metrics: Dict[str, Any] = Field(..., description="Performance metrics")
