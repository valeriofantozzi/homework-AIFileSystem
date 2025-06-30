"""
Test cases for the Gemini CLI adapter.

This module tests the integration between the CRUD tools and Gemini CLI
for local LLM testing without requiring API keys.
"""

import asyncio
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock

from workspace_fs import Workspace
from crud_tools.gemini_adapter import GeminiCLIAdapter, create_gemini_question_tool


class TestGeminiCLIAdapter:
    """Test cases for the GeminiCLIAdapter class."""

    def test_init_without_gemini_cli(self):
        """Test initialization when Gemini CLI is not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ['which', 'gemini'])
            
            with pytest.raises(RuntimeError, match="Gemini CLI not found"):
                GeminiCLIAdapter()

    def test_init_with_gemini_cli(self):
        """Test successful initialization when Gemini CLI is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.stdout = '/usr/local/bin/gemini\n'
            
            adapter = GeminiCLIAdapter(model="gemini-1.5-pro")
            assert adapter.model == "gemini-1.5-pro"
            assert adapter.gemini_path == '/usr/local/bin/gemini'

    @pytest.mark.asyncio
    async def test_query_success(self):
        """Test successful query execution."""
        with patch('subprocess.run') as mock_which:
            mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
            
            adapter = GeminiCLIAdapter()
            
            # Mock the asyncio subprocess
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b'This is the response', b'')
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                result = await adapter.query("What is AI?", "You are helpful")
                
                assert result == "This is the response"
                mock_subprocess.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_failure(self):
        """Test query execution with error."""
        with patch('subprocess.run') as mock_which:
            mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
            
            adapter = GeminiCLIAdapter()
            
            # Mock the asyncio subprocess with error
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (b'', b'API error')
                mock_process.returncode = 1
                mock_subprocess.return_value = mock_process
                
                with pytest.raises(RuntimeError, match="Gemini CLI failed"):
                    await adapter.query("What is AI?")

    @pytest.mark.asyncio
    async def test_analyze_files(self):
        """Test file analysis functionality."""
        with patch('subprocess.run') as mock_which:
            mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
            
            adapter = GeminiCLIAdapter()
            
            # Mock the query method
            with patch.object(adapter, 'query') as mock_query:
                mock_query.return_value = "The files contain Python code for math operations."
                
                file_contents = {
                    "math.py": "def add(a, b): return a + b",
                    "test.py": "import math; print(math.add(1, 2))"
                }
                
                result = await adapter.analyze_files(file_contents, "What do these files do?")
                
                assert result == "The files contain Python code for math operations."
                mock_query.assert_called_once()
                
                # Check that the call includes file contents and question
                call_args = mock_query.call_args
                prompt = call_args[0][0]  # First positional argument
                assert "=== math.py ===" in prompt
                assert "=== test.py ===" in prompt
                assert "What do these files do?" in prompt


class TestGeminiQuestionToolCreation:
    """Test cases for creating Gemini-based question tools."""

    def create_test_workspace(self):
        """Create a temporary workspace with test files."""
        temp_dir = tempfile.mkdtemp()
        workspace = Workspace(temp_dir)
        
        # Create a test file
        test_file = Path(temp_dir) / "example.py"
        test_file.write_text("def hello(): return 'Hello, World!'")
        
        return workspace, temp_dir

    @pytest.mark.asyncio
    async def test_create_gemini_question_tool(self):
        """Test creating a question tool with Gemini CLI backend."""
        workspace, temp_dir = self.create_test_workspace()
        
        try:
            # Mock Gemini CLI availability and execution
            with patch('subprocess.run') as mock_which, \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess:
                
                mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
                
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (
                    b'This code defines a hello function that returns a greeting.',
                    b''
                )
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # Create the tool
                question_tool = create_gemini_question_tool(workspace)
                
                # Test the tool
                result = await question_tool("What does this code do?")
                
                assert "hello function" in result
                mock_subprocess.assert_called_once()
                
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio
    async def test_gemini_tool_with_no_files(self):
        """Test Gemini tool behavior when no files are found."""
        # Create empty workspace
        temp_dir = tempfile.mkdtemp()
        workspace = Workspace(temp_dir)
        
        try:
            with patch('subprocess.run') as mock_which:
                mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
                
                question_tool = create_gemini_question_tool(workspace)
                result = await question_tool("What files are here?")
                
                assert result == "No files found in the workspace to analyze."
                
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)

    @pytest.mark.asyncio  
    async def test_gemini_tool_with_read_error(self):
        """Test Gemini tool behavior when file reading fails."""
        workspace, temp_dir = self.create_test_workspace()
        
        try:
            with patch('subprocess.run') as mock_which, \
                 patch('asyncio.create_subprocess_exec') as mock_subprocess:
                
                mock_which.return_value.stdout = '/usr/local/bin/gemini\n'
                
                mock_process = AsyncMock()
                mock_process.communicate.return_value = (
                    b'Some files had read errors but analysis completed.',
                    b''
                )
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # Mock FileSystemTools to raise an error for one file
                with patch('crud_tools.gemini_adapter.FileSystemTools') as mock_fs:
                    mock_fs_instance = mock_fs.return_value
                    mock_fs_instance.list_files.return_value = ["good.py", "bad.py"]
                    
                    def mock_read_file(filename):
                        if filename == "bad.py":
                            raise Exception("Permission denied")
                        return "def test(): pass"
                    
                    mock_fs_instance.read_file.side_effect = mock_read_file
                    
                    question_tool = create_gemini_question_tool(workspace)
                    result = await question_tool("What's in these files?")
                    
                    # Should handle the error gracefully
                    assert "analysis completed" in result
                    
        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)


# Import subprocess for the test
import subprocess
