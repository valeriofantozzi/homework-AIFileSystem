#!/usr/bin/env python3
"""
End-to-end integration test for MCP clients.

This script simulates MCP client workflows by sending requests
to the MCP server and validating the responses. Tests all core
file system operations exposed through the MCP protocol.

Architectural Notes:
- High cohesion: Single responsibility for MCP protocol testing
- Low coupling: Tests interface contracts, not implementation details
- Clean separation: Integration layer testing only
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any
import httpx

# Add project paths for testing
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class MCPIntegrationTester:
    """
    Encapsulates MCP protocol integration testing.
    
    High cohesion: Single responsibility for MCP client simulation
    Low coupling: Depends only on HTTP interface abstractions
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/mcp"):
        self.base_url = base_url
        self.request_id = 0
    
    def _next_request_id(self) -> str:
        """Generate sequential request IDs for JSON-RPC 2.0 compliance."""
        self.request_id += 1
        return f"test-{self.request_id}"
    
    async def test_tools_list(self, client: httpx.AsyncClient) -> Dict[str, Any]:
        """Test tools/list method to verify available tools."""
        request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=request)
        result = response.json()
        
        assert "result" in result, f"Expected 'result' in response: {result}"
        
        # The MCP server returns tools in result.tools
        tools_list = result["result"].get("tools", result["result"])
        assert isinstance(tools_list, list), f"Tools list should be an array, got: {type(tools_list)}"
        assert len(tools_list) > 0, "Should have at least one tool available"
        
        # Verify required file system tools are present
        tool_names = {tool["name"] for tool in tools_list}
        required_tools = {
            "list_files", "read_file", "write_file", "delete_file",
            "list_directories", "list_all", "list_tree", "answer_question_about_files"
        }
        
        missing_tools = required_tools - tool_names
        assert not missing_tools, f"Missing required tools: {missing_tools}"
        
        print(f"✅ Found {len(tools_list)} tools: {tool_names}")
        return result
    
    async def test_file_operations_workflow(self, client: httpx.AsyncClient) -> None:
        """Test complete file operations workflow: write → read → list → delete."""
        test_filename = "integration_test.txt"
        test_content = "This is a test file for MCP integration testing."
        
        # 1. Write file
        write_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "write_file",
                "arguments": {
                    "filename": test_filename,
                    "content": test_content,
                    "mode": "w"
                }
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=write_request)
        result = response.json()
        assert "result" in result, f"Write file failed: {result}"
        print(f"✅ File '{test_filename}' written successfully")
        
        # 2. Read file
        read_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "read_file",
                "arguments": {"filename": test_filename}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=read_request)
        result = response.json()
        assert "result" in result, f"Read file failed: {result}"
        
        # Handle MCP protocol format: result.content[0].text
        content_result = result["result"]
        if isinstance(content_result, dict) and "content" in content_result:
            # MCP protocol format
            content_blocks = content_result["content"]
            assert len(content_blocks) > 0, "Expected at least one content block"
            actual_content = content_blocks[0]["text"]
        else:
            # Direct string format
            actual_content = content_result
            
        assert actual_content == test_content, f"Content mismatch: expected '{test_content}', got '{actual_content}'"
        print(f"✅ File content read correctly")
        
        # 3. List files (verify file appears)
        list_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_files",
                "arguments": {}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=list_request)
        result = response.json()
        assert "result" in result, f"List files failed: {result}"
        
        # Handle MCP protocol format: result.content[0].text
        list_result = result["result"]
        if isinstance(list_result, dict) and "content" in list_result:
            # MCP protocol format
            content_blocks = list_result["content"]
            assert len(content_blocks) > 0, "Expected at least one content block"
            files_text = content_blocks[0]["text"]
        else:
            # Direct format
            files_text = str(list_result)
            
        assert test_filename in files_text, f"File not found in listing: {files_text}"
        print(f"✅ File appears in directory listing")
        
        # 4. Question about files
        question_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "answer_question_about_files",
                "arguments": {
                    "query": f"What is the content of {test_filename}?"
                }
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=question_request)
        result = response.json()
        assert "result" in result, f"Question answering failed: {result}"
        
        # Handle MCP protocol format: result.content[0].text
        answer_result = result["result"]
        if isinstance(answer_result, dict) and "content" in answer_result:
            # MCP protocol format
            content_blocks = answer_result["content"]
            assert len(content_blocks) > 0, "Expected at least one content block"
            answer_text = content_blocks[0]["text"]
        else:
            # Direct format
            answer_text = str(answer_result)
            
        # The answer should mention the test content
        assert "test" in answer_text.lower(), f"Answer doesn't mention test content: {answer_text}"
        print(f"✅ Question about files answered correctly")
        
        # 5. Delete file
        delete_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "delete_file",
                "arguments": {"filename": test_filename}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=delete_request)
        result = response.json()
        assert "result" in result, f"Delete file failed: {result}"
        print(f"✅ File '{test_filename}' deleted successfully")
    
    async def test_directory_operations(self, client: httpx.AsyncClient) -> None:
        """Test directory listing operations."""
        # Test list_directories
        dir_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_directories",
                "arguments": {}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=dir_request)
        result = response.json()
        assert "result" in result, f"List directories failed: {result}"
        print(f"✅ Directories listed successfully")
        
        # Test list_all
        all_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_all",
                "arguments": {}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=all_request)
        result = response.json()
        assert "result" in result, f"List all failed: {result}"
        print(f"✅ All items listed successfully")
        
        # Test list_tree
        tree_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "list_tree",
                "arguments": {}
            },
            "id": self._next_request_id()
        }
        
        response = await client.post(self.base_url, json=tree_request)
        result = response.json()
        assert "result" in result, f"List tree failed: {result}"
        print(f"✅ Tree view generated successfully")


async def run_mcp_integration_tests():
    """
    Main test runner for MCP integration tests.
    
    This function orchestrates the complete test suite,
    ensuring all MCP protocol operations work correctly.
    """
    print("🔄 STARTING MCP CLIENT INTEGRATION TESTS")
    print("=" * 60)
    
    tester = MCPIntegrationTester()
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test 1: Verify tools are available
            print("\n📋 Test 1: Listing available tools")
            await tester.test_tools_list(client)
            
            # Test 2: Complete file operations workflow
            print("\n📁 Test 2: File operations workflow")
            await tester.test_file_operations_workflow(client)
            
            # Test 3: Directory operations
            print("\n📂 Test 3: Directory operations")
            await tester.test_directory_operations(client)
            
            print("\n🎉 ALL MCP INTEGRATION TESTS PASSED!")
            print("✅ MCP server is ready for client integration")
            
    except httpx.ConnectError:
        print("❌ ERROR: Cannot connect to MCP server")
        print("   Make sure the server is running at http://localhost:8000")
        print("   Run: ./server/deploy.sh prod")
        sys.exit(1)
    except AssertionError as e:
        print(f"❌ TEST FAILURE: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_mcp_integration_tests())
