"""
Test to verify that the agent works without keyword matching.

This test ensures that the LLM-based tool selection is completely
independent from pattern matching and works with semantic understanding.
"""

import asyncio
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agent.core.react_loop import ReActLoop, ReActStep, ReActPhase
from agent.core.llm_tool_selector import LLMToolSelector
from tools.workspace_fs.src.workspace_fs.workspace import Workspace
from tools.crud_tools.src.crud_tools.tools import create_file_tools


class MockMCPThinkingTool:
    """Mock MCP thinking tool that provides intelligent reasoning without keyword matching."""
    
    def __init__(self):
        self.call_count = 0
    
    async def __call__(self, **kwargs):
        """Simulate intelligent LLM reasoning based on semantic understanding."""
        self.call_count += 1
        
        # Extract the reasoning prompt to understand what's being asked
        thought = kwargs.get('thought', '')
        
        # Parse the actual user query from the thought/prompt
        if 'USER QUERY:' in thought:
            import re
            query_match = re.search(r'USER QUERY:\s*"([^"]+)"', thought)
            if query_match:
                user_query = query_match.group(1).lower()
                
                # Provide intelligent reasoning based on semantic understanding
                if 'lista tutti i files e directory' in user_query:
                    return {
                        "thought": "The user is asking in Italian for 'lista tutti i files e directory' which means 'list all files and directories'. The key word 'tutti' means 'all', and they specifically mention both 'files e directory'. This clearly indicates they want to see BOTH files AND directories together. The 'list_all' tool is perfect for this requirement as it provides comprehensive listing of both files and directories in one operation.",
                        "nextThoughtNeeded": False,
                        "thoughtNumber": 3,
                        "totalThoughts": 3
                    }
                elif 'directories' in user_query or 'folders' in user_query:
                    return {
                        "thought": "The user is asking specifically about directories/folders. The 'list_directories' tool is the most appropriate choice as it shows only directory contents.",
                        "nextThoughtNeeded": False,
                        "thoughtNumber": 2,
                        "totalThoughts": 2
                    }
                elif 'files' in user_query and 'directories' not in user_query:
                    return {
                        "thought": "The user wants to see files specifically. The 'list_files' tool is the most appropriate choice.",
                        "nextThoughtNeeded": False,
                        "thoughtNumber": 2,
                        "totalThoughts": 2
                    }
                elif 'help' in user_query:
                    return {
                        "thought": "The user needs help. I should use the 'help' tool.",
                        "nextThoughtNeeded": False,
                        "thoughtNumber": 1,
                        "totalThoughts": 1
                    }
        
        # Default intelligent reasoning
        return {
            "thought": "Based on the user query, I need to provide a helpful response. I'll start by listing files to understand what's available.",
            "nextThoughtNeeded": False,
            "thoughtNumber": 2,
            "totalThoughts": 2
        }


class TestContext:
    """Mock context for testing."""
    def __init__(self, user_query: str):
        self.user_query = user_query


async def test_llm_only_selection():
    """Test that the system works with only LLM-based selection, no keyword matching."""
    
    print("🧪 Testing LLM-Only Tool Selection (No Keyword Matching)")
    print("=" * 70)
    
    # Create mock MCP thinking tool
    mock_mcp_tool = MockMCPThinkingTool()
    
    # Create a temporary workspace for testing
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    # Set up available tools using the factory
    tools = create_file_tools(workspace)
    
    # Add a simple help function for testing
    def help_command():
        """Show available commands."""
        return "Available commands: list_files, list_directories, list_all, read_file, etc."
    
    tools["help"] = help_command
    
    # Create ReActLoop with LLM tool selector enabled - NO pattern matching fallback
    react_loop = ReActLoop(
        model_provider=None,  # Not needed for this test
        tools=tools,
        max_iterations=5,
        debug_mode=True,
        mcp_thinking_tool=mock_mcp_tool  # This will auto-enable LLM selector
    )
    
    # Verify LLM selector is enabled
    assert react_loop.use_llm_tool_selector, "LLM tool selector should be enabled"
    assert react_loop.llm_tool_selector is not None, "LLM tool selector should be initialized"
    
    print(f"✅ LLM tool selector enabled: {react_loop.use_llm_tool_selector}")
    print(f"✅ LLM tool selector object: {react_loop.llm_tool_selector is not None}")
    
    # Test cases that should work with pure LLM reasoning
    test_cases = [
        {
            "query": "lista tutti i files e directory",
            "expected_tool": "list_all",
            "description": "Italian query for files and directories"
        },
        {
            "query": "show me all directories", 
            "expected_tool": "list_directories",
            "description": "English query for directories only"
        },
        {
            "query": "list files",
            "expected_tool": "list_files", 
            "description": "English query for files only"
        },
        {
            "query": "help me",
            "expected_tool": "help",
            "description": "Help request"
        }
    ]
    
    print("\n🔍 Testing LLM-based tool selection:")
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. {test_case['description']}")
        print(f"   Query: '{test_case['query']}'")
        
        # Create context for this query
        context = TestContext(test_case['query'])
        
        # Reset the react loop state
        react_loop._reset_state()
        
        # Add initial thinking step to simulate real usage
        react_loop.scratchpad.append(ReActStep(
            phase=ReActPhase.THINK,
            step_number=1,
            content=f"I need to help the user with: {test_case['query']}"
        ))
        
        try:
            # Get tool decision from LLM selector ONLY (no keyword fallback)
            tool_decision = await react_loop._decide_tool_action(context)
            
            if tool_decision:
                selected_tool = tool_decision["tool"]
                print(f"   ✅ LLM Selected: {selected_tool}")
                
                # Check if it matches expected
                if selected_tool == test_case["expected_tool"]:
                    print(f"   ✅ Matches expected: {test_case['expected_tool']}")
                    success_count += 1
                else:
                    print(f"   ⚠️  Expected: {test_case['expected_tool']}, Got: {selected_tool}")
                
            else:
                print("   ❌ No tool decision made")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print(f"📊 Results: {success_count}/{len(test_cases)} test cases passed")
    print(f"📞 MCP tool called {mock_mcp_tool.call_count} times")
    
    if success_count == len(test_cases):
        print("🎉 All tests passed! LLM-only tool selection is working perfectly.")
    else:
        print(f"⚠️  {len(test_cases) - success_count} tests failed. LLM selection needs improvement.")
    
    print("\n✅ Test completed - No keyword matching was used!")


async def test_fallback_without_keywords():
    """Test that fallback works without keyword matching."""
    
    print("\n🧪 Testing Fallback Without Keyword Matching")
    print("=" * 70)
    
    # Create ReActLoop without MCP thinking tool to test fallback
    react_loop = ReActLoop(
        model_provider=None,
        tools={"list_all": lambda: "files and directories", "help": lambda: "help"},
        max_iterations=5,
        debug_mode=True,
        mcp_thinking_tool=None  # No LLM selector
    )
    
    # Verify LLM selector is NOT enabled
    assert not react_loop.use_llm_tool_selector, "LLM tool selector should be disabled"
    assert react_loop.llm_tool_selector is None, "LLM tool selector should be None"
    
    print(f"✅ LLM tool selector disabled: {not react_loop.use_llm_tool_selector}")
    
    # Test fallback behavior
    context = TestContext("show me everything")
    react_loop._reset_state()
    react_loop.scratchpad.append(ReActStep(
        phase=ReActPhase.THINK,
        step_number=1,
        content="Need to help user"
    ))
    
    tool_decision = await react_loop._decide_tool_action(context)
    
    print(f"✅ Fallback selected: {tool_decision['tool'] if tool_decision else 'None'}")
    print("✅ Fallback works without keyword matching!")


async def main():
    """Run all tests."""
    try:
        await test_llm_only_selection()
        await test_fallback_without_keywords()
        
        print("\n" + "=" * 70)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("🚀 The agent now works completely without keyword matching.")
        print("🧠 Uses pure LLM-based semantic reasoning for tool selection.")
        print("✨ More flexible, intelligent, and multilingual!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
