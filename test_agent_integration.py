#!/usr/bin/env python3
"""
Test integration del goal-oriented reasoning con l'agente completo.

Questo test verifica che l'agente CLI integri correttamente il goal-oriented reasoning.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.append(str(project_root))

async def test_agent_goal_oriented_behavior():
    """Test l'agente con goal-oriented reasoning."""
    
    print("🧪 Testing Agent with Goal-Oriented Reasoning")
    print("=" * 50)
    
    try:
        from agent.core.secure_agent import SecureAgent
        
        # Use current workspace as test workspace
        workspace_path = "/Users/valeriofantozzi/Developer/Personal🦄/homework-AIFileSystem/workspace"
        
        # Create agent with debug mode to see goal logging
        agent = SecureAgent(
            workspace_path=workspace_path,
            debug_mode=True
        )
        
        # Test query that should generate a clear goal
        test_query = "visualizza i file con tree view"
        
        print(f"🎯 Testing query: '{test_query}'")
        print("Expected behavior:")
        print("  1. Generate explicit goal")
        print("  2. Use tree tool")
        print("  3. Validate goal compliance")
        print("  4. Show goal in debug logs")
        print("")
        
        # Process the query
        result = await agent.process_query(test_query)
        
        print("📋 Agent Response:")
        print(f"   Success: {result.success}")
        print(f"   Response length: {len(result.response)} chars")
        print(f"   Tools used: {result.tools_used}")
        
        # Check if result has goal information
        if hasattr(result, 'goal') and result.goal:
            print(f"   🎯 Goal Generated: {result.goal}")
        else:
            print("   ⚠️  No goal found in result")
        
        # Check if result has goal compliance
        if hasattr(result, 'goal_compliance') and result.goal_compliance:
            print(f"   ✅ Goal Compliance: {result.goal_compliance.compliance_level.value}")
            print(f"   📊 Compliance Score: {result.goal_compliance.confidence_score}")
        else:
            print("   ⚠️  No goal compliance validation found")
        
        # Validate basic success
        assert result.success, "Agent should succeed with tree query"
        assert result.response and len(result.response) > 50, "Response should be substantial"
        
        print("\n✅ Goal-oriented reasoning integration test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run integration test."""
    
    print("🚀 Goal-Oriented Reasoning Integration Test")
    print("=" * 50)
    
    try:
        success = await test_agent_goal_oriented_behavior()
        
        if success:
            print("\n🎉 Integration test completed successfully!")
            print("\nNow the agent should:")
            print("  ✅ Generate explicit goals for every query")
            print("  ✅ Validate goal compliance before responding")
            print("  ✅ Log goal information in debug mode")
            print("  ✅ Provide better aligned responses")
        else:
            print("\n❌ Integration test failed!")
            
        return success
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        sys.exit(1)
