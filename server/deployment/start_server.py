#!/usr/bin/env python3
"""
Production-ready MCP server startup script.

This script provides a clean interface for starting the MCP server
with proper configuration, health checks, and monitoring.
"""

import asyncio
import os
import sys
import signal
import logging
from pathlib import Path
from typing import Optional

import uvicorn
from uvicorn.config import LOGGING_CONFIG

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from server.api_mcp.mcp_server import app

# Configure structured logging
LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOGGING_CONFIG["formatters"]["access"]["fmt"] = '%(asctime)s [%(levelname)s] %(client_addr)s - "%(request_line)s" %(status_code)s'

logger = logging.getLogger(__name__)


class MCPServerRunner:
    """
    Production MCP server runner with lifecycle management.
    
    Handles graceful startup/shutdown, health monitoring, and
    configuration management for containerized deployments.
    """
    
    def __init__(self):
        self.server: Optional[uvicorn.Server] = None
        self.should_exit = False
    
    def setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.should_exit = True
            if self.server:
                self.server.should_exit = True
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def get_config(self) -> dict:
        """Get server configuration from environment variables."""
        return {
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", "8000")),
            "workers": int(os.getenv("WORKERS", "1")),
            "log_level": os.getenv("LOG_LEVEL", "info"),
            "access_log": os.getenv("ACCESS_LOG", "true").lower() == "true",
            "workspace_path": os.getenv("WORKSPACE_PATH", str(project_root / "workspace"))
        }
    
    async def health_check(self) -> bool:
        """Perform startup health check."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8000/health", timeout=5.0)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def run(self) -> None:
        """Run the MCP server with production configuration."""
        self.setup_signal_handlers()
        config = self.get_config()
        
        logger.info("Starting AI File System MCP Server")
        logger.info(f"Configuration: {config}")
        
        # Ensure workspace directory exists
        workspace_path = Path(config["workspace_path"])
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Workspace directory: {workspace_path}")
        
        # Create uvicorn server
        uvicorn_config = uvicorn.Config(
            app=app,
            host=config["host"],
            port=config["port"],
            workers=config["workers"],
            log_level=config["log_level"],
            access_log=config["access_log"],
            loop="asyncio"
        )
        
        self.server = uvicorn.Server(uvicorn_config)
        
        try:
            # Run server
            asyncio.run(self.server.serve())
        except KeyboardInterrupt:
            logger.info("Server interrupted by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)
        finally:
            logger.info("MCP server shutdown complete")


def main():
    """Main entry point for production deployment."""
    runner = MCPServerRunner()
    runner.run()


if __name__ == "__main__":
    main()
