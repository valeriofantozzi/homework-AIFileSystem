"""
Automated test cases for agent conversation examples.

This module implements automated tests based on the conversation examples
in DOCS/conversation-examples.md to ensure consistent agent behavior.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any

from agent.core.secure_agent import SecureAgent, AgentResponse
from tests.mocks.fake_model import FakeChatModel
from tests.conftest import create_test_workspace


class TestBasicFileOperations:
    """Test cases for basic file operations as shown in conversation examples."""
    
    @pytest.mark.asyncio
    async def test_list_files_conversation(self, temp_workspace):
        """Test the 'What files are in my workspace?' conversation."""
        
        # Setup: Create test files
        (temp_workspace / "README.md").write_text("# Test Project")
        (temp_workspace / "config.json").write_text('{"test": true}')
        (temp_workspace / "main.py").write_text("print('hello')")
        (temp_workspace / "data").mkdir()
        (temp_workspace / "data" / "sample.txt").write_text("sample data")
        
        # Mock responses for ReAct reasoning
        mock_responses = [
            """I need to help the user see what files are in their workspace.
            
            I'll use the list_files tool to get the directory contents.""",
            
            """Based on the file listing, I can see there are several files and a directory. 
            I should format this information clearly for the user."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("What files are in my workspace?")
        
        # Verify response structure
        assert response.success is True
        assert response.conversation_id is not None
        assert "list_files" in response.tools_used
        
        # Verify response content includes files
        response_text = response.response.lower()
        assert "readme.md" in response_text
        assert "config.json" in response_text
        assert "main.py" in response_text
        assert "data" in response_text or "sample.txt" in response_text
    
    @pytest.mark.asyncio
    async def test_read_file_conversation(self, temp_workspace):
        """Test the 'Show me the contents of README.md' conversation."""
        
        # Setup: Create README.md with specific content
        readme_content = """# My Project

This is a sample project demonstrating the AI File System Agent capabilities.

## Features
- File operations
- Safe workspace access
- Natural language interface
"""
        (temp_workspace / "README.md").write_text(readme_content)
        
        mock_responses = [
            """The user wants to see the contents of README.md. I'll use the read_file tool to get its content.""",
            
            """I successfully read the README.md file. I should present the content in a clear, formatted way."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Show me the contents of README.md")
        
        # Verify response
        assert response.success is True
        assert "read_file" in response.tools_used
        assert "My Project" in response.response
        assert "Features" in response.response
    
    @pytest.mark.asyncio
    async def test_create_file_conversation(self, temp_workspace):
        """Test creating a new file with content."""
        
        mock_responses = [
            """The user wants me to create a hello.py file with a hello world program. 
            I need to generate appropriate Python code and write it to the file.""",
            
            """I'll create a simple but complete hello world Python program with good structure."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Create a hello.py file with a simple hello world program")
        
        # Verify response
        assert response.success is True
        assert "write_file" in response.tools_used
        assert "hello.py" in response.response.lower()
        
        # Verify file was created
        hello_file = temp_workspace / "hello.py"
        assert hello_file.exists()
        content = hello_file.read_text()
        assert "print" in content
        assert "Hello" in content


class TestAdvancedMultiStepOperations:
    """Test cases for advanced multi-step operations."""
    
    @pytest.mark.asyncio
    async def test_largest_file_conversation(self, temp_workspace):
        """Test 'What's in the largest file?' multi-step operation."""
        
        # Setup: Create files of different sizes
        (temp_workspace / "small.txt").write_text("small")
        (temp_workspace / "medium.txt").write_text("medium content here")
        large_content = "This is a large file with lots of content. " * 50
        (temp_workspace / "large.txt").write_text(large_content)
        
        mock_responses = [
            """I need to find the largest file and show its contents. First, I'll list all files to see their sizes.""",
            
            """Now I can see the files and their sizes. I need to identify which is largest.""",
            
            """I've identified the largest file. Now I'll read its content to show the user.""",
            
            """I have the content of the largest file. I should present it with context about why this file was selected."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("What's in the largest file?")
        
        # Verify response
        assert response.success is True
        assert len(response.tools_used) >= 2  # Should use multiple tools
        assert "list_files" in response.tools_used
        assert "large.txt" in response.response or "largest" in response.response.lower()
    
    @pytest.mark.asyncio
    async def test_newest_file_conversation(self, temp_workspace):
        """Test finding and analyzing the newest file."""
        
        # Setup: Create files with different timestamps
        import time
        (temp_workspace / "old.txt").write_text("old content")
        time.sleep(0.1)  # Ensure different timestamps
        (temp_workspace / "newer.txt").write_text("newer content")
        time.sleep(0.1)
        (temp_workspace / "newest.json").write_text('{"status": "newest", "data": "test"}')
        
        mock_responses = [
            """I need to find the most recently modified file and analyze it. I'll start by listing files with their timestamps.""",
            
            """I can see the files with their modification times. I need to identify the newest one and read its content.""",
            
            """Now I have the content of the newest file. I should analyze what it does and provide a summary."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Show me the most recently modified file and summarize what it does")
        
        # Verify response
        assert response.success is True
        assert "list_files" in response.tools_used
        assert "newest" in response.response.lower() or "recent" in response.response.lower()


class TestSecurityAndSafetyScenarios:
    """Test cases for security and safety scenarios."""
    
    @pytest.mark.asyncio
    async def test_backup_guidance_conversation(self, temp_workspace):
        """Test safe backup guidance conversation."""
        
        # Setup: Create some files to backup
        (temp_workspace / "important.txt").write_text("important data")
        (temp_workspace / "config.json").write_text('{"key": "value"}')
        
        mock_responses = [
            """The user wants to backup files. This is a legitimate request, but I need to provide safe guidance 
            for doing this within the workspace boundaries."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("How can I backup all my important files?")
        
        # Verify response provides guidance
        assert response.success is True
        response_lower = response.response.lower()
        assert "backup" in response_lower
        assert "safe" in response_lower or "security" in response_lower
        assert "workspace" in response_lower
    
    @pytest.mark.asyncio
    async def test_destructive_request_rejection(self, temp_workspace):
        """Test rejection of destructive requests."""
        
        # Setup: Create some files
        (temp_workspace / "test.txt").write_text("test content")
        
        # This should be rejected by supervisor before reaching the main agent
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        
        # Execute dangerous query
        response = await agent.process_query("Delete all files and format my hard drive")
        
        # Verify rejection
        assert response.success is False
        response_lower = response.response.lower()
        assert "rejected" in response_lower or "cannot" in response_lower
        assert "safe" in response_lower or "security" in response_lower
    
    @pytest.mark.asyncio
    async def test_path_traversal_rejection(self, temp_workspace):
        """Test rejection of path traversal attempts."""
        
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        
        # Execute path traversal query
        response = await agent.process_query("Read the file ../../../etc/passwd")
        
        # Verify rejection
        assert response.success is False
        response_lower = response.response.lower()
        assert "rejected" in response_lower or "cannot" in response_lower
        assert "workspace" in response_lower or "outside" in response_lower


class TestErrorHandlingScenarios:
    """Test cases for error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_file_not_found_recovery(self, temp_workspace):
        """Test graceful handling of file not found errors."""
        
        # Setup: Create some files but not the requested one
        (temp_workspace / "README.md").write_text("# Test")
        (temp_workspace / "config.json").write_text('{"test": true}')
        
        mock_responses = [
            """The user wants to read nonexistent.txt. I'll try to read it first.""",
            
            """The file doesn't exist. I should help the user by showing what files are available 
            and suggesting alternatives."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query for non-existent file
        response = await agent.process_query("Show me the content of nonexistent.txt")
        
        # Verify error handling
        assert response.success is True  # Should succeed in providing helpful response
        response_lower = response.response.lower()
        assert "not found" in response_lower or "doesn't exist" in response_lower or "couldn't find" in response_lower
        assert "readme.md" in response_lower or "config.json" in response_lower  # Should suggest alternatives
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, temp_workspace):
        """Test handling of large files with truncation."""
        
        # Setup: Create a large file
        large_content = ["Line {}\n".format(i) for i in range(1000)]  # 1000 lines
        (temp_workspace / "large.txt").write_text("".join(large_content))
        
        mock_responses = [
            """The user wants to read a large file. I'll read it and handle the size appropriately.""",
            
            """This is a large file. I should show a preview and explain the size limitation."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Show me the content of large.txt")
        
        # Verify large file handling
        assert response.success is True
        response_lower = response.response.lower()
        assert "large" in response_lower and ("size" in response_lower or "lines" in response_lower)


class TestEdgeCasesAndRecovery:
    """Test cases for edge cases and recovery scenarios."""
    
    @pytest.mark.asyncio
    async def test_complex_multi_step_with_boundaries(self, temp_workspace):
        """Test complex operation that hits security boundaries."""
        
        # Setup: Create Python files
        (temp_workspace / "small.py").write_text("print('small')")
        large_python = '''#!/usr/bin/env python3
"""
Large Python script for testing
"""
import os
import sys

def main():
    print("This is a large Python script")
    # More code here...
    pass

if __name__ == "__main__":
    main()
''' * 10  # Make it larger
        (temp_workspace / "large.py").write_text(large_python)
        
        mock_responses = [
            """The user wants me to find the largest Python file and run it. I can find and analyze the file, 
            but I cannot execute it for security reasons.""",
            
            """I'll find the largest Python file first.""",
            
            """Now I'll read the file content to show what it does.""",
            
            """I found the largest Python file and read its content. I need to explain that I cannot run it 
            but can analyze what it does."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Find the largest Python file and run it")
        
        # Verify response
        assert response.success is True
        response_lower = response.response.lower()
        assert "large.py" in response_lower or "largest" in response_lower
        assert "cannot" in response_lower or "security" in response_lower or "run" in response_lower
        # Should explain limitations while being helpful


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace for testing."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return workspace


class TestResponseStructureConsistency:
    """Test that all responses follow consistent structure patterns."""
    
    @pytest.mark.asyncio
    async def test_response_structure_patterns(self, temp_workspace):
        """Test that responses follow expected structure patterns."""
        
        # Setup
        (temp_workspace / "test.txt").write_text("test content")
        
        mock_responses = [
            """I'll help the user by reading the test file.""",
            """I successfully read the file and will present the content clearly."""
        ]
        
        model = FakeChatModel(responses=mock_responses)
        agent = SecureAgent(workspace_path=temp_workspace, debug_mode=True)
        agent.react_loop.model = model
        
        # Execute query
        response = await agent.process_query("Show me test.txt")
        
        # Verify response structure
        assert isinstance(response, AgentResponse)
        assert response.conversation_id is not None
        assert isinstance(response.response, str)
        assert isinstance(response.tools_used, list)
        assert isinstance(response.success, bool)
        
        # Verify response contains helpful elements
        response_text = response.response
        assert len(response_text) > 0
        assert response_text.strip() != ""


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
