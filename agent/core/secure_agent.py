"""
SecureAgent implementation with ReAct reasoning pattern.

This module provides the core SecureAgent class that implements autonomous
reasoning using the ReAct (Reasoning-Action-Observation) pattern. The agent
can interact with file system tools while maintaining security constraints.
"""

import json
import logging
import os
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from config import ModelConfig
from tools.workspace_fs.src.workspace_fs import Workspace
from tools.crud_tools.src.crud_tools import create_gemini_question_tool
from .exceptions import (
    AgentError, 
    AgentInitializationError, 
    ModelConfigurationError,
    ToolExecutionError, 
    ReasoningError, 
    SafetyViolationError,
    ConversationError,
    ErrorFormatter
)
# Import diagnostics for performance tracking and usage statistics
from agent.diagnostics import (
    start_operation,
    end_operation, 
    log_conversation_start,
    log_tool_usage,
    log_security_event
)


# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "crud_tools" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "workspace_fs" / "src"))

from config.model_config import ModelConfig
from crud_tools import create_file_tools, answer_question_about_files
from workspace_fs import Workspace

from .react_loop import ReActLoop


class ToolResultFormatter:
    """Enhanced formatting for tool results to improve readability and error handling."""
    
    @staticmethod
    def format_success_result(tool_name: str, result: Any, execution_time: float = None) -> str:
        """Format a successful tool execution result."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_info = f" ({execution_time:.2f}s)" if execution_time else ""
        
        if tool_name == "list_files":
            if isinstance(result, list):
                count = len(result)
                files_str = "\n".join(f"  - {file}" for file in result[:10])  # Show first 10
                if count > 10:
                    files_str += f"\n  ... and {count - 10} more files"
                return f"✅ Found {count} files{time_info}:\n{files_str}"
            else:
                return f"✅ Files{time_info}:\n{str(result)}"
        
        elif tool_name == "read_file":
            content_len = len(str(result))
            lines = len(str(result).split('\n'))
            return f"✅ Read file{time_info} ({content_len} chars, {lines} lines):\n{str(result)}"
        
        elif tool_name == "write_file":
            return f"✅ File operation completed{time_info}: {str(result)}"
        
        elif tool_name == "delete_file":
            return f"✅ File deleted{time_info}: {str(result)}"
        
        elif tool_name in ["get_file_info", "find_files_by_pattern", "read_newest_file"]:
            return f"✅ {tool_name.replace('_', ' ').title()}{time_info}:\n{str(result)}"
        
        else:
            return f"✅ {tool_name}{time_info}: {str(result)}"
    
    @staticmethod
    def format_error_result(tool_name: str, error: Exception, execution_time: float = None) -> str:
        """Format a tool execution error with enhanced context and recovery suggestions."""
        time_info = f" ({execution_time:.2f}s)" if execution_time else ""
        
        # If it's already an AgentError, use its formatting
        if isinstance(error, AgentError):
            return ErrorFormatter.format_error_for_user(error)
        
        # Create a ToolExecutionError for consistent formatting
        tool_error = ToolExecutionError(
            message=str(error),
            tool_name=tool_name,
            original_error=error
        )
        
        return ErrorFormatter.format_error_for_user(tool_error)
    
    @staticmethod
    def format_validation_error(tool_name: str, validation_message: str) -> str:
        """Format validation errors with clear guidance."""
        return (f"⚠️  {tool_name} validation failed:\n"
                f"{validation_message}\n"
                f"Please check the tool arguments and try again.")


class SandboxValidator:
    """Validates sandbox initialization and security constraints."""
    
    @staticmethod
    def validate_workspace(workspace_path: str) -> Dict[str, Any]:
        """Validate workspace directory and return status information."""
        result = {
            "valid": False,
            "path": workspace_path,
            "exists": False,
            "readable": False,
            "writable": False,
            "file_count": 0,
            "total_size": 0,
            "errors": []
        }
        
        try:
            path = Path(workspace_path)
            
            # Check if path exists
            if not path.exists():
                result["errors"].append(f"Workspace path does not exist: {workspace_path}")
                return result
            result["exists"] = True
            
            # Check if it's a directory
            if not path.is_dir():
                result["errors"].append(f"Workspace path is not a directory: {workspace_path}")
                return result
            
            # Check read permissions
            try:
                list(path.iterdir())
                result["readable"] = True
            except PermissionError:
                result["errors"].append("Cannot read workspace directory")
            
            # Check write permissions
            try:
                test_file = path / ".test_write_access"
                test_file.touch()
                test_file.unlink()
                result["writable"] = True
            except PermissionError:
                result["errors"].append("Cannot write to workspace directory")
            
            # Count files and calculate size
            try:
                files = list(path.glob("*"))
                result["file_count"] = len([f for f in files if f.is_file()])
                result["total_size"] = sum(f.stat().st_size for f in files if f.is_file())
            except Exception as e:
                result["errors"].append(f"Error analyzing workspace contents: {str(e)}")
            
            # Mark as valid if no critical errors
            result["valid"] = result["exists"] and result["readable"] and result["writable"]
            
        except Exception as e:
            result["errors"].append(f"Unexpected error validating workspace: {str(e)}")
        
        return result


class ConversationContext(BaseModel):
    """Context information for a conversation session."""
    
    conversation_id: str
    user_query: str
    workspace_path: str
    timestamp: datetime
    debug_mode: bool = False


class AgentResponse(BaseModel):
    """Structured response from the agent."""
    
    conversation_id: str
    response: str
    tools_used: List[str]
    reasoning_steps: Optional[List[Dict[str, Any]]] = None
    success: bool = True
    error_message: Optional[str] = None


class SecureAgent:
    """
    Secure AI agent with ReAct reasoning for file system operations.
    
    This agent provides autonomous reasoning capabilities while maintaining
    strict security boundaries. It uses the ReAct pattern to think through
    problems, take actions with tools, and observe results.
    
    Key features:
    - Tool-based architecture with pluggable capabilities
    - Sandboxed file system operations
    - Structured logging and conversation tracking
    - Model configuration via centralized config system
    """
    
    def __init__(
        self,
        workspace_path: str,
        model_config: Optional[ModelConfig] = None,
        debug_mode: bool = False,
        **fs_kwargs: Any
    ) -> None:
        """
        Initialize the SecureAgent with enhanced validation and formatting.
        
        Args:
            workspace_path: Path to the secure workspace directory
            model_config: Model configuration instance. If None, creates default.
            debug_mode: Enable detailed logging and reasoning exposure
            **fs_kwargs: Additional arguments for FileSystemTools
        """
        self.workspace_path = workspace_path
        self.debug_mode = debug_mode
        self.logger = structlog.get_logger(__name__)
        
        # Enhanced sandbox validation (Task 4.1)
        self.sandbox_status = SandboxValidator.validate_workspace(workspace_path)
        if not self.sandbox_status["valid"]:
            error_msg = f"Sandbox validation failed: {'; '.join(self.sandbox_status['errors'])}"
            self.logger.error("Sandbox validation failed", errors=self.sandbox_status["errors"])
            raise ValueError(error_msg)
        
        self.logger.info(
            "Sandbox validated successfully",
            file_count=self.sandbox_status["file_count"],
            total_size=self.sandbox_status["total_size"]
        )
        
        # Initialize model configuration
        self.model_config = model_config or ModelConfig()
        
        # Get model provider for agent role
        self.model_provider = self.model_config.get_model_for_role("agent")
        
        # Initialize workspace
        self.workspace = Workspace(workspace_path)
        
        # Create basic file system tools with enhanced error handling
        self.file_tools = self._create_enhanced_file_tools(**fs_kwargs)
        
        # Add the intelligent question answering tool
        async def answer_question_tool(query: str) -> str:
            """Answer questions about files in the workspace using LLM analysis."""
            return await answer_question_about_files(self.workspace, query)
        
        self.file_tools["answer_question_about_files"] = answer_question_tool
        
        # Add advanced file operations (Task 4.3)
        self._add_advanced_file_operations()
        
        # Initialize ReAct loop
        self.react_loop = ReActLoop(
            model_provider=self.model_provider,
            tools=self.file_tools,
            logger=self.logger,
            debug_mode=debug_mode,
            llm_response_func=self._get_llm_response
        )
        
        # Initialize Pydantic-AI agent
        self._init_pydantic_agent()
        
        self.logger.info(
            "SecureAgent initialized",
            workspace_path=workspace_path,
            model=f"{self.model_provider.provider_name}:{self.model_provider.model_name}",
            debug_mode=debug_mode
        )
    
    def _init_pydantic_agent(self) -> None:
        """Initialize the Pydantic-AI agent with tools and configuration."""
        # For now, we'll use a simpler approach without complex tool registration
        # The ReAct loop will handle tool execution directly
        
        # Create agent with model configuration
        client_params = self.model_provider.get_client_params()
        
        # Remove model from client_params since we pass it explicitly
        model_name = client_params.pop("model", self.model_provider.model_name)
        
        # Create a basic agent for LLM interactions
        # We'll handle tool calling through the ReAct loop instead
        self.agent = Agent(
            model=f"{self.model_provider.provider_name}:{model_name}",
            system_prompt=self._get_system_prompt()
        )
    
    def _get_llm_response(self, prompt: str) -> str:
        """Get a response from the LLM without tool calling."""
        try:
            # Use the agent for text generation
            import asyncio
            
            async def get_response():
                result = await self.agent.run(prompt)
                return result.data
            
            # Run the async function
            return asyncio.run(get_response())
            
        except Exception as e:
            self.logger.error("LLM response failed", error=str(e))
            return f"Error getting LLM response: {str(e)}"
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent."""
        return """You are a secure AI assistant specialized in file system operations.

You have access to the following tools:

CORE FILE OPERATIONS:
- list_files(): List all files in the workspace (sorted by modification time, newest first)
- read_file(filename): Read content from a file
- write_file(filename, content, mode): Write content to a file
- delete_file(filename): Delete a file
- answer_question_about_files(query): Answer questions about file contents using AI analysis

ADVANCED OPERATIONS:
- read_newest_file(): Read the most recently modified file
- find_files_by_pattern(pattern): Find files matching a pattern (substring search)
- get_file_info(filename): Get detailed metadata about a file

IMPORTANT CONSTRAINTS:
1. You can ONLY operate on files within your assigned workspace
2. You cannot access files outside the workspace or use path traversal
3. All filenames must be simple names without path separators
4. Be helpful but always respect security boundaries

When solving problems:
1. THINK through what you need to do step by step
2. ACT by calling the appropriate tools
3. OBSERVE the results and continue reasoning
4. Provide clear, helpful responses to the user

Always explain your reasoning and what tools you're using."""
    
    async def process_query(self, user_query: str) -> AgentResponse:
        """
        Process a user query using ReAct reasoning.
        
        Args:
            user_query: The user's question or request
            
        Returns:
            AgentResponse with the result and metadata
        """
        conversation_id = str(uuid.uuid4())
        context = ConversationContext(
            conversation_id=conversation_id,
            user_query=user_query,
            workspace_path=self.workspace_path,
            timestamp=datetime.now(),
            debug_mode=self.debug_mode
        )
        
        # Start diagnostics tracking for this operation
        operation_id = start_operation("process_query", {
            "conversation_id": conversation_id,
            "query_length": len(user_query),
            "workspace_path": str(self.workspace_path)
        })
        
        # Log conversation start for usage statistics
        log_conversation_start(conversation_id, user_query)
        
        self.logger.info(
            "Processing user query",
            conversation_id=conversation_id,
            query=user_query
        )
        
        try:
            # Use ReAct loop for reasoning
            result = await self.react_loop.execute(user_query, context)
            
            response = AgentResponse(
                conversation_id=conversation_id,
                response=result.response,
                tools_used=result.tools_used,
                reasoning_steps=result.reasoning_steps if self.debug_mode else None,
                success=True
            )
            
            # End operation tracking with success
            end_operation(
                operation_id, 
                success=True, 
                result_summary=f"Query processed successfully, {len(result.tools_used)} tools used"
            )
            
            self.logger.info(
                "Query processed successfully",
                conversation_id=conversation_id,
                tools_used=result.tools_used
            )
            
            return response
            
        except AgentError as e:
            # Agent-specific errors with enhanced formatting
            self.logger.error(
                "Agent error processing query",
                conversation_id=conversation_id,
                error_code=e.error_code,
                error_type=type(e).__name__,
                context=e.context
            )
            
            # End operation tracking with failure
            end_operation(
                operation_id, 
                success=False, 
                error_message=f"{type(e).__name__}: {e.message}"
            )
            
            error_message = ErrorFormatter.format_error_for_user(e)
            if self.debug_mode:
                error_message = ErrorFormatter.format_error_for_debug(e)
            
            return AgentResponse(
                conversation_id=conversation_id,
                response=error_message,
                tools_used=[],
                success=False,
                error_message=e.message
            )
            
        except Exception as e:
            # Unexpected errors - wrap in generic AgentError
            self.logger.error(
                "Unexpected error processing query",
                conversation_id=conversation_id,
                error=str(e),
                error_type=type(e).__name__
            )
            
            # End operation tracking with failure
            end_operation(
                operation_id, 
                success=False, 
                error_message=f"Unexpected error: {type(e).__name__}: {str(e)}"
            )
            
            # Create a generic agent error for consistent handling
            agent_error = ReasoningError(
                message=f"An unexpected error occurred during processing: {str(e)}",
                reasoning_step="query_processing"
            )
            agent_error.context["original_error"] = str(e)
            agent_error.context["original_error_type"] = type(e).__name__
            
            error_message = ErrorFormatter.format_error_for_user(agent_error)
            if self.debug_mode:
                error_message = ErrorFormatter.format_error_for_debug(agent_error)
            
            return AgentResponse(
                conversation_id=conversation_id,
                response=error_message,
                tools_used=[],
                success=False,
                error_message=str(e)
            )
    
    def _add_advanced_file_operations(self) -> None:
        """Add advanced file operations for Task 4.3 with enhanced capabilities."""
        import time
        
        def read_newest_file() -> str:
            """Read the content of the most recently modified file."""
            start_time = time.time()
            try:
                # Get raw tools instead of enhanced ones to avoid formatting conflicts
                raw_tools = create_file_tools(self.workspace)
                files = raw_tools["list_files"]()
                
                if not files:
                    return "No files found in workspace"
                
                # list_files returns a list of files sorted by modification time (newest first)
                if isinstance(files, list) and files:
                    newest_file = files[0]
                    content = raw_tools["read_file"](newest_file)
                    execution_time = time.time() - start_time
                    return ToolResultFormatter.format_success_result(
                        "read_newest_file", 
                        f"Content of newest file '{newest_file}':\n{content}",
                        execution_time
                    )
                elif isinstance(files, str) and files.strip():
                    # Handle string format (fallback)
                    file_list = files.strip().split('\n')
                    if file_list and file_list[0]:
                        newest_file = file_list[0]
                        content = raw_tools["read_file"](newest_file)
                        execution_time = time.time() - start_time
                        return ToolResultFormatter.format_success_result(
                            "read_newest_file",
                            f"Content of newest file '{newest_file}':\n{content}",
                            execution_time
                        )
                    else:
                        return "No files found in workspace"
                else:
                    return "No files found in workspace"
            except Exception as e:
                execution_time = time.time() - start_time
                return ToolResultFormatter.format_error_result("read_newest_file", e, execution_time)
        
        def find_files_by_pattern(pattern: str, use_regex: bool = False) -> str:
            """Find files matching a pattern with optional regex support."""
            start_time = time.time()
            try:
                # Get raw tools to avoid formatting conflicts
                raw_tools = create_file_tools(self.workspace)
                files = raw_tools["list_files"]()
                
                if not files:
                    return "No files found in workspace"
                
                # Handle both list and string formats
                if isinstance(files, list):
                    file_list = files
                elif isinstance(files, str) and files.strip():
                    file_list = files.strip().split('\n')
                else:
                    return "No files found in workspace"
                
                matching_files = []
                
                if use_regex:
                    try:
                        regex_pattern = re.compile(pattern, re.IGNORECASE)
                        matching_files = [f for f in file_list if f and regex_pattern.search(f)]
                    except re.error as regex_err:
                        return ToolResultFormatter.format_validation_error(
                            "find_files_by_pattern",
                            f"Invalid regex pattern '{pattern}': {str(regex_err)}"
                        )
                else:
                    # Simple substring match
                    matching_files = [f for f in file_list if f and pattern.lower() in f.lower()]
                
                execution_time = time.time() - start_time
                
                if matching_files:
                    result = f"Files matching pattern '{pattern}':\n" + '\n'.join(f"  - {f}" for f in matching_files)
                    return ToolResultFormatter.format_success_result(
                        "find_files_by_pattern", result, execution_time
                    )
                else:
                    return f"No files found matching pattern '{pattern}'"
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return ToolResultFormatter.format_error_result("find_files_by_pattern", e, execution_time)
        
        def get_file_info(filename: str) -> str:
            """Get comprehensive metadata information about a file."""
            start_time = time.time()
            try:
                import os
                file_path = os.path.join(self.workspace_path, filename)
                
                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                    return f"File '{filename}' not found"
                
                # Get comprehensive file metadata
                stat = os.stat(file_path)
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get content preview using raw tools
                try:
                    raw_tools = create_file_tools(self.workspace)
                    content = raw_tools["read_file"](filename)
                    lines = len(content.split('\n'))
                    words = len(content.split())
                    preview = content[:300] + "..." if len(content) > 300 else content
                except Exception:
                    lines = "unknown"
                    words = "unknown"
                    preview = "Cannot read content"
                
                # Get file extension info
                file_ext = Path(filename).suffix.lower()
                file_type = {
                    '.txt': 'Text file',
                    '.md': 'Markdown file',
                    '.py': 'Python script',
                    '.json': 'JSON data',
                    '.csv': 'CSV data',
                    '.log': 'Log file'
                }.get(file_ext, f'{file_ext} file' if file_ext else 'File without extension')
                
                execution_time = time.time() - start_time
                
                result = (f"File: {filename}\n"
                         f"Type: {file_type}\n"
                         f"Size: {size:,} bytes\n"
                         f"Created: {created}\n"
                         f"Modified: {modified}\n"
                         f"Lines: {lines}\n"
                         f"Words: {words}\n"
                         f"Preview:\n{preview}")
                
                return ToolResultFormatter.format_success_result("get_file_info", result, execution_time)
                
            except Exception as e:
                execution_time = time.time() - start_time
                return ToolResultFormatter.format_error_result("get_file_info", e, execution_time)
        
        def find_largest_file() -> str:
            """Find the largest file in the workspace."""
            start_time = time.time()
            try:
                # Get raw tools to avoid formatting conflicts
                raw_tools = create_file_tools(self.workspace)
                files = raw_tools["list_files"]()
                
                if not files:
                    return "No files found in workspace"
                
                file_list = files if isinstance(files, list) else files.strip().split('\n')
                largest_file = None
                largest_size = 0
                
                for filename in file_list:
                    if filename:
                        try:
                            file_path = os.path.join(self.workspace_path, filename)
                            size = os.path.getsize(file_path)
                            if size > largest_size:
                                largest_size = size
                                largest_file = filename
                        except Exception:
                            continue
                
                execution_time = time.time() - start_time
                
                if largest_file:
                    result = f"Largest file: {largest_file} ({largest_size:,} bytes)"
                    return ToolResultFormatter.format_success_result("find_largest_file", result, execution_time)
                else:
                    return "No accessible files found"
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return ToolResultFormatter.format_error_result("find_largest_file", e, execution_time)
        
        def find_files_by_extension(extension: str) -> str:
            """Find all files with a specific extension."""
            start_time = time.time()
            try:
                # Get raw tools to avoid formatting conflicts
                raw_tools = create_file_tools(self.workspace)
                files = raw_tools["list_files"]()
                
                if not files:
                    return "No files found in workspace"
                
                file_list = files if isinstance(files, list) else files.strip().split('\n')
                ext = extension.lower() if not extension.startswith('.') else extension.lower()
                if not ext.startswith('.'):
                    ext = '.' + ext
                
                matching_files = [f for f in file_list if f and f.lower().endswith(ext)]
                
                execution_time = time.time() - start_time
                
                if matching_files:
                    result = f"Files with extension '{ext}':\n" + '\n'.join(f"  - {f}" for f in matching_files)
                    return ToolResultFormatter.format_success_result("find_files_by_extension", result, execution_time)
                else:
                    return f"No files found with extension '{ext}'"
                    
            except Exception as e:
                execution_time = time.time() - start_time
                return ToolResultFormatter.format_error_result("find_files_by_extension", e, execution_time)
        
        # Add all advanced operations to tools
        self.file_tools["read_newest_file"] = read_newest_file
        self.file_tools["find_files_by_pattern"] = find_files_by_pattern
        self.file_tools["get_file_info"] = get_file_info
        self.file_tools["find_largest_file"] = find_largest_file
        self.file_tools["find_files_by_extension"] = find_files_by_extension
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [
            # Core CRUD operations (Task 4.1)
            "list_files", 
            "read_file", 
            "write_file", 
            "delete_file", 
            "answer_question_about_files",
            # Advanced operations (Task 4.3)
            "read_newest_file",
            "find_files_by_pattern", 
            "get_file_info",
            "find_largest_file",
            "find_files_by_extension"
        ]
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the current workspace."""
        return {
            "workspace_path": self.workspace_path,
            "available_tools": self.get_available_tools(),
            "model": f"{self.model_provider.provider_name}:{self.model_provider.model_name}",
            "debug_mode": self.debug_mode
        }
    
    def _create_enhanced_file_tools(self, **fs_kwargs: Any) -> Dict[str, Any]:
        """Create file system tools with enhanced error handling and formatting."""
        import time
        
        # Get basic tools
        basic_tools = create_file_tools(self.workspace, **fs_kwargs)
        enhanced_tools = {}
        
        # Wrap each tool with enhanced error handling and formatting
        for tool_name, tool_func in basic_tools.items():
            def create_enhanced_wrapper(name: str, func: callable):
                def enhanced_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        # Execute the original tool function
                        result = func(*args, **kwargs)
                        execution_time = time.time() - start_time
                        
                        # Format successful result
                        formatted_result = ToolResultFormatter.format_success_result(
                            name, result, execution_time
                        )
                        
                        if self.debug_mode:
                            self.logger.debug(
                                "Tool executed successfully",
                                tool=name,
                                args=args,
                                kwargs=kwargs,
                                execution_time=execution_time
                            )
                        
                        return formatted_result
                        
                    except Exception as e:
                        execution_time = time.time() - start_time
                        
                        # Format error result
                        formatted_error = ToolResultFormatter.format_error_result(
                            name, e, execution_time
                        )
                        
                        self.logger.error(
                            "Tool execution failed",
                            tool=name,
                            args=args,
                            kwargs=kwargs,
                            error=str(e),
                            execution_time=execution_time
                        )
                        
                        return formatted_error
                
                return enhanced_wrapper
            
            enhanced_tools[tool_name] = create_enhanced_wrapper(tool_name, tool_func)
        
        return enhanced_tools
