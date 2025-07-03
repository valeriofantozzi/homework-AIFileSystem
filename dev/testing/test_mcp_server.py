#!/usr/bin/env python3
"""
Test script for the MCP server implementation.

This script tests the MCP server as a standalone component without
dependencies on the SecureAgent architecture.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tools" / "crud_tools" / "src"))
sys.path.insert(0, str(project_root / "tools" / "workspace_fs" / "src"))

from server.api_mcp.mcp_server import MCPServer


async def test_mcp_server():
    """Test the MCP server functionality."""
    print("🧪 TESTING MCP SERVER (STANDALONE)")
    print("=" * 50)
    
    try:
        # Create test workspace
        test_workspace = project_root / "dev" / "sandbox" / "mcp_test"
        test_workspace.mkdir(parents=True, exist_ok=True)
        
        # Create some test files
        (test_workspace / "test.txt").write_text("Hello from MCP server!")
        (test_workspace / "data.json").write_text('{"name": "test", "version": "1.0"}')
        
        print(f"📁 Test workspace: {test_workspace}")
        
        # Initialize MCP server
        server = MCPServer(str(test_workspace))
        await server.initialize()
        
        print("✅ MCP server initialized successfully")
        print(f"🔧 Available tools: {list(server.file_tools.keys())}")
        
        # Test tools
        test_cases = [
            ("list_files", {}),
            ("read_file", {"filename": "test.txt"}),
            ("list_directories", {}),
            ("list_all", {}),
        ]
        
        for tool_name, arguments in test_cases:
            print(f"\n🛠️  Testing tool: {tool_name}")
            print(f"   Arguments: {arguments}")
            
            try:
                result = await server.execute_tool(tool_name, arguments)
                print(f"   ✅ Success: {result.content[0]['text'][:100]}...")
                print(f"   🎯 Error: {result.isError}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test the async tool
        print(f"\n🤖 Testing async tool: answer_question_about_files")
        try:
            result = await server.execute_tool(
                "answer_question_about_files", 
                {"query": "What files are in this workspace?"}
            )
            print(f"   ✅ Success: {result.content[0]['text'][:100]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n🎉 MCP server test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_server())
