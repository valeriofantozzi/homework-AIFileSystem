#!/usr/bin/env python3
"""
Health check script for MCP server monitoring.

Used by Docker health checks and external monitoring systems
to verify server availability and functionality.
"""

import asyncio
import json
import sys
import time
from typing import Dict, Any

import httpx


class MCPHealthChecker:
    """
    Comprehensive health checker for MCP server.
    
    Performs multiple health checks including API availability,
    tool functionality, and response time monitoring.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.timeout = 10.0
    
    async def check_basic_health(self) -> Dict[str, Any]:
        """Check basic server health endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=self.timeout
                )
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code,
                    "response": response.json() if response.status_code == 200 else None
                }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    async def check_mcp_tools(self) -> Dict[str, Any]:
        """Check MCP tools/list endpoint functionality."""
        async with httpx.AsyncClient() as client:
            try:
                mcp_request = {
                    "jsonrpc": "2.0",
                    "id": "health-check",
                    "method": "tools/list"
                }
                
                response = await client.post(
                    f"{self.base_url}/mcp",
                    json=mcp_request,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if "result" in result:
                        tools = result["result"]["tools"]
                        return {
                            "status": "healthy",
                            "tools_count": len(tools),
                            "tools": [t["name"] for t in tools]
                        }
                
                return {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "response": response.text
                }
                
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "error": str(e)
                }
    
    async def check_response_time(self) -> Dict[str, Any]:
        """Check server response time performance."""
        start_time = time.time()
        health_result = await self.check_basic_health()
        response_time = time.time() - start_time
        
        return {
            "response_time_ms": round(response_time * 1000, 2),
            "performance": "good" if response_time < 1.0 else "slow",
            "health_status": health_result["status"]
        }
    
    async def comprehensive_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        results = {}
        
        # Run all checks concurrently
        health_task = self.check_basic_health()
        tools_task = self.check_mcp_tools()
        performance_task = self.check_response_time()
        
        results["health"] = await health_task
        results["tools"] = await tools_task
        results["performance"] = await performance_task
        
        # Overall status
        all_healthy = all(
            check.get("status") == "healthy" 
            for check in [results["health"], results["tools"]]
        )
        
        results["overall"] = {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": time.time(),
            "checks_passed": sum(1 for check in [results["health"], results["tools"]] 
                                if check.get("status") == "healthy"),
            "total_checks": 2
        }
        
        return results


async def main():
    """Main health check entry point."""
    checker = MCPHealthChecker()
    
    # Determine check type from command line args
    check_type = sys.argv[1] if len(sys.argv) > 1 else "basic"
    
    try:
        if check_type == "basic":
            result = await checker.check_basic_health()
        elif check_type == "tools":
            result = await checker.check_mcp_tools()
        elif check_type == "performance":
            result = await checker.check_response_time()
        elif check_type == "comprehensive":
            result = await checker.comprehensive_check()
        else:
            result = await checker.check_basic_health()
        
        # Output results
        print(json.dumps(result, indent=2))
        
        # Exit with appropriate code
        if result.get("status") == "healthy" or result.get("overall", {}).get("status") == "healthy":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(json.dumps({"status": "unhealthy", "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
