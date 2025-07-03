#!/usr/bin/env python3
"""
Simple test for the translation method in ReAct loop.

Tests the _translate_to_english method directly without dependencies.
"""

import asyncio
import sys
from pathlib import Path

# Mock the imports that would cause dependency issues
sys.modules['psutil'] = type(sys)('mock_psutil')
sys.modules['agent.diagnostics'] = type(sys)('mock_diagnostics')

# Mock diagnostics function
def log_tool_usage(tool_name, tool_args):
    pass

# Add it to the mock module
sys.modules['agent.diagnostics'].log_tool_usage = log_tool_usage

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.react_loop import ReActLoop

# Mock LLM response function for testing
async def mock_llm_response(prompt: str) -> str:
    """Mock LLM response function that simulates translation."""
    # Simple translation rules for testing
    translations = {
        "lista tutti i file e cartelle": "list all files and folders",
        "mostra il contenuto del file": "show the file content", 
        "trova il file più grande": "find the largest file",
        "crea un nuovo file": "create a new file",
        "leggi il file readme": "read the readme file"
    }
    
    prompt_lower = prompt.lower()
    for italian, english in translations.items():
        if italian in prompt_lower:
            return english
    
    # If no translation found, check if it's a translation prompt
    if "translate" in prompt_lower and '"' in prompt:
        # Extract the text between quotes
        query_start = prompt.find('"') + 1
        query_end = prompt.rfind('"')
        if query_start > 0 and query_end > query_start:
            original_text = prompt[query_start:query_end]
            # Check if it's in our translation dictionary
            for italian, english in translations.items():
                if italian == original_text.lower():
                    return english
            # If not found, return original (assuming it's English)
            return original_text
    
    return "list files"  # default fallback

async def test_translation_method():
    """Test the translation method directly."""
    
    print("🧪 Testing Translation Method")
    print("=" * 40)
    
    # Create minimal ReAct loop instance
    react_loop = ReActLoop(
        model_provider=None,  # Not used for translation test
        tools={},  # Not used for translation test
        llm_response_func=mock_llm_response
    )
    
    # Test cases
    test_cases = [
        ("lista tutti i file e cartelle", True),  # Italian -> should translate
        ("list all files and folders", False),   # English -> should not translate
        ("trova il file più grande", True),      # Italian -> should translate
        ("create a new file", False),            # English -> should not translate
        ("leggi il file readme", True),          # Italian -> should translate
    ]
    
    for i, (query, should_translate) in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: '{query}'")
        
        translated, original = await react_loop._translate_to_english(query)
        
        print(f"   Original: '{original}'")
        print(f"   Translated: '{translated}'")
        
        was_translated = (translated != original)
        
        if should_translate:
            if was_translated:
                print(f"   ✅ Correctly translated")
            else:
                print(f"   ❌ Expected translation but got none")
        else:
            if not was_translated:
                print(f"   ✅ Correctly unchanged")
            else:
                print(f"   ⚠️ Unexpected translation occurred")
    
    print("\n" + "=" * 40)
    print("🎯 Translation Test Summary:")
    print("- Italian queries should be translated to English")
    print("- English queries should remain unchanged")
    print("- Translation improves tool selection accuracy")

if __name__ == "__main__":
    asyncio.run(test_translation_method())
