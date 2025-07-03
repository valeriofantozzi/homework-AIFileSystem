#!/usr/bin/env python3
"""
Test script to verify MCP initialize handler functionality.

This script tests the MCP protocol initialize method to ensure proper
VSCode integration and protocol compliance.
"""

import json
import requests
import sys


def test_mcp_initialize():
    """Test the MCP initialize method endpoint."""
    
    # MCP server endpoint
    url = "http://localhost:8000/mcp"
    
    # Initialize request following MCP protocol
    initialize_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "VSCode MCP Client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        # Send initialize request
        print("🔄 Testing MCP initialize handler...")
        response = requests.post(
            url,
            json=initialize_request,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # Check HTTP status
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
        
        # Parse JSON response
        result = response.json()
        print(f"📨 Server response: {json.dumps(result, indent=2)}")
        
        # Validate MCP response structure
        if result.get("jsonrpc") != "2.0":
            print("❌ Invalid JSON-RPC version")
            return False
        
        if result.get("id") != 1:
            print("❌ Mismatched request ID")
            return False
        
        if "error" in result and result["error"] is not None:
            print(f"❌ Server error: {result['error']}")
            return False
        
        if "result" not in result:
            print("❌ Missing result field")
            return False
        
        # Validate initialize response content
        initialize_result = result["result"]
        
        # Check protocol version
        if initialize_result.get("protocolVersion") != "2024-11-05":
            print("❌ Invalid protocol version in response")
            return False
        
        # Check capabilities structure
        capabilities = initialize_result.get("capabilities")
        if not isinstance(capabilities, dict):
            print("❌ Invalid capabilities structure")
            return False
        
        if "tools" not in capabilities:
            print("❌ Missing tools capability")
            return False
        
        if "resources" not in capabilities:
            print("❌ Missing resources capability")
            return False
        
        # Check server info
        server_info = initialize_result.get("serverInfo")
        if not isinstance(server_info, dict):
            print("❌ Invalid serverInfo structure")
            return False
        
        if server_info.get("name") != "AI FileSystem MCP Server":
            print("❌ Incorrect server name")
            return False
        
        if server_info.get("version") != "1.0.0":
            print("❌ Incorrect server version")
            return False
        
        print("✅ MCP initialize handler test passed!")
        print("📋 Response validation:")
        print(f"   ✓ Protocol version: {initialize_result['protocolVersion']}")
        print(f"   ✓ Server name: {server_info['name']}")
        print(f"   ✓ Server version: {server_info['version']}")
        print(f"   ✓ Capabilities: tools={type(capabilities['tools']).__name__}, resources={type(capabilities['resources']).__name__}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_health_endpoint():
    """Test the health endpoint for good measure."""
    
    try:
        print("\n🔄 Testing health endpoint...")
        response = requests.get("http://localhost:8000/health", timeout=5)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health check passed: {health_data.get('status')}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False


if __name__ == "__main__":
    print("🧪 MCP Initialize Handler Test Suite")
    print("=" * 50)
    
    # Test initialize handler
    initialize_success = test_mcp_initialize()
    
    # Test health endpoint 
    health_success = test_health_endpoint()
    
    print("\n" + "=" * 50)
    if initialize_success and health_success:
        print("🎉 All tests passed! MCP server is ready for VSCode integration.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check server configuration.")
        sys.exit(1)
