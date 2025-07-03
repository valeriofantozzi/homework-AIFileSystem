#!/usr/bin/env python3
"""
Test script per verificare che il nuovo tool tree_workspace funzioni correttamente.
"""

import sys
import asyncio
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "crud_tools" / "src"))
sys.path.insert(0, str(project_root / "tools" / "workspace_fs" / "src"))

from agent.core.secure_agent import SecureAgent


async def test_tree_tool():
    """Test the new tree_workspace tool."""
    print("🧪 TESTING NEW TREE TOOL")
    print("=" * 50)
    
    try:
        # Initialize agent with dev/sandbox workspace
        workspace_path = project_root / "dev" / "sandbox"
        
        print(f"📁 Using workspace: {workspace_path}")
        print(f"📁 Workspace exists: {workspace_path.exists()}")
        
        # Create agent
        agent = SecureAgent(str(workspace_path), debug_mode=True)
        
        print(f"\n✅ Agent initialized successfully")
        print(f"🔧 Available tools: {list(agent.file_tools.keys())}")
        
        # Test the tree tool directly
        print(f"\n🌳 Testing tree_workspace tool:")
        print("-" * 30)
        
        if "tree_workspace" in agent.file_tools:
            tree_result = agent.file_tools["tree_workspace"]()
            print(tree_result)
        else:
            print("❌ tree_workspace tool not found in available tools!")
            
        # Test through agent query
        print(f"\n🤖 Testing through agent query:")
        print("-" * 30)
        
        response = await agent.process_query("show me the tree structure of the workspace")
        print(f"Response: {response.response}")
        print(f"Tools used: {response.tools_used}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_tree_tool())
