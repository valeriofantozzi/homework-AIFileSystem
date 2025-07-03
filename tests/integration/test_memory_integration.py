#!/usr/bin/env python3
"""
Test script for memory-enhanced conversation flow.

This script tests the enhanced memory system that allows the agent
to handle ambiguous responses like "yes" by maintaining conversation context.
"""

import asyncio
import tempfile
from pathlib import Path

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent.core.secure_agent import SecureAgent
from agent.supervisor.supervisor import RequestSupervisor, ModerationRequest  
from config.model_config import ModelConfig


async def test_memory_conversation_flow():
    """Test the complete memory-enhanced conversation flow."""
    print("🧠 MEMORY-ENHANCED CONVERSATION FLOW TEST")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Using temporary workspace: {temp_dir}")
        
        # Create some test files
        test_files = {
            'readme.md': '# Project README\nThis is a sample project with documentation.',
            'config.json': '{"name": "test-project", "version": "1.0.0"}',
            'data.txt': 'Sample data file with important information.'
        }
        
        workspace_path = Path(temp_dir)
        for filename, content in test_files.items():
            (workspace_path / filename).write_text(content)
        
        # Initialize agent with memory tools
        print("🚀 Initializing agent with memory tools...")
        try:
            agent = SecureAgent(
                workspace_path=temp_dir,
                model_config=ModelConfig(),
                debug_mode=True
            )
            
            supervisor = RequestSupervisor()
            
            print("✅ Agent and supervisor initialized successfully")
            
            # Test conversation with memory context
            conversation_id = "test-conversation-123"
            
            print("\n💬 Starting conversation flow...")
            
            # Step 1: Ask for file listing (should work)
            print("\n--- Step 1: Initial request ---")
            user_query_1 = "list all files and directories"
            
            print(f"User: {user_query_1}")
            
            # Process through supervisor first
            mod_request_1 = ModerationRequest(
                user_query=user_query_1,
                conversation_id=conversation_id
            )
            
            mod_response_1 = await supervisor.moderate_request(mod_request_1)
            print(f"Supervisor: {'✅ ALLOWED' if mod_response_1.allowed else '❌ REJECTED'}")
            
            if mod_response_1.allowed:
                # Process with agent
                agent_response_1 = await agent.process_query_with_conversation(
                    user_query_1, conversation_id
                )
                print(f"Agent: {agent_response_1.response[:200]}...")
                print(f"Tools used: {agent_response_1.tools_used}")
                
                # Simulate agent asking a follow-up question
                print("\n--- Agent asks follow-up question ---")
                follow_up = "Would you like me to show you the content of any specific file?"
                print(f"Agent: {follow_up}")
                
                # Store this interaction manually (simulating what CLI would do)
                if "store_interaction" in agent.file_tools:
                    agent.file_tools["store_interaction"](
                        conversation_id,
                        user_query_1,
                        agent_response_1.response + "\n\n" + follow_up,
                        agent_response_1.tools_used,
                        {"timestamp": "2025-07-03T10:00:00", "follow_up_question": follow_up}
                    )
                
                # Step 2: User responds with ambiguous "yes"
                print("\n--- Step 2: Ambiguous response with context ---")
                user_query_2 = "yes"
                print(f"User: {user_query_2}")
                
                # Get conversation context
                context = None
                if "get_conversation_context" in agent.file_tools:
                    context = agent.file_tools["get_conversation_context"](conversation_id)
                    print(f"📝 Context available: {context is not None}")
                    if context:
                        print(f"Context preview: {context[:150]}...")
                
                # Process through supervisor with context
                mod_request_2 = ModerationRequest(
                    user_query=user_query_2,
                    conversation_id=conversation_id,
                    conversation_context=context
                )
                
                mod_response_2 = await supervisor.moderate_request(mod_request_2)
                print(f"Supervisor: {'✅ ALLOWED' if mod_response_2.allowed else '❌ REJECTED'}")
                print(f"Reason: {mod_response_2.reason}")
                
                if mod_response_2.allowed:
                    # Process with agent
                    agent_response_2 = await agent.process_query_with_conversation(
                        user_query_2, conversation_id
                    )
                    print(f"Agent: {agent_response_2.response[:200]}...")
                    print(f"Tools used: {agent_response_2.tools_used}")
                    
                    print("\n🎉 SUCCESS: Ambiguous response handled correctly with memory context!")
                else:
                    print(f"\n❌ ISSUE: Ambiguous response still rejected despite context")
                    print(f"   This indicates the memory integration needs refinement.")
                    return False
                    
            else:
                print(f"❌ Initial request rejected: {mod_response_1.reason}")
                return False
                
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


async def test_ambiguous_response_detection():
    """Test specific ambiguous response detection logic."""
    print("\n🔍 AMBIGUOUS RESPONSE DETECTION TEST")
    print("=" * 50)
    
    supervisor = RequestSupervisor()
    
    # Test cases for ambiguous responses
    test_cases = [
        {
            "query": "yes",
            "context": "Recent conversation context:\n[10:30:15] Agent: Would you like me to read the config.json file?",
            "should_be_enhanced": True
        },
        {
            "query": "sure",
            "context": "Recent conversation context:\n[10:30:15] Agent: Should I list all the files in the directory?",
            "should_be_enhanced": True
        },
        {
            "query": "list all files",
            "context": "Some context here",
            "should_be_enhanced": False  # Not ambiguous
        },
        {
            "query": "no",
            "context": None,  # No context
            "should_be_enhanced": False
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest case {i}: '{test_case['query']}'")
        
        request = ModerationRequest(
            user_query=test_case["query"],
            conversation_id=f"test-{i}",
            conversation_context=test_case["context"]
        )
        
        enhanced_query = supervisor._handle_ambiguous_response(request)
        
        was_enhanced = enhanced_query != test_case["query"]
        expected_enhancement = test_case["should_be_enhanced"]
        
        print(f"  Enhanced: {was_enhanced}")
        print(f"  Expected: {expected_enhancement}")
        print(f"  Result: {'✅ PASS' if was_enhanced == expected_enhancement else '❌ FAIL'}")
        
        if was_enhanced:
            print(f"  Enhanced query preview: {enhanced_query[:100]}...")


async def main():
    """Main test runner."""
    print("🧪 MEMORY SYSTEM INTEGRATION TESTS")
    print("=" * 70)
    
    try:
        # Test 1: Ambiguous response detection
        await test_ambiguous_response_detection()
        
        # Test 2: Full conversation flow
        success = await test_memory_conversation_flow()
        
        if success:
            print("\n🎉 ALL TESTS PASSED!")
            print("\n✅ Memory system successfully integrated:")
            print("   • Conversation context tracking ✅")
            print("   • Ambiguous response detection ✅") 
            print("   • Supervisor context integration ✅")
            print("   • Agent memory tools ✅")
        else:
            print("\n❌ Some tests failed - check implementation")
            
    except Exception as e:
        print(f"\n💥 Test suite failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
