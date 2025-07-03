#!/usr/bin/env python3
"""
Test script per simulare il comando 'list directories' nell'agent.
"""

import sys
import os
import asyncio

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

async def test_list_directories_command():
    """Test del comando 'list directories' nell'agent."""
    
    print("🧪 TESTING 'list directories' in Agent")
    print("=" * 45)
    
    try:
        # Add the specific agent path to avoid conflicts
        agent_path = os.path.join(project_root, 'agent')
        sys.path.insert(0, agent_path)
        
        from core.secure_agent import SecureAgent
        from config.model_config import ModelConfig
        
        # Initialize agent
        model_config = ModelConfig()
        agent = SecureAgent(
            workspace_path="sandbox",
            model_config=model_config,
            debug_mode=True
        )
        
        print("✅ Agent initialized successfully")
        print(f"Available tools: {list(agent.file_tools.keys())}")
        
        # Test the command
        query = "list directories"
        print(f"\n🔍 Testing query: '{query}'")
        
        response = await agent.process_query(query)
        
        print("\n📋 Agent Response:")
        print(f"Response: {response.response}")
        print(f"Tools used: {response.tools_used}")
        print(f"Success: {response.success}")
        
        if response.reasoning_steps:
            print(f"\n🧠 Reasoning steps:")
            for i, step in enumerate(response.reasoning_steps, 1):
                print(f"  {i}. {step}")
        
        return response.success
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_list_directories_command())
        print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)
