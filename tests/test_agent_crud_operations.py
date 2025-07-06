"""
Core CRUD functionality tests for the AI File System Agent.

Each test covers a single file operation (list, create/write, read, append, delete)
and uses the clean_workspace fixture for isolation.

Follows high cohesion, low coupling, and Clean Architecture principles.
"""

import pytest
from pathlib import Path
from tests.conftest import assert_successful_response, assert_error_response

pytestmark = [pytest.mark.asyncio]

class TestCoreFileOperations:
    async def test_list_files_empty_workspace(self, clean_workspace):
        agent, workspace_path = clean_workspace
        response = await agent.process_query("List all files in the workspace.")
        assert_successful_response(response.response, "list files")
        # Should be empty or indicate no files present
        assert "no files" in response.response.lower() or len(response.response) < 100

    async def test_write_file_create_new(self, clean_workspace):
        agent, workspace_path = clean_workspace
        response = await agent.process_query("Create a file called 'test.txt' with the content 'Hello, World!'")
        assert_successful_response(response.response, "file creation")
        test_file = workspace_path / "test.txt"
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"

    async def test_read_file_existing(self, clean_workspace):
        agent, workspace_path = clean_workspace
        test_file = workspace_path / "readme.md"
        test_file.write_text("Read me please.")
        response = await agent.process_query("Read the file 'readme.md'")
        # Accept short but correct content for file read
        assert "read me please" in response.response.lower()

    async def test_append_to_file(self, clean_workspace):
        agent, workspace_path = clean_workspace
        test_file = workspace_path / "append.txt"
        test_file.write_text("Line 1\n")
        response = await agent.process_query("Append 'Line 2' to the file 'append.txt'")
        assert_successful_response(response.response, "file append")
        # Accept trailing newline (POSIX standard)
        assert test_file.read_text() in ("Line 1\nLine 2", "Line 1\nLine 2\n")

    async def test_delete_file(self, clean_workspace):
        agent, workspace_path = clean_workspace
        test_file = workspace_path / "delete_me.txt"
        test_file.write_text("To be deleted.")
        response = await agent.process_query("Delete the file 'delete_me.txt'")
        assert_successful_response(response.response, "file delete")
        assert not test_file.exists()

    async def test_read_nonexistent_file(self, clean_workspace):
        agent, workspace_path = clean_workspace
        response = await agent.process_query("Read the file 'ghost.txt'")
        assert_error_response(response.response, "read nonexistent file")

    async def test_delete_nonexistent_file(self, clean_workspace):
        agent, workspace_path = clean_workspace
        response = await agent.process_query("Delete the file 'ghost.txt'")
        assert_error_response(response.response, "delete nonexistent file")
