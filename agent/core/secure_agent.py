"""
SecureAgent implementation with ReAct reasoning pattern.

This module provides the core SecureAgent class that implements autonomous
reasoning using the ReAct (Reasoning-Action-Observation) pattern. The agent
can interact with file system tools while maintaining security constraints.
"""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "crud_tools" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "tools" / "workspace_fs" / "src"))

from config.model_config import ModelConfig
from crud_tools import create_file_tools, answer_question_about_files
from workspace_fs import Workspace

from .react_loop import ReActLoop


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
        Initialize the SecureAgent.
        
        Args:
            workspace_path: Path to the secure workspace directory
            model_config: Model configuration instance. If None, creates default.
            debug_mode: Enable detailed logging and reasoning exposure
            **fs_kwargs: Additional arguments for FileSystemTools
        """
        self.workspace_path = workspace_path
        self.debug_mode = debug_mode
        self.logger = structlog.get_logger(__name__)
        
        # Initialize model configuration
        self.model_config = model_config or ModelConfig()
        
        # Get model provider for agent role
        self.model_provider = self.model_config.get_model_for_role("agent")
        
        # Initialize workspace
        self.workspace = Workspace(workspace_path)
        
        # Create basic file system tools
        self.file_tools = create_file_tools(self.workspace, **fs_kwargs)
        
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
            
            self.logger.info(
                "Query processed successfully",
                conversation_id=conversation_id,
                tools_used=result.tools_used
            )
            
            return response
            
        except Exception as e:
            self.logger.error(
                "Error processing query",
                conversation_id=conversation_id,
                error=str(e)
            )
            
            return AgentResponse(
                conversation_id=conversation_id,
                response=f"I encountered an error: {str(e)}",
                tools_used=[],
                success=False,
                error_message=str(e)
            )
    
    def _add_advanced_file_operations(self) -> None:
        """Add advanced file operations for Task 4.3."""
        
        def read_newest_file() -> str:
            """Read the content of the most recently modified file."""
            try:
                files = self.file_tools["list_files"]()
                if not files:
                    return "No files found in workspace"
                
                # list_files returns a list of files sorted by modification time (newest first)
                if isinstance(files, list) and files:
                    newest_file = files[0]
                    content = self.file_tools["read_file"](newest_file)
                    return f"Content of newest file '{newest_file}':\n{content}"
                elif isinstance(files, str) and files.strip():
                    # Handle string format (fallback)
                    file_list = files.strip().split('\n')
                    if file_list and file_list[0]:
                        newest_file = file_list[0]
                        content = self.file_tools["read_file"](newest_file)
                        return f"Content of newest file '{newest_file}':\n{content}"
                    else:
                        return "No files found in workspace"
                else:
                    return "No files found in workspace"
            except Exception as e:
                return f"Error reading newest file: {str(e)}"
        
        def find_files_by_pattern(pattern: str) -> str:
            """Find files matching a pattern (simple substring match)."""
            try:
                files = self.file_tools["list_files"]()
                if not files:
                    return "No files found in workspace"
                
                # Handle both list and string formats
                if isinstance(files, list):
                    file_list = files
                elif isinstance(files, str) and files.strip():
                    file_list = files.strip().split('\n')
                else:
                    return "No files found in workspace"
                
                matching_files = [f for f in file_list if f and pattern.lower() in f.lower()]
                
                if matching_files:
                    return f"Files matching pattern '{pattern}':\n" + '\n'.join(matching_files)
                else:
                    return f"No files found matching pattern '{pattern}'"
            except Exception as e:
                return f"Error finding files by pattern: {str(e)}"
        
        def get_file_info(filename: str) -> str:
            """Get metadata information about a file."""
            try:
                import os
                file_path = os.path.join(self.workspace_path, filename)
                
                if not os.path.exists(file_path) or not os.path.isfile(file_path):
                    return f"File '{filename}' not found"
                
                # Get basic file metadata
                stat = os.stat(file_path)
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                # Try to get content preview
                try:
                    content = self.file_tools["read_file"](filename)
                    lines = len(content.split('\n'))
                    preview = content[:200] + "..." if len(content) > 200 else content
                except Exception:
                    lines = "unknown"
                    preview = "Cannot read content"
                
                return (f"File: {filename}\n"
                       f"Size: {size} bytes\n"
                       f"Modified: {modified}\n"
                       f"Lines: {lines}\n"
                       f"Preview:\n{preview}")
            except Exception as e:
                return f"Error getting file info for '{filename}': {str(e)}"
        
        # Add advanced operations to tools
        self.file_tools["read_newest_file"] = read_newest_file
        self.file_tools["find_files_by_pattern"] = find_files_by_pattern
        self.file_tools["get_file_info"] = get_file_info
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return [
            # Core CRUD operations
            "list_files", 
            "read_file", 
            "write_file", 
            "delete_file", 
            "answer_question_about_files",
            # Advanced operations (Task 4.3)
            "read_newest_file",
            "find_files_by_pattern", 
            "get_file_info"
        ]
    
    def get_workspace_info(self) -> Dict[str, Any]:
        """Get information about the current workspace."""
        return {
            "workspace_path": self.workspace_path,
            "available_tools": self.get_available_tools(),
            "model": f"{self.model_provider.provider_name}:{self.model_provider.model_name}",
            "debug_mode": self.debug_mode
        }
