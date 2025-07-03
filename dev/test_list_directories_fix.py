#!/usr/bin/env python3
"""
Test rapido per verificare che il comando "list directories" funzioni.
"""

import sys
import os
import asyncio

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from pathlib import Path
from agent.core.secure_agent import SecureAgent

async def test_list_directories():
    """Test che il comando 'list directories' chiami il tool giusto."""
    
    print("🧪 TESTING 'list directories' COMMAND")
    print("=" * 45)
    
    # Setup agent
    workspace_path = "sandbox"  # Use string instead of Path
    agent = SecureAgent(workspace_path, debug_mode=True)
    
    # Test the specific command that was failing
    test_query = "list directories"
    
    print(f"\n📝 Sending query: '{test_query}'")
    print("-" * 30)
    
    try:
        response = await agent.process_query(test_query)
        
        print(f"\n✅ Response received:")
        print(f"   Success: {response.success}")
        print(f"   Response: {response.response[:200]}...")  # Use 'response' attribute
        print(f"   Tools used: {response.tools_used}")
        
        # Check if the right tool was used
        if "list_directories" in response.tools_used:
            print("\n🎯 SUCCESS: Used list_directories tool!")
        elif "list_files" in response.tools_used:
            print("\n⚠️  WARNING: Still using list_files instead of list_directories")
        else:
            print(f"\n❓ UNEXPECTED: Used tools {response.tools_used}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return False
    
    return True

if __name__ == "__main__":
    asyncio.run(test_list_directories())
