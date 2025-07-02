#!/usr/bin/env python3
"""
Quick test to demonstrate the enhanced tool chaining for 'largest file' queries.
"""

import asyncio
import tempfile
import time
from pathlib import Path

from agent.core.secure_agent import SecureAgent


async def test_largest_file_chaining():
    """Test the multi-step tool chaining for 'largest file' queries."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created test workspace: {temp_dir}")
        
        # Create test files of different sizes
        test_files = {
            "small.txt": "Small file content.",  # ~20 bytes
            "medium.txt": "This is a medium-sized file with more content than the small one.",  # ~70 bytes
            "large.txt": "This is a much larger file containing more content. " * 5,  # ~250 bytes
        }
        
        for filename, content in test_files.items():
            filepath = Path(temp_dir) / filename
            filepath.write_text(content)
            time.sleep(0.01)  # Ensure different modification times
        
        # Initialize the agent
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        print("\n=== Testing 'Largest File' Query ===")
        
        # Test the enhanced tool chaining
        query = "What files are available and what's in the largest one?"
        print(f"Query: {query}")
        
        response = await agent.process_query(query)
        
        print(f"\nSuccess: {response.success}")
        print(f"Tools used: {response.tools_used}")
        print(f"Response:\n{response.response}")
        
        # Verify the expected tool chain
        expected_tools = ["list_files", "find_largest_file", "read_file"]
        assert response.tools_used == expected_tools, f"Expected {expected_tools}, got {response.tools_used}"
        
        # Verify the largest file was found and read
        assert "large.txt" in response.response, "Should mention the largest file"
        assert "larger file containing more content" in response.response, "Should show content of largest file"
        
        print("✅ Multi-step tool chaining for 'largest file' works correctly!")


if __name__ == "__main__":
    asyncio.run(test_largest_file_chaining())
