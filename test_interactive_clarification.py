#!/usr/bin/env python3
"""
Test script per verificare l'Interactive Goal Clarification.

Questo test valida che l'agente:
1. Riconosca quando una richiesta è ambigua o incompleta
2. Generi domande di chiarimento appropriate
3. Formatti le domande in modo user-friendly
4. Gestisca correttamente il flusso di clarification
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from agent.core.react_loop import ConsolidatedReActResponse, ReActLoop


def test_clarification_response_parsing():
    """Test che il parsing JSON estragga correttamente clarification_question."""
    
    print("🧪 Testing Clarification Response Parsing")
    print("=" * 50)
    
    # Test case con clarification request
    test_json = '''
    {
      "thinking": "The user's request is very vague - they just said 'help'. I need to ask what specific task they need help with.",
      "goal": "Request clarification for user's help request",
      "tool_name": null,
      "tool_args": {},
      "continue_reasoning": false,
      "final_response": null,
      "goal_compliance_check": null,
      "clarification_question": "What specific task would you like help with? I can help you list files, read files, create files, delete files, or answer questions about your workspace contents.",
      "confidence": 0.8
    }
    '''
    
    try:
        response = ConsolidatedReActResponse.from_json_string(test_json)
        
        print("✅ JSON parsing successful!")
        print(f"   Goal: {response.goal}")
        print(f"   Tool: {response.tool_name}")
        print(f"   Clarification Question: {response.clarification_question}")
        print(f"   Continue Reasoning: {response.continue_reasoning}")
        
        # Validate that clarification fields are extracted
        assert response.clarification_question is not None, "Clarification should be extracted"
        assert response.tool_name is None, "Tool should be null when asking for clarification"
        assert response.continue_reasoning is False, "Should not continue reasoning when asking for clarification"
        assert "help with" in response.clarification_question.lower(), "Clarification should ask for help details"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in clarification parsing: {e}")
        return False


def test_clarification_formatting():
    """Test della formattazione delle richieste di chiarimento."""
    
    print("\n🧪 Testing Clarification Formatting")
    print("=" * 50)
    
    try:
        # Mock ReActLoop instance per testare _format_clarification_response
        react_loop = ReActLoop.__new__(ReActLoop)  # Create without __init__
        
        test_cases = [
            {
                "clarification": "Which file would you like me to read?",
                "goal": "Read a file for the user",
                "query": "read file",
                "expected_elements": ["clarification needed", "which file", "read file"]
            },
            {
                "clarification": "What specific task would you like help with?",
                "goal": "Help the user with a task",
                "query": "help",
                "expected_elements": ["clarification needed", "specific task", "help"]
            },
            {
                "clarification": "Could you specify which file you want to delete?",
                "goal": "Delete a file safely",
                "query": "delete something",
                "expected_elements": ["clarification needed", "specify", "delete"]
            }
        ]
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n   Test Case {i}:")
            print(f"   Query: '{case['query']}'")
            print(f"   Clarification: '{case['clarification']}'")
            
            formatted = react_loop._format_clarification_response(
                case["clarification"],
                case["goal"],
                case["query"]
            )
            
            print(f"   Formatted Response:\n{formatted}")
            
            # Validate formatting elements
            formatted_lower = formatted.lower()
            for element in case["expected_elements"]:
                assert element in formatted_lower, f"Should contain '{element}'"
                print(f"   ✅ Contains: '{element}'")
            
            # Check for proper formatting elements
            assert "❓" in formatted, "Should have clarification emoji"
            assert "💡" in formatted, "Should have context section"
            assert "📝" in formatted, "Should have original request section"
            assert "💬" in formatted, "Should have help section"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in clarification formatting: {e}")
        return False


def test_ambiguous_goal_detection():
    """Test della rilevazione di richieste ambigue."""
    
    print("\n🧪 Testing Ambiguous Goal Detection")
    print("=" * 50)
    
    try:
        # Mock ReActLoop instance per testare _generate_default_goal
        react_loop = ReActLoop.__new__(ReActLoop)  # Create without __init__
        
        ambiguous_cases = [
            ("help", "AMBIGUOUS_REQUEST"),
            ("what can you do", "AMBIGUOUS_REQUEST"),
            ("do something", "AMBIGUOUS_REQUEST"),
            ("hi", "AMBIGUOUS_REQUEST"),
            ("read file", "NEEDS_FILE_SPECIFICATION"),
            ("delete something", "NEEDS_FILE_SPECIFICATION"),
            ("create file", "NEEDS_FILE_SPECIFICATION")
        ]
        
        clear_cases = [
            ("list files", "List all files in the workspace"),
            ("show tree view", "Display workspace file and directory structure in tree format"),
            ("read hello.py", "Read and analyze the specified file content"),
            ("create README.md", "Create or write content to a file")
        ]
        
        print("   Testing Ambiguous Cases:")
        for query, expected in ambiguous_cases:
            goal = react_loop._generate_default_goal(query)
            print(f"   '{query}' → {goal}")
            assert goal == expected, f"Expected {expected}, got {goal}"
            print(f"   ✅ Correctly detected as {expected}")
        
        print("\n   Testing Clear Cases:")
        for query, expected in clear_cases:
            goal = react_loop._generate_default_goal(query)
            print(f"   '{query}' → {goal}")
            assert expected.lower() in goal.lower(), f"Goal should contain elements of {expected}"
            print(f"   ✅ Generated clear goal")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in ambiguous goal detection: {e}")
        return False


def test_malformed_json_clarification_extraction():
    """Test dell'estrazione clarification da JSON malformato."""
    
    print("\n🧪 Testing Malformed JSON Clarification Extraction")
    print("=" * 50)
    
    # JSON malformato che contiene clarification
    malformed_json = '''
    {
      "thinking": "The request is unclear",
      "goal": "Request clarification from user",
      // Comment that breaks JSON
      "tool_name": null,
      "clarification_question": "Could you please specify what you want to do?"
      // Missing comma above
    }
    '''
    
    try:
        response = ConsolidatedReActResponse.from_json_string(malformed_json)
        
        print("✅ Malformed JSON handled gracefully!")
        print(f"   Extracted Goal: {response.goal}")
        print(f"   Extracted Clarification: {response.clarification_question}")
        
        # Validate fallback extraction worked
        assert response.clarification_question is not None, "Clarification should be extracted even from malformed JSON"
        assert "specify" in response.clarification_question.lower(), "Clarification should ask for specification"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in malformed JSON clarification extraction: {e}")
        return False


async def test_end_to_end_clarification_flow():
    """Test completo del flusso di clarification."""
    
    print("\n🧪 Testing End-to-End Clarification Flow")
    print("=" * 50)
    
    try:
        # Mock LLM che richiede clarification per richieste ambigue
        async def mock_clarification_llm(prompt: str) -> str:
            if "help" in prompt.lower() and "COMMON CLARIFICATION SCENARIOS" in prompt:
                return '''
                {
                  "thinking": "The user just said 'help' which is very vague. I need to ask what specific task they want help with to provide useful assistance.",
                  "goal": "Request clarification for vague help request",
                  "tool_name": null,
                  "tool_args": {},
                  "continue_reasoning": false,
                  "final_response": null,
                  "goal_compliance_check": null,
                  "clarification_question": "What specific task would you like help with? I can help you list files, read files, create files, delete files, or answer questions about your workspace contents.",
                  "confidence": 0.9
                }
                '''
            
            # Default response
            return '''
            {
              "thinking": "I understand the request clearly.",
              "goal": "Help the user with their request",
              "tool_name": "list_all",
              "tool_args": {},
              "continue_reasoning": false,
              "final_response": "I can help you with that.",
              "confidence": 0.8
            }
            '''
        
        # Create ReAct loop with clarification support
        react_loop = ReActLoop(
            model_provider=None,
            tools={},  # Empty tools for this test
            max_iterations=3,
            debug_mode=True,
            llm_response_func=mock_clarification_llm
        )
        
        # Test context
        class MockContext:
            def __init__(self):
                self.conversation_id = "test-clarification"
                self.user_query = "help"
                self.workspace_path = "/test"
        
        context = MockContext()
        
        print(f"   Testing ambiguous query: '{context.user_query}'")
        print("   Expected: Agent should ask for clarification")
        
        # Execute the query
        result = await react_loop.execute(context.user_query, context)
        
        print(f"\n   📋 Result:")
        print(f"   Success: {result.success}")
        print(f"   Response: {result.response}")
        
        # Validate clarification response
        response = result.response
        is_clarification = (
            response and
            ("clarification needed" in response.lower() or "❓" in response) and
            ("specific task" in response.lower() or "what" in response.lower()) and
            len(response) > 50
        )
        
        if is_clarification:
            print("   ✅ SUCCESS: Agent correctly requested clarification!")
            print("   ✅ Response contains clarification elements")
            print("   ✅ Response is user-friendly")
            return True
        else:
            print("   ❌ ISSUE: Agent didn't request clarification properly")
            print(f"   Contains clarification markers: {'❓' in (response or '')}")
            print(f"   Asks for specifics: {'what' in (response or '').lower()}")
            return False
            
    except Exception as e:
        print(f"❌ End-to-end test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all interactive goal clarification tests."""
    
    print("🚀 Interactive Goal Clarification Implementation Test Suite")
    print("=" * 70)
    
    tests = [
        test_clarification_response_parsing,
        test_clarification_formatting,
        test_ambiguous_goal_detection,
        test_malformed_json_clarification_extraction,
        test_end_to_end_clarification_flow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
                
            if result:
                passed += 1
                print("✅ PASSED\n")
            else:
                failed += 1
                print("❌ FAILED\n")
        except Exception as e:
            failed += 1
            print(f"❌ FAILED with exception: {e}\n")
    
    print("📊 Test Results Summary")
    print("=" * 30)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success Rate: {passed/(passed+failed)*100:.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed! Interactive Goal Clarification is working correctly.")
        print("\nNow the agent can:")
        print("  ✅ Detect ambiguous or unclear requests")
        print("  ✅ Ask appropriate clarification questions")
        print("  ✅ Format clarification requests user-friendly")
        print("  ✅ Handle the clarification flow properly")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please review implementation.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        sys.exit(1)
