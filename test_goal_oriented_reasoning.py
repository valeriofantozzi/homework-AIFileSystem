#!/usr/bin/env python3
"""
Test script per verificare il goal-oriented reasoning del ReAct loop.

Questo test valida che l'agente:
1. Generi obiettivi espliciti per ogni query
2. Verifichi la compliance della risposta con l'obiettivo
3. Registri i goal nel debug logging
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from agent.core.react_loop import ConsolidatedReActResponse, ReActLoop, ReActResult
from agent.core.goal_validator import GoalComplianceValidator, ComplianceLevel


def test_goal_oriented_response_parsing():
    """Test che il parsing JSON estragga correttamente goal e goal_compliance_check."""
    
    print("🧪 Testing Goal-Oriented Response Parsing")
    print("=" * 50)
    
    # Test case con goal e compliance check
    test_json = '''
    {
      "thinking": "The user wants to see files in tree format. I need to use the tree tool to display the hierarchical structure.",
      "goal": "Display workspace file and directory structure in tree format",
      "tool_name": "tree",
      "tool_args": {},
      "continue_reasoning": false,
      "final_response": "Ecco la struttura ad albero del workspace: [tree output]",
      "goal_compliance_check": "Response successfully displays hierarchical tree structure as requested, showing all files and folders in organized format",
      "confidence": 0.95
    }
    '''
    
    try:
        response = ConsolidatedReActResponse.from_json_string(test_json)
        
        print("✅ JSON parsing successful!")
        print(f"   Goal: {response.goal}")
        print(f"   Tool: {response.tool_name}")
        print(f"   Compliance Check: {response.goal_compliance_check}")
        print(f"   Continue Reasoning: {response.continue_reasoning}")
        
        # Validate that goal fields are extracted
        assert response.goal is not None, "Goal should be extracted"
        assert response.goal_compliance_check is not None, "Goal compliance check should be extracted"
        assert "tree format" in response.goal.lower(), "Goal should mention tree format"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in goal-oriented parsing: {e}")
        return False


def test_goal_compliance_validator():
    """Test del GoalComplianceValidator."""
    
    print("\n🧪 Testing Goal Compliance Validator")
    print("=" * 50)
    
    try:
        # Test case: tree view request
        goal = "Display workspace file and directory structure in tree format"
        response = "Ecco la struttura ad albero completa del workspace:\n├── file1.txt\n├── folder1/\n│   └── subfolder/\n└── README.md"
        tools_used = ["tree"]
        
        result = GoalComplianceValidator.validate_compliance(
            goal=goal,
            response=response,
            tools_used=tools_used
        )
        
        print(f"✅ Goal compliance validation successful!")
        print(f"   Compliance Level: {result.compliance_level.value}")
        print(f"   Confidence Score: {result.confidence_score}")
        print(f"   Explanation: {result.explanation}")
        print(f"   Is Compliant: {result.is_compliant}")
        
        # Validate results
        assert result.is_compliant, "Tree response should be compliant with tree goal"
        assert result.confidence_score > 0.7, "Confidence should be high for clear match"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in goal compliance validation: {e}")
        return False


def test_default_goal_generation():
    """Test della generazione di goal di default."""
    
    print("\n🧪 Testing Default Goal Generation")
    print("=" * 50)
    
    try:
        # Mock ReActLoop instance per testare _generate_default_goal
        react_loop = ReActLoop.__new__(ReActLoop)  # Create without __init__
        
        test_cases = [
            ("visualizza i file con tree view", "tree format"),
            ("list all files", "list all files"),
            ("describe hello.py", "read and analyze"),
            ("mostra cartelle", "directories"),
            ("unknown command", "fulfill user request")
        ]
        
        for query, expected_keyword in test_cases:
            goal = react_loop._generate_default_goal(query)
            print(f"   Query: '{query}'")
            print(f"   Generated Goal: '{goal}'")
            
            # Validate goal contains expected keyword
            assert expected_keyword.lower() in goal.lower(), f"Goal should contain '{expected_keyword}'"
            print(f"   ✅ Contains expected keyword: '{expected_keyword}'")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in default goal generation: {e}")
        return False


def test_malformed_json_goal_extraction():
    """Test dell'estrazione goal da JSON malformato."""
    
    print("\n🧪 Testing Malformed JSON Goal Extraction")
    print("=" * 50)
    
    # JSON malformato che contiene goal e compliance check
    malformed_json = '''
    {
      "thinking": "I need to help with the request",
      "goal": "Display all files in the workspace",
      // This is a malformed comment
      "tool_name": "list_files"
      "goal_compliance_check": "Response shows all files as requested"
      // Missing comma above intentionally
    }
    '''
    
    try:
        response = ConsolidatedReActResponse.from_json_string(malformed_json)
        
        print("✅ Malformed JSON handled gracefully!")
        print(f"   Extracted Goal: {response.goal}")
        print(f"   Extracted Compliance Check: {response.goal_compliance_check}")
        print(f"   Extracted Tool: {response.tool_name}")
        
        # Validate fallback extraction worked
        assert response.goal is not None, "Goal should be extracted even from malformed JSON"
        assert "files" in response.goal.lower(), "Goal should mention files"
        
        return True
        
    except Exception as e:
        print(f"❌ Error in malformed JSON goal extraction: {e}")
        return False


async def main():
    """Run all goal-oriented reasoning tests."""
    
    print("🚀 Goal-Oriented Reasoning Implementation Test Suite")
    print("=" * 60)
    
    tests = [
        test_goal_oriented_response_parsing,
        test_goal_compliance_validator, 
        test_default_goal_generation,
        test_malformed_json_goal_extraction
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
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
        print("\n🎉 All tests passed! Goal-oriented reasoning is working correctly.")
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
