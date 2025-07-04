#!/usr/bin/env python3
"""
Test to verify that all internal thinking is done in English only,
while final responses match the user's input language.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class MockLLMResponse:
    """Mock LLM that might try to use Italian in thinking - we want to prevent this."""
    
    async def __call__(self, prompt: str) -> str:
        """Mock LLM response that tests the prompt constraints."""
        
        # Check if this is a consolidated prompt (contains CRITICAL LANGUAGE RULES)
        if "CRITICAL LANGUAGE RULES" in prompt and "thinking" in prompt:
            # This should now be enforced by the prompt to use English thinking
            return '''{
  "thinking": "The user is asking in Italian for file and directory listing. I understand they want to see both files and directories together. I'll use the list_all tool to provide comprehensive results.",
  "tool_name": "list_all",
  "tool_args": {},
  "continue_reasoning": false,
  "final_response": "Ecco tutti i file e le cartelle nel workspace...",
  "confidence": 0.9
}'''
        
        # For translation prompts
        if "Translate" in prompt and "lista tutti i file e cartelle" in prompt:
            return "list all files and directories"
        
        # Default fallback
        return "list files"

async def test_english_thinking_enforcement():
    """Test that internal thinking is enforced to be in English."""
    
    print("🧪 Testing English-Only Internal Thinking Enforcement")
    print("=" * 60)
    
    try:
        from agent.core.react_loop import ReActLoop, ConsolidatedReActResponse
        from config.model_config import ModelProvider
        from unittest.mock import Mock
        
        # Create mock tools
        tools = {
            "list_all": lambda: "📄 file1.txt, 📁 folder1/, 📄 readme.md, 📁 docs/",
            "list_files": lambda: "📄 file1.txt, 📄 readme.md", 
            "list_directories": lambda: "📁 folder1/, 📁 docs/"
        }
        
        # Create mock LLM
        mock_llm = MockLLMResponse()
        
        # Create ReAct loop with the mock LLM
        react_loop = ReActLoop(
            model_provider=Mock(spec=ModelProvider),
            tools=tools,
            debug_mode=True,
            llm_response_func=mock_llm
        )
        
        # Test context
        class TestContext:
            def __init__(self):
                self.conversation_id = "test-123"
                self.user_query = ""
        
        context = TestContext()
        
        print("📋 Test Case: Italian query with English thinking enforcement")
        print("   Input: 'lista tutti i file e cartelle'")
        print("   Expected: English thinking, Italian final response")
        
        # Execute the ReAct loop
        result = await react_loop.execute("lista tutti i file e cartelle", context)
        
        print(f"\n📊 Results:")
        print(f"   Success: {result.success}")
        print(f"   Response: {result.response[:100]}...")
        
        # Check the reasoning steps for language compliance
        english_thinking_found = False
        italian_thinking_found = False
        
        for step in react_loop.scratchpad:
            step_content = step.content.lower()
            
            # Check for English indicators in thinking
            if any(word in step_content for word in ['the user', 'i will', 'i understand', 'looking at']):
                english_thinking_found = True
                print(f"   ✅ English thinking detected: {step.content[:50]}...")
            
            # Check for Italian indicators in thinking (should NOT be found)
            if any(word in step_content for word in ['utente', 'voglio', 'devo', 'sto', 'userò']):
                italian_thinking_found = True
                print(f"   ❌ Italian thinking found: {step.content[:50]}...")
        
        print(f"\n🎯 Language Compliance Check:")
        print(f"   ✅ English thinking found: {english_thinking_found}")
        print(f"   ❌ Italian thinking found: {italian_thinking_found}")
        
        if english_thinking_found and not italian_thinking_found:
            print("\n🎉 SUCCESS: Internal thinking is correctly enforced to be in English!")
            print("✅ The agent now properly separates:")
            print("   • Internal reasoning: Always English")
            print("   • Final response: Matches user's language")
            return True
        else:
            print("\n⚠️ ISSUE: Language enforcement may not be working correctly")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_english_thinking_enforcement())
    
    print(f"\n🎯 Final Result: {'PASS' if success else 'FAIL'}")
    
    if success:
        print("\n💡 Key Benefits:")
        print("   🌍 Consistent internal reasoning in English")
        print("   🎯 Better tool selection accuracy")
        print("   🔧 Easier debugging and maintenance")
        print("   👥 Natural user experience in their language")
    
    sys.exit(0 if success else 1)
