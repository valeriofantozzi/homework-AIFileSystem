#!/usr/bin/env python3
"""
Simple test script to verify SecureAgent implementation.

This script creates a test workspace and demonstrates basic agent functionality.
"""

import asyncio
import os
import tempfile
from pathlib import Path
import pytest

# Add the project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent
from config.model_config import ModelConfig


@pytest.mark.asyncio
async def test_basic_agent():
    """Test basic agent functionality with a temporary workspace."""
    
    # Create temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created test workspace: {temp_dir}")
        
        # Create some test files
        test_file_path = Path(temp_dir) / "test.txt"
        test_file_path.write_text("Hello, this is a test file!")
        
        another_file_path = Path(temp_dir) / "data.txt"
        another_file_path.write_text("Some important data here.")
        
        print("Created test files")
        
        try:
            # Initialize agent
            print("Initializing SecureAgent...")
            agent = SecureAgent(
                workspace_path=temp_dir,
                debug_mode=True
            )
            
            print("Agent initialized successfully!")
            print(f"Workspace info: {agent.get_workspace_info()}")
            
            # Test queries
            test_queries = [
                "What files are in the workspace?",
                "Read the content of test.txt",
                "List all files"
            ]
            
            for query in test_queries:
                print(f"\n--- Testing query: {query} ---")
                try:
                    response = await agent.process_query(query)
                    print(f"Success: {response.success}")
                    print(f"Response: {response.response}")
                    print(f"Tools used: {response.tools_used}")
                    if response.reasoning_steps:
                        print("Reasoning steps:")
                        for step in response.reasoning_steps:
                            print(f"  {step['phase']}: {step['content']}")
                    
                except Exception as e:
                    print(f"Error processing query: {e}")
                    
        except Exception as e:
            print(f"Error initializing agent: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    print("Starting SecureAgent test...")
    asyncio.run(test_basic_agent())
    print("Test completed!")
