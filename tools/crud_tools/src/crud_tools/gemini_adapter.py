"""
Gemini CLI adapter for local LLM testing.

This module provides an adapter to use the locally installed Gemini CLI
as an LLM backend for testing the question answering functionality.
"""

import asyncio
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, List


class GeminiCLIAdapter:
    """
    Adapter to use Gemini CLI as an LLM backend.
    
    This adapter allows testing the question answering functionality
    using the locally installed Gemini CLI instead of remote APIs.
    """
    
    def __init__(self, model: str = "gemini-2.5-pro"):
        """
        Initialize the Gemini CLI adapter.
        
        Args:
            model: The Gemini model to use.
        """
        self.model = model
        self._check_availability()
    
    def _check_availability(self) -> None:
        """Check if Gemini CLI is available."""
        try:
            result = subprocess.run(
                ["which", "gemini"],
                capture_output=True,
                text=True,
                check=True
            )
            self.gemini_path = result.stdout.strip()
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Gemini CLI not found. Please install it first: "
                "https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/cli"
            )
    
    async def query(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: Optional[int] = None,
        use_stdin: bool = True
    ) -> str:
        """
        Query the Gemini CLI with a prompt.
        
        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt (will be prepended).
            max_tokens: Maximum tokens (not directly supported by CLI).
            use_stdin: Use stdin instead of temporary file (better for CLI).
            
        Returns:
            The response from Gemini.
        """
        # Combine system prompt with user prompt
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        if use_stdin:
            # Use stdin approach - more compatible with Gemini CLI
            cmd = ["gemini", "--model", self.model]
            
            # Run the command asynchronously with stdin
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=full_prompt.encode('utf-8'))
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                raise RuntimeError(f"Gemini CLI failed: {error_msg}")
            
            return stdout.decode('utf-8').strip()
        else:
            # Fallback to file approach
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
                tmp_file.write(full_prompt)
                tmp_path = tmp_file.name
            
            try:
                cmd = [
                    "gemini",
                    "--model", self.model,
                    "--prompt", f"@{tmp_path}"
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode != 0:
                    error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
                    raise RuntimeError(f"Gemini CLI failed: {error_msg}")
                
                return stdout.decode('utf-8').strip()
                
            finally:
                Path(tmp_path).unlink(missing_ok=True)
    
    async def analyze_files(
        self,
        file_contents: dict[str, str],
        query: str
    ) -> str:
        """
        Analyze file contents and answer a question using Gemini CLI.
        
        Args:
            file_contents: Dictionary mapping filenames to their contents.
            query: The question to answer.
            
        Returns:
            The analysis result from Gemini.
        """
        # Prepare context
        context = "File contents:\n\n"
        for filename, content in file_contents.items():
            context += f"=== {filename} ===\n{content}\n\n"
        
        # Construct prompt
        prompt = (
            f"{context}\nQuestion: {query}\n\n"
            "Please provide a helpful answer based on the file contents above."
        )
        
        system_prompt = (
            "You are a helpful assistant that analyzes file contents and "
            "answers questions about them. You will be given the contents "
            "of multiple files and a question. Provide a concise, accurate "
            "answer based on the file contents. If the files don't contain "
            "relevant information, say so clearly."
        )
        
        return await self.query(prompt, system_prompt)


def create_gemini_question_tool(workspace, **kwargs):
    """
    Create a question tool that uses Gemini CLI instead of pydantic-ai.
    
    This is useful for testing the LLM functionality locally without
    requiring API keys or remote services. Model selection is configurable
    through the centralized configuration system.
    
    Args:
        workspace: The workspace instance for secure operations.
        **kwargs: Additional arguments (gemini_model, max_files, role, etc.).
        
    Returns:
        Async function that can be used as a question tool.
    """
    from workspace_fs import FileSystemTools, WorkspaceError
    
    # Try to get model from configuration system
    role = kwargs.pop('role', 'file_analysis')
    gemini_model = kwargs.pop('gemini_model', None)
    
    if gemini_model is None:
        try:
            # Try to import and use the configuration system
            from config import get_model_for_role
            model_provider = get_model_for_role(role)
            
            # Check if it's a Gemini provider
            if model_provider.provider_name in ['gemini', 'local']:
                if model_provider.provider_name == 'local':
                    # Handle local gemini_cli configuration
                    gemini_model = model_provider.config.default_params.get('model', 'gemini-2.5-pro')
                else:
                    gemini_model = model_provider.model_name
            else:
                # Fallback for non-Gemini providers in CLI mode
                gemini_model = 'gemini-2.5-pro'
                
        except ImportError:
            # Configuration system not available, use default
            gemini_model = 'gemini-2.5-pro'
        except Exception:
            # Configuration failed, use default
            gemini_model = 'gemini-2.5-pro'
    
    max_files = kwargs.pop('max_files', 10)
    max_content_per_file = kwargs.pop('max_content_per_file', 2048)
    
    adapter = GeminiCLIAdapter(model=gemini_model)
    
    async def gemini_question_tool(query: str) -> str:
        """
        Answer questions about files using Gemini CLI.
        
        Args:
            query: The question to answer about the files.
            
        Returns:
            A synthesized answer based on file analysis.
        """
        try:
            # Create FileSystemTools
            fs_tools = FileSystemTools(workspace, **kwargs)
            
            # Get list of files
            files = fs_tools.list_files()
            
            if not files:
                return "No files found in the workspace to analyze."
            
            # Limit number of files to analyze
            files_to_analyze = files[:max_files]
            
            # Read file contents
            file_contents = {}
            for filename in files_to_analyze:
                try:
                    content = fs_tools.read_file(filename)
                    # Truncate content if too long
                    if len(content) > max_content_per_file:
                        content = content[:max_content_per_file] + "...[truncated]"
                    file_contents[filename] = content
                except Exception as e:
                    # Skip files that can't be read
                    file_contents[filename] = f"[Error reading file: {e}]"
            
            # Use Gemini CLI to analyze
            return await adapter.analyze_files(file_contents, query)
            
        except Exception as e:
            raise WorkspaceError(f"Failed to analyze files with Gemini CLI: {e}") from e
    
    return gemini_question_tool
