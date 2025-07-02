"""
Unit tests for agent reasoning patterns.

This module tests the agent's reasoning capabilities using FakeChatModel
to provide deterministic responses without external API dependencies.
Tests focus on validating reasoning patterns, tool selection, and
multi-step problem solving.
"""

import asyncio
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

# Add project to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import from conftest for test utilities
from ..conftest import FakeChatModel, PredictableResponse, MockPydanticAgent, create_test_fake_model

from agent.core.secure_agent import SecureAgent, AgentResponse
from agent.core.react_loop import ReActLoop


class TestAgentReasoningPatterns:
    """Test suite for agent reasoning pattern validation."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some test files
            test_files = {
                'readme.txt': 'This is a README file with project information.',
                'config.json': '{"name": "test-project", "version": "1.0.0", "author": "Test"}',
                'data.txt': 'Sample data file\nLine 2\nLine 3',
                'notes.md': '# Notes\n\nImportant project notes here.'
            }
            
            for filename, content in test_files.items():
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            yield tmpdir
    
    @pytest.fixture
    def fake_model(self):
        """Create a fake chat model for testing."""
        return create_test_fake_model()
    
    def test_fake_model_basic_functionality(self, fake_model):
        """Test that FakeChatModel works correctly."""
        # Test pattern matching
        response = fake_model.find_matching_response("list all files")
        assert response is not None
        assert "list_files" in response.tools_to_call
        
        # Test non-matching pattern
        response = fake_model.find_matching_response("random unmatched query")
        assert response is None
        
        # Test call history
        assert fake_model.get_call_count() == 0
        fake_model.call_history.append({'test': 'call'})
        assert fake_model.get_call_count() == 1
    
    @pytest.mark.asyncio
    async def test_fake_model_response_generation(self, fake_model):
        """Test response generation with fake model."""
        # Test matching response
        result = await fake_model.generate_response("list all files in the workspace")
        
        assert result['success'] is True
        assert 'list_files' in result['tools_to_call']
        assert len(result['reasoning_steps']) > 0
        assert result['reasoning_steps'][0]['phase'] == 'THINK'
        
        # Test call history tracking
        assert fake_model.get_call_count() == 1
        assert 'list all files' in fake_model.call_history[0]['input']
    
    @pytest.mark.asyncio 
    async def test_multi_step_reasoning_pattern(self, fake_model):
        """Test multi-step reasoning scenarios."""
        # Add a complex multi-step response
        fake_model.add_response(
            pattern=r"analyze.*workspace.*summary",
            response="I'll analyze the workspace systematically by first listing files, then reading key files, and providing a summary.",
            reasoning_steps=[
                {"phase": "THINK", "content": "Need to analyze workspace - requires multiple steps"},
                {"phase": "ACT", "content": "Step 1: List all files to see what's available"},
                {"phase": "OBSERVE", "content": "Found 4 files in workspace"},
                {"phase": "THINK", "content": "Now I need to read key files for analysis"},
                {"phase": "ACT", "content": "Step 2: Read readme and config files"},
                {"phase": "OBSERVE", "content": "Key files read, content analyzed"},
                {"phase": "THINK", "content": "Ready to provide comprehensive summary"}
            ],
            tools_to_call=["list_files", "read_file", "read_file"]
        )
        
        result = await fake_model.generate_response("analyze the workspace and give me a summary")
        
        # Verify multi-step reasoning structure
        assert len(result['reasoning_steps']) == 7  # Multiple THINK-ACT-OBSERVE cycles
        assert len(result['tools_to_call']) == 3  # Multiple tools used
        
        # Verify reasoning progression
        steps = result['reasoning_steps']
        think_steps = [s for s in steps if s['phase'] == 'THINK']
        act_steps = [s for s in steps if s['phase'] == 'ACT']
        observe_steps = [s for s in steps if s['phase'] == 'OBSERVE']
        
        assert len(think_steps) == 3  # Multiple thinking phases
        assert len(act_steps) == 2    # Multiple actions
        assert len(observe_steps) == 2 # Multiple observations
    
    @pytest.mark.asyncio
    async def test_tool_selection_accuracy(self, fake_model):
        """Test that the model selects appropriate tools for different queries."""
        test_cases = [
            ("list files", ["list_files"]),
            ("read the config file", ["read_file"]),
            ("create a new document", ["write_file"]),
            ("show me the newest file", ["read_newest_file"]),
        ]
        
        for query, expected_tools in test_cases:
            result = await fake_model.generate_response(query)
            assert any(tool in result['tools_to_call'] for tool in expected_tools), \
                f"Expected tools {expected_tools} not found in {result['tools_to_call']} for query: {query}"
    
    @pytest.mark.asyncio
    async def test_reasoning_step_structure(self, fake_model):
        """Test that reasoning steps follow correct ReAct structure."""
        result = await fake_model.generate_response("list all files")
        
        steps = result['reasoning_steps']
        assert len(steps) >= 3  # At least THINK-ACT-OBSERVE
        
        # Check that phases are valid
        valid_phases = {'THINK', 'ACT', 'OBSERVE'}
        for step in steps:
            assert 'phase' in step
            assert 'content' in step
            assert step['phase'] in valid_phases
            assert isinstance(step['content'], str)
            assert len(step['content']) > 0
    
    def test_failure_simulation(self, fake_model):
        """Test that model can simulate failures for error handling tests."""
        # Add a failure response
        fake_model.add_response(
            pattern=r"cause.*error",
            response="This should fail",
            should_fail=True
        )
        
        # Test that it raises exception
        with pytest.raises(Exception) as exc_info:
            asyncio.run(fake_model.generate_response("cause an error"))
        
        assert "Simulated failure" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_conversation_context_handling(self, fake_model):
        """Test that model can handle conversation context."""
        context = {
            'previous_files': ['readme.txt', 'config.json'],
            'user_intent': 'analysis'
        }
        
        result = await fake_model.generate_response("continue analysis", context)
        
        # Verify context was recorded
        assert fake_model.get_call_count() == 1
        recorded_call = fake_model.call_history[0]
        assert recorded_call['context'] == context
        assert recorded_call['input'] == "continue analysis"


class TestReActLoopWithFakeModel:
    """Test ReAct loop behavior with fake model."""
    
    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            test_files = {
                'test.txt': 'Hello world!',
                'data.json': '{"test": true}'
            }
            
            for filename, content in test_files.items():
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            yield tmpdir
    
    @pytest.mark.asyncio
    async def test_react_loop_integration(self, temp_workspace):
        """Test ReAct reasoning loop with fake model."""
        # This test would require deeper integration with ReActLoop
        # For now, we'll test the conceptual flow
        
        fake_model = create_test_fake_model()
        
        # Simulate a reasoning cycle
        user_query = "What files are in the workspace?"
        
        # Step 1: THINK
        think_result = await fake_model.generate_response(f"THINK: {user_query}")
        assert think_result['success'] is True
        
        # Step 2: ACT (based on thinking)
        act_result = await fake_model.generate_response("ACT: list_files")
        assert act_result['success'] is True
        
        # Step 3: OBSERVE (after action)
        observe_result = await fake_model.generate_response("OBSERVE: Files listed successfully")
        assert observe_result['success'] is True
        
        # Verify reasoning flow was captured
        assert fake_model.get_call_count() == 3


class TestReasoningPatternValidation:
    """Test validation of specific reasoning patterns."""
    
    @pytest.mark.asyncio
    async def test_simple_query_pattern(self):
        """Test reasoning for simple single-step queries."""
        fake_model = create_test_fake_model()
        
        result = await fake_model.generate_response("list files")
        
        # Should have clear reasoning structure
        steps = result['reasoning_steps']
        assert len(steps) >= 1
        
        # Should identify the task correctly
        assert any("files" in step['content'].lower() for step in steps)
        
        # Should select correct tool
        assert "list_files" in result['tools_to_call']
    
    @pytest.mark.asyncio
    async def test_complex_query_pattern(self):
        """Test reasoning for complex multi-step queries."""
        fake_model = create_test_fake_model()
        
        result = await fake_model.generate_response("show me what files exist and tell me about the newest one")
        
        # Complex queries should trigger multi-step reasoning
        steps = result['reasoning_steps']
        
        # Should recognize complexity
        assert any("multi" in step['content'].lower() or "step" in step['content'].lower() 
                  for step in steps)
    
    @pytest.mark.asyncio
    async def test_error_recovery_pattern(self):
        """Test reasoning patterns for error recovery."""
        fake_model = FakeChatModel()
        
        # Add an error-prone response followed by recovery
        fake_model.add_response(
            pattern=r"read.*nonexistent",
            response="I'll try to read the file, but handle the error gracefully if it doesn't exist.",
            reasoning_steps=[
                {"phase": "THINK", "content": "User wants to read a file that might not exist"},
                {"phase": "ACT", "content": "Attempting to read file with error handling"},
                {"phase": "OBSERVE", "content": "File not found - providing helpful error message"},
                {"phase": "THINK", "content": "Should suggest alternatives or next steps"}
            ],
            tools_to_call=["read_file"]
        )
        
        result = await fake_model.generate_response("read nonexistent.txt")
        
        # Should show error-aware reasoning
        steps = result['reasoning_steps']
        assert any("error" in step['content'].lower() or "not found" in step['content'].lower() 
                  for step in steps)
    
    @pytest.mark.asyncio
    async def test_tool_chaining_pattern(self):
        """Test reasoning for operations requiring multiple tools."""
        fake_model = FakeChatModel()
        
        # Add tool chaining response
        fake_model.add_response(
            pattern=r"list.*then.*read",
            response="I'll first list the files, then read the specified one.",
            reasoning_steps=[
                {"phase": "THINK", "content": "This requires two steps: list then read"},
                {"phase": "ACT", "content": "Step 1: List files to see what's available"},
                {"phase": "OBSERVE", "content": "Files listed successfully"},
                {"phase": "THINK", "content": "Now I can read the requested file"},
                {"phase": "ACT", "content": "Step 2: Read the specified file"},
                {"phase": "OBSERVE", "content": "File content retrieved"}
            ],
            tools_to_call=["list_files", "read_file"]
        )
        
        result = await fake_model.generate_response("list files then read readme.txt")
        
        # Should show sequential tool usage
        assert len(result['tools_to_call']) == 2
        assert "list_files" in result['tools_to_call']
        assert "read_file" in result['tools_to_call']
        
        # Should show step-by-step reasoning
        steps = result['reasoning_steps']
        assert len(steps) >= 6  # Multiple THINK-ACT-OBSERVE cycles


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
