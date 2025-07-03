#!/usr/bin/env python3
"""
End-to-end integration test for MCP clients.

This script simulates MCP client workflows by sending requests
to the MCP server and validating the responses, ensuring complete
compliance with the MCP protocol specification.
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
import httpx

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class MCPIntegrationTester:
    """
    High-cohesion integration tester for MCP protocol compliance.
    
    This class encapsulates all MCP client simulation logic,
    providing a clean interface for testing file system operations
    through the MCP JSON-RPC 2.0 protocol.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/mcp"):
        self.base_url = base_url
        self.request_id = 0
    
    def _next_request_id(self) -> str:
        """Generate unique request ID for JSON-RPC calls."""
        self.request_id += 1
        return f"test-{self.request_id}"
    
    async def _make_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make JSON-RPC 2.0 request to MCP server.
        
        Centralizes request handling with proper error checking
        and protocol compliance validation.
        """
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._next_request_id()
        }
        
        if params:
            request_data["params"] = params
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.base_url, json=request_data, timeout=30.0)
            result = response.json()
            
            # Validate JSON-RPC 2.0 compliance
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
            
            if "result" not in result:
                raise Exception(f"Invalid JSON-RPC response: {result}")
            
            return result["result"]
    
    async def test_server_health(self) -> bool:
        """Test server health endpoint availability."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                if response.status_code == 200:
                    health_data = response.json()
                    print(f"✅ Server health: {health_data['status']}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_list_tools(self) -> bool:
        """Test MCP tools/list endpoint."""
        try:
            result = await self._make_request("tools/list")
            tools = result.get("tools", [])
            
            if len(tools) > 0:
                print(f"✅ Found {len(tools)} available tools:")
                for tool in tools[:3]:  # Show first 3 tools
                    print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
                return True
            else:
                print("❌ No tools found")
                return False
        except Exception as e:
            print(f"❌ Failed to list tools: {e}")
            return False
    
    async def test_file_operations(self) -> bool:
        """Test complete file operation workflow."""
        test_filename = "test_integration_file.txt"
        test_content = "This is a test file for MCP integration.\nSecond line for testing."
        
        try:
            # 1. Write file
            await self._make_request("tools/call", {
                "name": "write_file",
                "arguments": {
                    "filename": test_filename,
                    "content": test_content,
                    "mode": "w"
                }
            })
            print("✅ File written successfully")
            
            # 2. Read file
            read_result = await self._make_request("tools/call", {
                "name": "read_file",
                "arguments": {"filename": test_filename}
            })
            
            if read_result == test_content:
                print("✅ File content read correctly")
            else:
                print(f"❌ File content mismatch: expected '{test_content}', got '{read_result}'")
                return False
            
            # 3. List files to verify existence
            list_result = await self._make_request("tools/call", {
                "name": "list_files",
                "arguments": {}
            })
            
            if test_filename in str(list_result):
                print("✅ File appears in directory listing")
            else:
                print("❌ File not found in directory listing")
                return False
            
            # 4. Test question answering about files
            question_result = await self._make_request("tools/call", {
                "name": "answer_question_about_files",
                "arguments": {
                    "query": f"What does the {test_filename} file contain?"
                }
            })
            
            if "test file" in question_result.lower():
                print("✅ Question about file answered correctly")
            else:
                print(f"❌ Question answering failed: {question_result}")
                return False
            
            # 5. Delete file
            await self._make_request("tools/call", {
                "name": "delete_file",
                "arguments": {"filename": test_filename}
            })
            print("✅ File deleted successfully")
            
            return True
            
        except Exception as e:
            print(f"❌ File operations failed: {e}")
            return False
    
    async def test_directory_operations(self) -> bool:
        """Test directory listing operations."""
        try:
            # Test list_directories
            directories = await self._make_request("tools/call", {
                "name": "list_directories",
                "arguments": {}
            })
            print(f"✅ Found {len(directories)} directories")
            
            # Test list_all
            all_items = await self._make_request("tools/call", {
                "name": "list_all",
                "arguments": {}
            })
            print(f"✅ Found {len(all_items)} total items (files + directories)")
            
            # Test list_tree
            tree_result = await self._make_request("tools/call", {
                "name": "list_tree",
                "arguments": {}
            })
            
            if isinstance(tree_result, str) and len(tree_result) > 0:
                print("✅ Directory tree generated successfully")
                return True
            else:
                print("❌ Directory tree generation failed")
                return False
                
        except Exception as e:
            print(f"❌ Directory operations failed: {e}")
            return False


async def run_complete_mcp_integration_test():
    """Run complete MCP integration test suite."""
    print("🔄 STARTING MCP INTEGRATION TEST SUITE")
    print("=" * 60)
    
    tester = MCPIntegrationTester()
    
    # Test sequence with proper dependency order
    tests = [
        ("Server Health Check", tester.test_server_health),
        ("MCP Tools Listing", tester.test_list_tools),
        ("File Operations Workflow", tester.test_file_operations),
        ("Directory Operations", tester.test_directory_operations),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 40)
        
        try:
            if await test_func():
                passed_tests += 1
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"❌ {test_name} ERROR: {e}")
    
    print(f"\n📊 INTEGRATION TEST RESULTS")
    print("=" * 60)
    print(f"Passed: {passed_tests}/{total_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if passed_tests == total_tests:
        print("🎉 ALL INTEGRATION TESTS PASSED!")
        return True
    else:
        print("❌ Some integration tests failed")
        return False


if __name__ == "__main__":
    # Run the integration test
    success = asyncio.run(run_complete_mcp_integration_test())
    sys.exit(0 if success else 1)
