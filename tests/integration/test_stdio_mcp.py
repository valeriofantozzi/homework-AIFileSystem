#!/usr/bin/env python3
"""
Test script for stdio MCP server functionality.

This script tests the stdio-based MCP server to ensure proper
VSCode integration and protocol compliance over stdin/stdout.
"""

import json
import subprocess
import sys
import time
from pathlib import Path


def test_stdio_mcp_server():
    """Test the stdio MCP server with proper JSON-RPC communication."""
    
    print("🧪 Testing Stdio MCP Server")
    print("=" * 50)
    
    # Docker command to start stdio server
    docker_cmd = [
        "docker", "run", "--rm", "-i", 
        "--name", "ai-filesystem-stdio-test",
        "-v", f"{Path.cwd()}:/app/workspace",
        "-e", "WORKSPACE_PATH=/app/workspace",
        "-e", "PYTHONPATH=/app",
        "ai-filesystem-mcp:latest",
        "python", "server/stdio_mcp_server.py"
    ]
    
    try:
        # Start the stdio server process
        print("🔄 Starting stdio MCP server...")
        process = subprocess.Popen(
            docker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0
        )
        
        # Test initialize request (critical for VSCode)
        print("📤 Sending initialize request...")
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send request and get response
        process.stdin.write(json.dumps(initialize_request) + "\n")
        process.stdin.flush()
        
        # Read response (may have multiple lines due to logging)
        response_line = None
        for _ in range(10):  # Try to read up to 10 lines to find JSON response
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith('{"jsonrpc"'):
                response_line = line
                break
        
        if not response_line:
            print("❌ No JSON-RPC response received")
            return False
        
        try:
            response = json.loads(response_line.strip())
            print(f"📨 Initialize response: {json.dumps(response, indent=2)}")
            
            # Validate initialize response
            if (response.get("jsonrpc") == "2.0" and
                response.get("id") == 1 and
                "result" in response):
                
                result = response["result"]
                if (result.get("protocolVersion") == "2024-11-05" and
                    "capabilities" in result and
                    "serverInfo" in result):
                    print("✅ Initialize request successful!")
                else:
                    print("❌ Invalid initialize response structure")
                    return False
            else:
                print("❌ Invalid JSON-RPC response")
                return False
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            return False
        
        # Test tools/list request
        print("\n📤 Sending tools/list request...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        process.stdin.write(json.dumps(tools_request) + "\n")
        process.stdin.flush()
        
        # Read response (may have multiple lines due to logging)
        response_line = None
        for _ in range(10):  # Try to read up to 10 lines to find JSON response
            line = process.stdout.readline()
            if not line:
                break
            line = line.strip()
            if line.startswith('{"jsonrpc"'):
                response_line = line
                break
        
        if response_line:
            try:
                response = json.loads(response_line.strip())
                if (response.get("jsonrpc") == "2.0" and
                    response.get("id") == 2 and
                    "result" in response and
                    "tools" in response["result"]):
                    tools_count = len(response["result"]["tools"])
                    print(f"✅ Tools list successful! Found {tools_count} tools")
                else:
                    print("❌ Invalid tools/list response")
                    return False
            except json.JSONDecodeError as e:
                print(f"❌ Tools response JSON error: {e}")
                return False
        else:
            print("❌ No tools/list response received")
            return False
        
        print("\n🎉 All stdio MCP tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False
        
    finally:
        # Clean up process
        try:
            process.terminate()
            process.wait(timeout=5)
        except:
            process.kill()


if __name__ == "__main__":
    success = test_stdio_mcp_server()
    sys.exit(0 if success else 1)
