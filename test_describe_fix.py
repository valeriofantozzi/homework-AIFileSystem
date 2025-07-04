#!/usr/bin/env python3
"""
Quick test to verify the describe query fix.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent.core.react_loop import ReActLoop, ConsolidatedReActResponse
import structlog

# Mock LLM response that simulates proper completion for describe queries
async def mock_llm_response_with_completion(prompt: str) -> str:
    """Mock LLM that provides proper final response for describe queries."""
    
    if "describe" in prompt and "secure_agent.py" in prompt:
        # Check if we've already read the file (based on context)
        if "CONTEXT FROM TOOLS:" in prompt and "class SecureAgent" in prompt:
            # We have file content, provide final response
            return '''
            {
              "thinking": "I have successfully read the secure_agent.py file and can now provide a comprehensive description. The file contains the SecureAgent class and related functionality.",
              "tool_name": null,
              "tool_args": {},
              "continue_reasoning": false,
              "final_response": "## Description of secure_agent.py\n\nThis is the main agent implementation file containing the SecureAgent class. The file defines the core autonomous agent logic using the ReAct (Reasoning-Action-Observation) pattern for secure file operations within the workspace. It includes methods for processing user queries, maintaining conversation context, coordinating with the security supervisor, and executing tools safely. The agent provides structured responses with comprehensive error handling and maintains detailed reasoning traces for debugging and audit purposes.",
              "confidence": 0.9
            }
            '''
        elif "find_file_by_name" in prompt or "read_file" in prompt:
            # We need to read the file
            return '''
            {
              "thinking": "I need to read the content of secure_agent.py to provide a comprehensive description.",
              "tool_name": "read_file",
              "tool_args": {"filename": "secure_agent.py"},
              "continue_reasoning": true,
              "final_response": null,
              "confidence": 0.8
            }
            '''
        else:
            # First step - find the file
            return '''
            {
              "thinking": "I need to find the secure_agent.py file first, then read its content to provide a description.",
              "tool_name": "find_file_by_name",
              "tool_args": {"filename": "secure_agent.py"},
              "continue_reasoning": true,
              "final_response": null,
              "confidence": 0.8
            }
            '''
    
    # Default fallback
    return '''
    {
      "thinking": "I need to help with this request.",
      "tool_name": "list_all",
      "tool_args": {},
      "continue_reasoning": false,
      "final_response": "I can help you with file operations.",
      "confidence": 0.7
    }
    '''

# Mock tools
def mock_find_file():
    return "Found file: agent/core/secure_agent.py"

def mock_read_file(filename="secure_agent.py"):
    return '''"""
SecureAgent implementation module.

This module contains the main SecureAgent class that handles autonomous
file operations using the ReAct reasoning pattern.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

class SecureAgent:
    """
    Main autonomous agent for secure file operations.
    
    This agent uses ReAct reasoning to process user queries safely
    within workspace boundaries.
    """
    
    def __init__(self, config):
        self.config = config
        self.logger = structlog.get_logger(__name__)
    
    async def process_query(self, query: str, context: Any):
        """Process user query with ReAct reasoning."""
        # Implementation here
        pass
    
    def validate_request(self, request: str) -> bool:
        """Validate request for security."""
        return True
'''

async def test_describe_fix():
    """Test the describe query fix."""
    
    print("🧪 Testing Describe Query Fix")
    print("=" * 40)
    
    # Set up logger
    logger = structlog.get_logger(__name__)
    
    # Mock tools
    tools = {
        "find_file_by_name": mock_find_file,
        "read_file": mock_read_file,
        "list_all": lambda: "file1.txt, file2.py, secure_agent.py"
    }
    
    # Create ReAct loop with the improved logic
    react_loop = ReActLoop(
        model_provider=None,  # We're using mock function
        tools=tools,
        logger=logger,
        max_iterations=5,
        debug_mode=True,
        llm_response_func=mock_llm_response_with_completion,
        use_llm_tool_selector=False
    )
    
    # Mock context
    class MockContext:
        def __init__(self):
            self.conversation_id = "test-123"
            self.user_query = "describe secure_agent.py"
    
    context = MockContext()
    
    print(f"Query: '{context.user_query}'")
    print()
    
    try:
        # Execute the ReAct loop
        result = await react_loop.execute(context.user_query, context)
        
        print(f"✅ Success: {result.success}")
        print(f"🔄 Iterations: {result.iterations}")
        print(f"🛠️  Tools used: {result.tools_used}")
        print()
        print("📝 Final Response:")
        print("-" * 20)
        print(result.response)
        print("-" * 20)
        
        # Check if we got a proper description (not just raw file content)
        if (result.response and 
            ("description" in result.response.lower() or "agent implementation" in result.response.lower()) and
            len(result.response) > 100):
            print("\n✅ SUCCESS: Got proper file description!")
            return True
        else:
            print(f"\n❌ ISSUE: Response doesn't look like a proper description:")
            print(f"Response: {result.response[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_describe_fix())
    print(f"\n🎯 Test Result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)
