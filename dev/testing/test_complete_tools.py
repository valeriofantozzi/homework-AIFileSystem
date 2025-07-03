#!/usr/bin/env python3
"""
Test finale per entrambi i nuovi tool: tree_workspace e show_complete_workspace.
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


async def test_complete_tools():
    """Test both new tools."""
    print("🧪 TESTING COMPLETE WORKSPACE TOOLS")
    print("=" * 50)
    
    try:
        workspace_path = project_root / "dev" / "sandbox"
        agent = SecureAgent(str(workspace_path), debug_mode=False)
        
        print(f"✅ Agent initialized")
        print(f"🔧 New tools available: tree_workspace, show_complete_workspace")
        
        # Test tree_workspace 
        print(f"\n🌳 Testing tree_workspace:")
        print("-" * 30)
        tree_result = agent.file_tools["tree_workspace"]()
        print(tree_result)
        
        # Test show_complete_workspace
        print(f"\n📋 Testing show_complete_workspace:")
        print("-" * 30)
        complete_result = agent.file_tools["show_complete_workspace"]()
        print(complete_result)
        
        # Test through agent queries
        print(f"\n🤖 Testing tree query:")
        print("-" * 30)
        response1 = await agent.process_query("tree")
        print(f"Response: {response1.response[:200]}...")
        print(f"Tools used: {response1.tools_used}")
        
        print(f"\n🤖 Testing complete listing query:")
        print("-" * 30)
        response2 = await agent.process_query("mostra tutto completo")
        print(f"Response: {response2.response[:200]}...")
        print(f"Tools used: {response2.tools_used}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_complete_tools())
