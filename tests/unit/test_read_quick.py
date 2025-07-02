#!/usr/bin/env python3
"""
Quick test for read functionality
"""

import sys
import asyncio
import tempfile
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent


async def test_read_functionality():
    """Test read functionality specifically."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary workspace: {temp_dir}")
        
        # Create a test file
        test_file = os.path.join(temp_dir, 'config.json')
        with open(test_file, 'w') as f:
            f.write('{"name": "test-project", "version": "1.0.0", "author": "AI Agent"}')
        
        print("Created test file")
        
        # Initialize agent
        agent = SecureAgent(temp_dir, debug_mode=True)
        print('✓ SecureAgent initialization successful')
        
        # Test read
        print("\nTesting read functionality...")
        response = await agent.process_query("Read the content of config.json")
        print(f"Response: {response.response}")
        print(f"Tools used: {response.tools_used}")
        
        if 'test-project' in response.response.lower():
            print('✅ Read functionality working!')
            return True
        else:
            print('❌ Read functionality failed')
            return False


if __name__ == "__main__":
    asyncio.run(test_read_functionality())
