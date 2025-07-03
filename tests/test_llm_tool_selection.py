"""
Test suite for LLM-based tool selection mechanism.

This module contains comprehensive tests for the LLMToolSelector and its integration
into the ReActLoop, ensuring correct tool selection for various user queries.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from dataclasses import dataclass

from agent.core.llm_tool_selector import LLMToolSelector, ToolSelectionResult
from agent.core.react_loop import ReActLoop, ReActPhase, ReActStep


@dataclass
class MockContext:
    """Mock context for testing."""
    user_query: str
    conversation_id: str = "test-conv"
    current_directory: str = "/test/dir"
    tool_chain_context = None


class TestLLMToolSelector:
    """Test cases for the LLMToolSelector class."""
    
    @pytest.fixture
    def mock_mcp_tool(self):
        """Create a mock MCP thinking tool."""
        mock_tool = AsyncMock()
        # Mock successful reasoning output
        mock_tool.return_value = {
            "thought": "Based on the user query 'list all files', I need to analyze what tool is best. The user wants to see files in the directory. The available tools include list_files, list_directories, and list_all. Since they specifically want 'all files', the list_files tool is most appropriate.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 3,
            "totalThoughts": 3
        }
        return mock_tool
    
    @pytest.fixture
    def llm_tool_selector(self, mock_mcp_tool):
        """Create an LLMToolSelector instance."""
        return LLMToolSelector(mock_mcp_tool)
    
    def test_tool_metadata_construction(self, llm_tool_selector):
        """Test that tool metadata is correctly constructed."""
        available_tools = {
            "list_files": {"description": "List files", "parameters": {}},
            "read_file": {"description": "Read file", "parameters": {"filename": "string"}}
        }
        
        metadata = llm_tool_selector._build_tool_metadata_prompt(available_tools)
        
        assert "list_files" in metadata
        assert "read_file" in metadata
        assert "List files" in metadata
        assert "filename" in metadata
    
    @pytest.mark.asyncio
    async def test_select_tool_basic(self, llm_tool_selector, mock_mcp_tool):
        """Test basic tool selection functionality."""
        # Setup mock response that indicates list_files
        mock_mcp_tool.return_value = {
            "thought": "The user wants to list files. The most appropriate tool is list_files.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }
        
        available_tools = {
            "list_files": {"description": "List all files", "parameters": {}},
            "list_directories": {"description": "List directories", "parameters": {}}
        }
        
        result = await llm_tool_selector.select_tool(
            user_query="show me all files",
            available_tools=available_tools,
            context={}
        )
        
        assert result.selected_tool == "list_files"
        assert result.confidence > 0.7  # Should be confident about this clear request
        assert "list" in result.reasoning.lower()
    
    @pytest.mark.asyncio
    async def test_select_tool_with_parameters(self, llm_tool_selector, mock_mcp_tool):
        """Test tool selection with parameter extraction."""
        # Mock response for read_file with filename
        mock_mcp_tool.return_value = {
            "thought": "The user wants to read test.txt. I should use read_file with filename='test.txt'.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }
        
        available_tools = {
            "read_file": {"description": "Read file content", "parameters": {"filename": "string"}},
            "list_files": {"description": "List files", "parameters": {}}
        }
        
        result = await llm_tool_selector.select_tool(
            user_query="read test.txt",
            available_tools=available_tools,
            context={}
        )
        
        assert result.selected_tool == "read_file"
        assert "test.txt" in result.suggested_parameters.get("filename", "")
    
    @pytest.mark.asyncio
    async def test_ambiguous_query_handling(self, llm_tool_selector, mock_mcp_tool):
        """Test handling of ambiguous queries."""
        # Mock response for ambiguous query
        mock_mcp_tool.return_value = {
            "thought": "The query 'show me stuff' is ambiguous. Could mean files or directories. I'll suggest list_all to show both.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 3,
            "totalThoughts": 3
        }
        
        available_tools = {
            "list_files": {"description": "List files", "parameters": {}},
            "list_directories": {"description": "List directories", "parameters": {}},
            "list_all": {"description": "List files and directories", "parameters": {}}
        }
        
        result = await llm_tool_selector.select_tool(
            user_query="show me stuff",
            available_tools=available_tools,
            context={}
        )
        
        assert result.selected_tool == "list_all"
        assert result.confidence < 0.9  # Should be less confident about ambiguous queries
        assert len(result.alternatives) > 0  # Should suggest alternatives
    
    def test_parse_tool_from_reasoning(self, llm_tool_selector):
        """Test parsing tool names from reasoning text."""
        reasoning = "Based on the analysis, I recommend using the list_files tool to show all files."
        available_tools = ["list_files", "list_directories", "read_file"]
        
        tool = llm_tool_selector._parse_tool_from_reasoning(reasoning, available_tools)
        assert tool == "list_files"
    
    def test_parse_tool_with_quotes(self, llm_tool_selector):
        """Test parsing tool names when mentioned in quotes."""
        reasoning = "I should use 'read_file' to read the content."
        available_tools = ["list_files", "read_file", "write_file"]
        
        tool = llm_tool_selector._parse_tool_from_reasoning(reasoning, available_tools)
        assert tool == "read_file"
    
    def test_extract_parameters_from_reasoning(self, llm_tool_selector):
        """Test parameter extraction from reasoning text."""
        reasoning = "I need to read the file 'config.txt' using read_file tool."
        
        params = llm_tool_selector._extract_parameters_from_reasoning(reasoning, "read_file")
        assert "filename" in params
        assert params["filename"] == "config.txt"
    
    def test_extract_pattern_parameter(self, llm_tool_selector):
        """Test extraction of pattern parameters."""
        reasoning = "I should find files with pattern '*.py' using find_files_by_pattern."
        
        params = llm_tool_selector._extract_parameters_from_reasoning(reasoning, "find_files_by_pattern")
        assert "pattern" in params
        assert params["pattern"] == "*.py"


class TestReActLoopLLMIntegration:
    """Test cases for LLM tool selection integration in ReActLoop."""
    
    @pytest.fixture
    def mock_tools(self):
        """Create mock tools for testing."""
        return {
            "list_files": Mock(return_value="file1.txt\nfile2.py"),
            "list_directories": Mock(return_value="dir1/\ndir2/"),
            "list_all": Mock(return_value="file1.txt\ndir1/\nfile2.py"),
            "read_file": Mock(return_value="File content"),
            "help": Mock(return_value="Available commands...")
        }
    
    @pytest.fixture
    def mock_mcp_tool(self):
        """Create a mock MCP thinking tool."""
        return AsyncMock()
    
    @pytest.fixture
    def react_loop(self, mock_tools, mock_mcp_tool):
        """Create a ReActLoop instance with LLM tool selector enabled."""
        return ReActLoop(
            tools=mock_tools,
            max_iterations=3,
            debug_mode=True,
            use_llm_tool_selector=True,
            mcp_thinking_tool=mock_mcp_tool
        )
    
    @pytest.mark.asyncio
    async def test_llm_tool_selection_enabled(self, react_loop, mock_mcp_tool):
        """Test that LLM tool selection is properly enabled."""
        assert react_loop.use_llm_tool_selector is True
        assert react_loop.llm_tool_selector is not None
    
    @pytest.mark.asyncio
    async def test_english_file_listing_query(self, react_loop, mock_mcp_tool):
        """Test English query for file listing."""
        # Mock LLM response for file listing
        mock_mcp_tool.return_value = {
            "thought": "User wants to see files. I'll use list_files tool.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }
        
        context = MockContext(user_query="show me all files")
        
        # Add initial thinking step to scratchpad
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content="I need to show the user all files."
        ))
        
        tool_decision = await react_loop._decide_tool_action(context)
        
        assert tool_decision is not None
        assert tool_decision["tool"] == "list_files"
    
    @pytest.mark.asyncio
    async def test_italian_directory_listing_query(self, react_loop, mock_mcp_tool):
        """Test Italian query for directory listing."""
        # Mock LLM response for directory listing
        mock_mcp_tool.return_value = {
            "thought": "L'utente vuole vedere le cartelle. Uso list_directories.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }
        
        context = MockContext(user_query="mostra tutte le cartelle")
        
        # Add initial thinking step
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content="I need to show directories to the user."
        ))
        
        tool_decision = await react_loop._decide_tool_action(context)
        
        assert tool_decision is not None
        assert tool_decision["tool"] == "list_directories"
    
    @pytest.mark.asyncio
    async def test_complex_multi_step_query(self, react_loop, mock_mcp_tool):
        """Test complex query requiring multiple steps."""
        # Mock LLM responses for multi-step reasoning
        responses = [
            {
                "thought": "User wants the largest file. First I need to list files to see what's available.",
                "nextThoughtNeeded": False,
                "thoughtNumber": 3,
                "totalThoughts": 3
            },
            {
                "thought": "Now I have file list. I should use find_largest_file to identify the biggest one.",
                "nextThoughtNeeded": False,
                "thoughtNumber": 2,
                "totalThoughts": 2
            }
        ]
        
        mock_mcp_tool.side_effect = responses
        
        context = MockContext(user_query="show me the largest file")
        
        # Simulate first step - thinking
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content="I need to find the largest file."
        ))
        
        # First tool decision should be list_files
        tool_decision1 = await react_loop._decide_tool_action(context)
        assert tool_decision1["tool"] == "list_files"
        
        # Simulate having taken the first action
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.ACT,
            step_number=2,
            content="Listed files",
            tool_name="list_files",
            tool_result="file1.txt\nfile2.py\nlarge_file.dat"
        ))
        
        # Second tool decision should be find_largest_file
        tool_decision2 = await react_loop._decide_tool_action(context)
        assert tool_decision2["tool"] == "find_largest_file"
    
    @pytest.mark.asyncio
    async def test_fallback_to_pattern_matching(self, react_loop, mock_mcp_tool):
        """Test fallback to pattern matching when LLM selection fails."""
        # Mock LLM failure
        mock_mcp_tool.side_effect = Exception("LLM service unavailable")
        
        context = MockContext(user_query="list directories")
        
        # Add thinking step
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content="I need to list directories."
        ))
        
        tool_decision = await react_loop._decide_tool_action(context)
        
        # Should fall back to pattern matching and still work
        assert tool_decision is not None
        assert tool_decision["tool"] == "list_directories"
    
    @pytest.mark.asyncio
    async def test_filename_extraction_from_llm(self, react_loop, mock_mcp_tool):
        """Test filename extraction when LLM suggests file operations."""
        # Mock LLM response that suggests reading a specific file
        mock_mcp_tool.return_value = {
            "thought": "User wants to read 'config.json'. I'll use read_file with filename='config.json'.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }
        
        context = MockContext(user_query="read config.json")
        
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content="I need to read a file."
        ))
        
        tool_decision = await react_loop._decide_tool_action(context)
        
        assert tool_decision is not None
        assert tool_decision["tool"] == "read_file"
        assert tool_decision["args"]["filename"] == "config.json"
    
    def test_build_tools_metadata(self, react_loop):
        """Test building of tools metadata for LLM context."""
        metadata = react_loop._build_tools_metadata()
        
        assert "list_files" in metadata
        assert "description" in metadata["list_files"]
        assert "parameters" in metadata["list_files"]
        
        # Check that file operation tools have filename parameter
        if "read_file" in metadata:
            assert "filename" in metadata["read_file"]["parameters"]
    
    def test_build_llm_context(self, react_loop):
        """Test building of context for LLM tool selector."""
        context = MockContext(
            user_query="lista tutti i files", 
            current_directory="/test"
        )
        
        # Add some previous actions
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.ACT,
            step_number=1,
            content="Listed files",
            tool_name="list_files"
        ))
        
        llm_context = react_loop._build_llm_context(context)
        
        assert "current_directory" in llm_context
        assert llm_context["current_directory"] == "/test"
        assert "previous_action" in llm_context
        assert llm_context["previous_action"] == "list_files"
        assert "user_language" in llm_context
        assert llm_context["user_language"] == "Italian"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test handling of empty user queries."""
        mock_mcp_tool = AsyncMock()
        selector = LLMToolSelector(mock_mcp_tool)
        
        result = await selector.select_tool(
            user_query="",
            available_tools={},
            context={}
        )
        
        # Should handle gracefully
        assert result.selected_tool is None or result.confidence < 0.5
    
    @pytest.mark.asyncio
    async def test_no_available_tools(self):
        """Test behavior when no tools are available."""
        mock_mcp_tool = AsyncMock()
        mock_mcp_tool.return_value = {
            "thought": "No tools available.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 1,
            "totalThoughts": 1
        }
        
        selector = LLMToolSelector(mock_mcp_tool)
        
        result = await selector.select_tool(
            user_query="do something",
            available_tools={},
            context={}
        )
        
        assert result.selected_tool is None
    
    @pytest.mark.asyncio
    async def test_mcp_tool_timeout(self):
        """Test handling of MCP tool timeouts."""
        mock_mcp_tool = AsyncMock()
        mock_mcp_tool.side_effect = TimeoutError("MCP tool timed out")
        
        selector = LLMToolSelector(mock_mcp_tool)
        
        # Should handle timeout gracefully
        with pytest.raises(Exception):
            await selector.select_tool(
                user_query="test query",
                available_tools={"test_tool": {"description": "Test"}},
                context={}
            )
    
    def test_invalid_tool_parsing(self):
        """Test parsing when reasoning contains no valid tool names."""
        mock_mcp_tool = Mock()
        selector = LLMToolSelector(mock_mcp_tool)
        
        reasoning = "This reasoning contains no valid tool names at all."
        available_tools = ["list_files", "read_file"]
        
        tool = selector._parse_tool_from_reasoning(reasoning, available_tools)
        assert tool is None
    
    def test_malformed_parameter_extraction(self):
        """Test parameter extraction from malformed reasoning."""
        mock_mcp_tool = Mock()
        selector = LLMToolSelector(mock_mcp_tool)
        
        reasoning = "Use read_file with filename=unclosed_quote"
        
        params = selector._extract_parameters_from_reasoning(reasoning, "read_file")
        # Should handle gracefully and not crash
        assert isinstance(params, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
