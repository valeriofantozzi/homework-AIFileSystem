#!/usr/bin/env python3
"""
Test script for Phase 2 - Task 1 implementation
"""

import sys
import asyncio
import tempfile
import os
from pathlib import Path
import pytest

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent


@pytest.mark.asyncio
async def test_agent():
    """Test the SecureAgent implementation."""
    try:
        print("=" * 60)
        print("Testing Phase 2 - Task 1: SecureAgent Implementation")
        print("=" * 60)
        
        # Test with a real workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary workspace: {temp_dir}")
            
            # Create some test files
            test_files = {
                'readme.txt': 'This is a README file with project information.',
                'config.json': '{"name": "test-project", "version": "1.0.0"}',
                'data.txt': 'Sample data file\nLine 2\nLine 3'
            }
            
            for filename, content in test_files.items():
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
            
            print(f"Created {len(test_files)} test files")
            
            # Initialize agent
            agent = SecureAgent(temp_dir, debug_mode=True)
            print('✓ SecureAgent initialization successful')
            print(f'Available tools: {agent.get_available_tools()}')
            
            # Test cases
            test_queries = [
                "List all files in the workspace",
                "Read the content of readme.txt",
                "What files are available and what do they contain?",
                "Read the newest file in the workspace"
            ]
            
            for i, query in enumerate(test_queries, 1):
                print(f"\n--- Test {i}: {query} ---")
                try:
                    response = await agent.process_query(query)
                    print(f"Success: {response.success}")
                    print(f"Tools used: {response.tools_used}")
                    print(f"Response: {response.response}")
                    
                    if response.reasoning_steps:
                        print("Reasoning steps:")
                        for step in response.reasoning_steps:
                            print(f"  {step['phase']}: {step['content'][:100]}...")
                        
                except Exception as e:
                    print(f"✗ Query failed: {e}")
                    import traceback
                    traceback.print_exc()
            
            print("\n" + "=" * 60)
            print("Phase 2 - Task 1 Testing Complete")
            print("=" * 60)
                
    except Exception as e:
        print(f'✗ Error: {e}')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_agent())
