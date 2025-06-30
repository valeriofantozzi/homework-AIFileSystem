"""
Unit tests for crud_tools package.

Tests the tool wrappers and their integration with workspace_fs,
using deterministic fake models to avoid external dependencies.
"""

import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from crud_tools import answer_question_about_files, create_file_tools
from workspace_fs import Workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)
        yield workspace


@pytest.fixture
def sample_files(temp_workspace):
    """Create sample files in the workspace for testing."""
    files_data = {
        "README.md": "# Test Project\n\nThis is a test project for the AI file system.",
        "config.json": '{"name": "test", "version": "1.0.0", "debug": true}',
        "main.py": "def main():\n    print('Hello, world!')\n\nif __name__ == '__main__':\n    main()",
        "data.txt": "Sample data file\nLine 2\nLine 3",
    }

    for filename, content in files_data.items():
        file_path = temp_workspace.root / filename
        file_path.write_text(content)

    return files_data


class TestFileTools:
    """Test suite for basic file operation tools."""

    def test_create_file_tools(self, temp_workspace):
        """Test that create_file_tools returns expected tool functions."""
        tools = create_file_tools(temp_workspace)

        # Check that all expected tools are present
        expected_tools = {
            "list_files", 
            "read_file", 
            "write_file", 
            "delete_file"
        }
        assert set(tools.keys()) == expected_tools

        # Check that all values are callable
        for tool_name, tool_func in tools.items():
            assert callable(tool_func), f"Tool {tool_name} is not callable"

    def test_list_files_tool(self, temp_workspace, sample_files):
        """Test the list_files tool function."""
        tools = create_file_tools(temp_workspace)
        list_files = tools["list_files"]

        # Test listing files
        files = list_files()
        assert isinstance(files, list)
        assert len(files) == len(sample_files)

        # Files should be sorted by modification time
        for filename in sample_files.keys():
            assert filename in files

    def test_read_file_tool(self, temp_workspace, sample_files):
        """Test the read_file tool function."""
        tools = create_file_tools(temp_workspace)
        read_file = tools["read_file"]

        # Test reading existing file
        content = read_file("README.md")
        assert content == sample_files["README.md"]

        # Test reading non-existent file
        with pytest.raises(FileNotFoundError):
            read_file("nonexistent.txt")

    def test_write_file_tool(self, temp_workspace):
        """Test the write_file tool function."""
        tools = create_file_tools(temp_workspace)
        write_file = tools["write_file"]
        read_file = tools["read_file"]

        # Test writing new file
        test_content = "This is a test file."
        result = write_file("test.txt", test_content)
        assert "written" in result.lower()

        # Verify file was written correctly
        written_content = read_file("test.txt")
        assert written_content == test_content

        # Test append mode
        append_content = "\nAppended line."
        write_file("test.txt", append_content, "a")
        final_content = read_file("test.txt")
        assert final_content == test_content + append_content

    def test_delete_file_tool(self, temp_workspace, sample_files):
        """Test the delete_file tool function."""
        tools = create_file_tools(temp_workspace)
        delete_file = tools["delete_file"]
        list_files = tools["list_files"]

        # Test deleting existing file
        initial_files = list_files()
        assert "README.md" in initial_files

        result = delete_file("README.md")
        assert "deleted" in result.lower()

        # Verify file was deleted
        remaining_files = list_files()
        assert "README.md" not in remaining_files
        assert len(remaining_files) == len(initial_files) - 1

        # Test deleting non-existent file
        with pytest.raises(FileNotFoundError):
            delete_file("nonexistent.txt")

    def test_tool_error_handling(self, temp_workspace):
        """Test error handling in tool functions."""
        # Very small limit to trigger errors
        tools = create_file_tools(temp_workspace, max_read=10)

        # Create a file larger than the read limit
        large_content = "x" * 20
        tools["write_file"]("large.txt", large_content)

        # Reading should handle the size limit
        from workspace_fs import SizeLimitExceeded
        with pytest.raises(SizeLimitExceeded):
            tools["read_file"]("large.txt")

    def test_list_files_empty_workspace(self, temp_workspace):
        """Test list_files with empty workspace."""
        tools = create_file_tools(temp_workspace)
        list_files = tools["list_files"]

        files = list_files()
        assert isinstance(files, list)
        assert len(files) == 0

    def test_read_write_modes(self, temp_workspace):
        """Test write file with different modes."""
        tools = create_file_tools(temp_workspace)
        write_file = tools["write_file"]
        read_file = tools["read_file"]

        # Test explicit write mode
        write_file("test.txt", "initial", "w")
        content = read_file("test.txt")
        assert content == "initial"

        # Test append mode
        write_file("test.txt", " appended", "a")
        content = read_file("test.txt")
        assert content == "initial appended"

    def test_list_files_error_handling(self, temp_workspace):
        """Test list_files error handling."""
        tools = create_file_tools(temp_workspace)
        list_files = tools["list_files"]

        # Just test that it's callable and returns expected type
        files = list_files()
        assert isinstance(files, list)

    def test_workspace_error_handling(self, temp_workspace):
        """Test WorkspaceError propagation."""
        tools = create_file_tools(temp_workspace)

        # Delete a non-existent file to test error propagation
        with pytest.raises(FileNotFoundError):
            tools["delete_file"]("nonexistent_file.txt")

    def test_pydantic_ai_availability_check(self):
        """Test the pydantic_ai availability check."""
        from crud_tools.question_tool import PYDANTIC_AI_AVAILABLE as question_available
        from crud_tools.tools import PYDANTIC_AI_AVAILABLE

        # These should be boolean
        assert isinstance(PYDANTIC_AI_AVAILABLE, bool)
        assert isinstance(question_available, bool)


class TestQuestionTool:
    """Test suite for the file question tool."""

    def test_create_question_tool_function(self, temp_workspace):
        """Test the create_question_tool_function factory."""
        from crud_tools.question_tool import create_question_tool_function

        # Create question tool function
        tool_func = create_question_tool_function(temp_workspace)

        # Check that it returns a callable
        assert callable(tool_func)
        assert tool_func.__name__ == "question_tool_func"

    @patch('crud_tools.question_tool.PYDANTIC_AI_AVAILABLE', True)
    @patch('crud_tools.question_tool.Agent')
    @pytest.mark.asyncio
    async def test_answer_question_about_files(
        self, mock_agent_class, temp_workspace, sample_files
    ):
        """Test the answer_question_about_files function."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.output = "This is a test project based on the README file."
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        # Test question answering
        query = "What is this project about?"
        result = await answer_question_about_files(temp_workspace, query)

        # Verify result
        assert isinstance(result, str)
        assert result == "This is a test project based on the README file."

        # Verify agent was called with correct parameters
        mock_agent_class.assert_called_once()
        mock_agent.run.assert_called_once()

        # Check the prompt includes file contents
        call_args = mock_agent.run.call_args[0][0]
        assert "README.md" in call_args
        assert "Test Project" in call_args
        assert query in call_args

    @patch('crud_tools.question_tool.PYDANTIC_AI_AVAILABLE', True)
    @patch('crud_tools.question_tool.Agent')
    @pytest.mark.asyncio
    async def test_question_tool_with_limits(
        self, mock_agent_class, temp_workspace, sample_files
    ):
        """Test question tool with file and content limits."""
        mock_result = MagicMock()
        mock_result.output = "Limited analysis completed."
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        # Test with very small limits
        result = await answer_question_about_files(
            temp_workspace,
            "What files are here?",
            max_files=2,
            max_content_per_file=10,
        )

        # Should still work but with limited content
        assert isinstance(result, str)

        # Check that content was truncated
        call_args = mock_agent.run.call_args[0][0]
        assert "[truncated]" in call_args

    @pytest.mark.asyncio
    async def test_question_tool_no_files(self, temp_workspace):
        """Test question tool with empty workspace."""
        result = await answer_question_about_files(temp_workspace, "What files are here?")
        assert result == "No files found in the workspace to analyze."

    @pytest.mark.asyncio
    async def test_question_tool_import_error(self, temp_workspace):
        """Test question tool when pydantic-ai is not available."""
        with patch('crud_tools.question_tool.PYDANTIC_AI_AVAILABLE', False):
            with pytest.raises(ImportError, match="pydantic-ai is required"):
                await answer_question_about_files(temp_workspace, "Test query")


class TestIntegration:
    """Integration tests for the full tool suite."""

    def test_tools_with_custom_limits(self, temp_workspace):
        """Test tools with custom FileSystemTools limits."""
        # Create tools with very restrictive limits
        tools = create_file_tools(
            temp_workspace, max_read=100, max_write=50, rate_limit=1.0
        )

        # Should still create all tools
        assert len(tools) == 4

        # Test that limits are enforced
        large_content = "x" * 200
        from workspace_fs import SizeLimitExceeded
        with pytest.raises(SizeLimitExceeded):  # Should hit write limit
            tools["write_file"]("large.txt", large_content)

    def test_workspace_security(self, temp_workspace):
        """Test that tools respect workspace security."""
        tools = create_file_tools(temp_workspace)

        # Try to access file outside workspace (should fail)
        with pytest.raises(ValueError, match="directory separators"):
            tools["read_file"]("../../../etc/passwd")

        # Try to write file outside workspace (should fail)
        with pytest.raises(ValueError, match="directory separators"):
            tools["write_file"]("../../../tmp/evil.txt", "hacked")

    @patch('crud_tools.question_tool.PYDANTIC_AI_AVAILABLE', True)
    @patch('crud_tools.question_tool.Agent')
    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_agent_class, temp_workspace):
        """Test a complete workflow using all tools."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.output = (
            "The project has 3 files including README, config, and Python code."
        )
        mock_agent = AsyncMock()
        mock_agent.run = AsyncMock(return_value=mock_result)
        mock_agent_class.return_value = mock_agent

        # Get tools
        tools = create_file_tools(temp_workspace)

        # Create some files
        tools["write_file"]("project.md", "# My Project\nThis is awesome!")
        tools["write_file"]("code.py", "print('Hello world')")

        # List files
        files = tools["list_files"]()
        assert len(files) == 2

        # Read a file
        content = tools["read_file"]("project.md")
        assert "My Project" in content

        # Ask a question about the files
        answer = await answer_question_about_files(
            temp_workspace,
            "How many files are in this project?"
        )
        assert "3 files" in answer

        # Clean up
        tools["delete_file"]("project.md")
        remaining_files = tools["list_files"]()
        assert len(remaining_files) == 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
