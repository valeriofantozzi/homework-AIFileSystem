#!/usr/bin/env python3
"""Simple test to verify clarification questions work end-to-end."""

import asyncio
import tempfile
from pathlib import Path
import os
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from agent.core.react_loop import ReActLoop
from agent.core.secure_agent import SecureAgent
from config.model_config import ModelConfig


async def test_simple_clarification():
    """Test the simplest clarification case."""
    print("🧪 Simple Clarification Test")
    print("=" * 40)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace_path = Path(temp_dir)
        
        # Create a test file
        (workspace_path / "test.txt").write_text("Hello world")
        
        try:
            config = ModelConfig()
            agent = SecureAgent(
                workspace_path=str(workspace_path),
                debug_mode=True
            )
            
            # Test default goal generation directly
            react_loop = agent.react_loop
            
            print("1. Testing default goal generation for ambiguous queries:")
            test_queries = ["help", "what can you do", "do something"]
            
            for query in test_queries:
                goal = react_loop._generate_default_goal(query)
                print(f"   '{query}' → {goal}")
                
                if goal == "AMBIGUOUS_REQUEST":
                    print("   ✅ Correctly identified as ambiguous")
                else:
                    print("   ❌ Should be identified as ambiguous")
            
            print("\n2. Testing clarification formatting:")
            clarification = "What specific task would you like help with?"
            goal = "Help the user with a task"
            original_query = "help"
            
            formatted = react_loop._format_clarification_response(clarification, goal, original_query)
            print(f"   Formatted response:\n{formatted}")
            
            if "Clarification Needed" in formatted:
                print("   ✅ Contains clarification marker")
            else:
                print("   ❌ Missing clarification marker")
                
            # Now test a mock LLM response that includes clarification
            print("\n3. Testing LLM response parsing with clarification:")
            
            mock_json_response = '''
            {
                "thinking": "The user just said 'help' which is very vague. I need to ask what specific task they want help with.",
                "goal": "Request clarification for vague help request",
                "tool_name": null,
                "tool_args": {},
                "continue_reasoning": false,
                "final_response": null,
                "goal_compliance_check": null,
                "clarification_question": "What specific task would you like help with? I can assist with file operations, reading content, or answering questions about your workspace.",
                "confidence": 0.8
            }
            '''
            
            from agent.core.react_loop import ConsolidatedReActResponse
            
            parsed = ConsolidatedReActResponse.from_json_string(mock_json_response)
            
            print(f"   Parsed goal: {parsed.goal}")
            print(f"   Parsed clarification: {parsed.clarification_question}")
            print(f"   Tool name: {parsed.tool_name}")
            print(f"   Continue reasoning: {parsed.continue_reasoning}")
            
            if parsed.clarification_question:
                print("   ✅ Clarification question parsed correctly")
                
                # Test the formatting of this clarification
                formatted_clarification = react_loop._format_clarification_response(
                    parsed.clarification_question,
                    parsed.goal,
                    "help"
                )
                
                print(f"\n   Formatted clarification response:\n{formatted_clarification}")
                
                if "❓" in formatted_clarification and "Clarification Needed" in formatted_clarification:
                    print("   ✅ Clarification response formatted correctly")
                else:
                    print("   ❌ Clarification response formatting issue")
            else:
                print("   ❌ Clarification question not parsed")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_simple_clarification())
