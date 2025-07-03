#!/usr/bin/env python3
"""
Test script for the full MCP HTTP API.

This script tests the MCP server running as an HTTP service with
all endpoints including health, metrics, and diagnostics.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

# Add project paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def test_mcp_http_api():
    """Test the MCP server HTTP API."""
    print("🌐 TESTING MCP HTTP API")
    print("=" * 50)
    
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health endpoint
            print("\n🏥 Testing /health endpoint")
            response = await client.get(f"{base_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                health = response.json()
                print(f"   Health: {health['status']}")
                print(f"   Uptime: {health['uptime']:.2f}s")
            
            # Test metrics endpoint
            print("\n📊 Testing /metrics endpoint")
            response = await client.get(f"{base_url}/metrics")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                metrics = response.json()
                print(f"   Total requests: {metrics['total_requests']}")
                print(f"   Tool calls: {metrics['tool_calls']}")
            
            # Test diagnostics endpoint
            print("\n🔍 Testing /diagnostics endpoint")
            response = await client.get(f"{base_url}/diagnostics")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                diagnostics = response.json()
                print(f"   Server initialized: {diagnostics['agent_status']['initialized']}")
                print(f"   Workspace path: {diagnostics['workspace_info']['path']}")
            
            # Test MCP tools/list
            print("\n🛠️  Testing MCP tools/list")
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-1",
                "method": "tools/list"
            }
            response = await client.post(f"{base_url}/mcp", json=mcp_request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    tools = result["result"]["tools"]
                    print(f"   Available tools: {[t['name'] for t in tools]}")
                else:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
            
            # Test MCP tools/call
            print("\n📂 Testing MCP tools/call (list_files)")
            mcp_request = {
                "jsonrpc": "2.0",
                "id": "test-2",
                "method": "tools/call",
                "params": {
                    "name": "list_files",
                    "arguments": {}
                }
            }
            response = await client.post(f"{base_url}/mcp", json=mcp_request)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                if "result" in result:
                    content = result["result"]["content"][0]["text"]
                    print(f"   Files: {content}")
                else:
                    print(f"   Error: {result.get('error', 'Unknown error')}")
            
            print("\n🎉 MCP HTTP API test completed successfully!")
            
        except httpx.ConnectError:
            print("❌ Cannot connect to MCP server at http://127.0.0.1:8000")
            print("   Please start the server with: python -m server.api_mcp.mcp_server")
        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_mcp_http_api())
