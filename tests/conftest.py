"""
Test configuration and shared fixtures for the AI File System Agent project.

This module provides pytest fixtures and test utilities that are shared
across unit and integration tests, following Clean Architecture principles.
"""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from unittest.mock import AsyncMock, MagicMock

import pytest


@dataclass
class PredictableResponse:
    """A predefined response for specific input patterns."""
    
    pattern: str  # Regex pattern to match input
    response: str  # Response to return
    reasoning_steps: Optional[List[Dict[str, Any]]] = None
    tools_to_call: Optional[List[str]] = None
    should_fail: bool = False


class FakeChatModel:
    """
    A fake chat model for deterministic testing.
    
    This model can be configured with predefined responses that match
    input patterns, allowing for predictable testing of agent reasoning
    without external API dependencies.
    """
    
    def __init__(self, responses: Optional[List[PredictableResponse]] = None):
        """Initialize with optional predefined responses."""
        self.responses = responses or []
        self.call_history = []
        self.default_response = "I understand your request and will help you with that."
        
    def add_response(self, pattern: str, response: str, **kwargs):
        """Add a response pattern to the model."""
        self.responses.append(PredictableResponse(
            pattern=pattern,
            response=response,
            **kwargs
        ))
    
    def find_matching_response(self, input_text: str) -> Optional[PredictableResponse]:
        """Find the first response that matches the input pattern."""
        for response in self.responses:
            if re.search(response.pattern, input_text, re.IGNORECASE):
                return response
        return None
    
    async def generate_response(self, input_text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate a response for the given input."""
        # Record the call
        self.call_history.append({
            'input': input_text,
            'context': context,
            'timestamp': 'test_time'
        })
        
        # Find matching response
        matching_response = self.find_matching_response(input_text)
        
        if matching_response:
            if matching_response.should_fail:
                raise Exception(f"Simulated failure for pattern: {matching_response.pattern}")
            
            return {
                'response': matching_response.response,
                'reasoning_steps': matching_response.reasoning_steps or [],
                'tools_to_call': matching_response.tools_to_call or [],
                'success': True
            }
        
        # Default response
        return {
            'response': self.default_response,
            'reasoning_steps': [],
            'tools_to_call': [],
            'success': True
        }
    
    def reset_history(self):
        """Clear the call history."""
        self.call_history = []
    
    def get_call_count(self) -> int:
        """Get the number of calls made to this model."""
        return len(self.call_history)


class MockPydanticAgent:
    """
    Mock implementation of pydantic_ai.Agent for testing.
    
    This provides the same interface as the real Agent but uses
    FakeChatModel for predictable responses.
    """
    
    def __init__(self, model: FakeChatModel, **kwargs):
        """Initialize with a fake model."""
        self.model = model
        self.system_prompt = kwargs.get('system_prompt', '')
        self.tools = kwargs.get('tools', [])
        
        # Mock the run method
        self.run = AsyncMock()
        self.run.side_effect = self._mock_run
    
    async def _mock_run(self, user_prompt: str, **kwargs) -> MagicMock:
        """Mock implementation of agent.run()."""
        # Generate response using fake model
        result = await self.model.generate_response(user_prompt, kwargs)
        
        # Create mock result object
        mock_result = MagicMock()
        mock_result.data = result['response']
        mock_result.cost = None
        mock_result.usage = None
        
        return mock_result


# Predefined response patterns for common testing scenarios
COMMON_REASONING_PATTERNS = [
    PredictableResponse(
        pattern=r"list.*files?",
        response="I need to check what files are available in the workspace. Let me list them for you.",
        reasoning_steps=[
            {"phase": "THINK", "content": "User wants to see available files"},
            {"phase": "ACT", "content": "Using list_files tool"},
            {"phase": "OBSERVE", "content": "Files retrieved successfully"}
        ],
        tools_to_call=["list_files"]
    ),
    PredictableResponse(
        pattern=r"read.*file|show.*content",
        response="I'll read the requested file and show you its contents.",
        reasoning_steps=[
            {"phase": "THINK", "content": "User wants to read file contents"},
            {"phase": "ACT", "content": "Using read_file tool"},
            {"phase": "OBSERVE", "content": "File content retrieved"}
        ],
        tools_to_call=["read_file"]
    ),
    PredictableResponse(
        pattern=r"create.*file|write.*file|create.*document|new.*document",
        response="I'll create the file with the specified content.",
        reasoning_steps=[
            {"phase": "THINK", "content": "User wants to create a new file"},
            {"phase": "ACT", "content": "Using write_file tool"},
            {"phase": "OBSERVE", "content": "File created successfully"}
        ],
        tools_to_call=["write_file"]
    ),
    PredictableResponse(
        pattern=r"newest.*file|latest.*file",
        response="I'll find and read the newest file in the workspace.",
        reasoning_steps=[
            {"phase": "THINK", "content": "User wants the newest file"},
            {"phase": "ACT", "content": "Finding newest file"},
            {"phase": "OBSERVE", "content": "Newest file identified and read"}
        ],
        tools_to_call=["read_newest_file"]
    ),
    PredictableResponse(
        pattern=r"multi.step|complex.*task|files.*exist.*tell.*newest|show.*files.*newest|what.*files.*newest",
        response="This requires multiple steps. I'll break it down systematically.",
        reasoning_steps=[
            {"phase": "THINK", "content": "This is a complex multi-step task"},
            {"phase": "ACT", "content": "First, I'll list the files"},
            {"phase": "OBSERVE", "content": "Files listed, now processing"},
            {"phase": "THINK", "content": "Next, I need to analyze the content"},
            {"phase": "ACT", "content": "Reading relevant files"},
            {"phase": "OBSERVE", "content": "Content analyzed, providing summary"}
        ],
        tools_to_call=["list_files", "read_file"]
    )
]


@pytest.fixture
def fake_chat_model():
    """Provide a FakeChatModel pre-configured with common test patterns."""
    return FakeChatModel(COMMON_REASONING_PATTERNS)


@pytest.fixture
def mock_pydantic_agent(fake_chat_model):
    """Provide a MockPydanticAgent for testing."""
    return MockPydanticAgent(fake_chat_model)


def create_test_fake_model() -> FakeChatModel:
    """Create a FakeChatModel pre-configured with common test patterns."""
    model = FakeChatModel(COMMON_REASONING_PATTERNS)
    return model
