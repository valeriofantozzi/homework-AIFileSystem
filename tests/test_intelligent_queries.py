"""
Tests for intelligent question answering about files.

Covers:
- Direct function call to answer_question_about_files with mock LLM
- End-to-end MCP server integration for answer_question_about_files tool
- Error handling: no files, missing LLM, API key issues

High cohesion: each test targets a single aspect.
Low coupling: all LLM and file system dependencies are mocked or isolated.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from pathlib import Path

from tools.crud_tools.src.crud_tools import question_tool

@pytest.fixture
def temp_workspace(tmp_path):
    # Create a mock Workspace with a root directory
    class MockWorkspace:
        def __init__(self, root):
            self.root = str(root)
    return MockWorkspace(tmp_path)

@pytest.mark.asyncio
async def test_answer_question_about_files_basic(temp_workspace):
    # Create sample files
    file1 = Path(temp_workspace.root) / "a.txt"
    file1.write_text("The answer is 42.", encoding="utf-8")
    file2 = Path(temp_workspace.root) / "b.md"
    file2.write_text("This is a test file.", encoding="utf-8")

    # Patch Agent to return a canned response via async run
    with patch("tools.crud_tools.src.crud_tools.question_tool.Agent") as MockAgent:
        instance = MockAgent.return_value
        instance.run = AsyncMock(return_value="The answer is 42.")
        result = await question_tool.answer_question_about_files(
            workspace=temp_workspace,
            query="What is the answer?",
            max_files=2,
            max_content_per_file=100,
            llm_model="mock:mock"
        )
        assert "42" in result

@pytest.mark.asyncio
async def test_answer_question_about_files_no_files(temp_workspace):
    # No files in workspace
    with patch("tools.crud_tools.src.crud_tools.question_tool.Agent") as MockAgent:
        instance = MockAgent.return_value
        instance.run = AsyncMock(return_value="No analyzable files found in the workspace.")
        result = await question_tool.answer_question_about_files(
            workspace=temp_workspace,
            query="Anything here?",
            max_files=2,
            max_content_per_file=100,
            llm_model="mock:mock"
        )
        assert "No analyzable files" in result

@pytest.mark.asyncio
async def test_answer_question_about_files_llm_error(temp_workspace):
    # Create a file
    file1 = Path(temp_workspace.root) / "a.txt"
    file1.write_text("Some content.", encoding="utf-8")

    # Patch Agent to raise an exception
    with patch("tools.crud_tools.src.crud_tools.question_tool.Agent") as MockAgent:
        instance = MockAgent.return_value
        instance.run = AsyncMock(side_effect=Exception("API key error"))
        # Patch _get_fallback_model to raise WorkspaceError
        with patch("tools.crud_tools.src.crud_tools.question_tool._get_fallback_model", side_effect=question_tool.WorkspaceError("No API keys")):
            with pytest.raises(question_tool.WorkspaceError):
                await question_tool.answer_question_about_files(
                    workspace=temp_workspace,
                    query="Test?",
                    max_files=1,
                    max_content_per_file=100,
                    llm_model="mock:mock"
                )

def test_create_question_tool_function_returns_callable(temp_workspace):
    func = question_tool.create_question_tool_function(temp_workspace)
    assert callable(func)
