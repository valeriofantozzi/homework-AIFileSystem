#!/usr/bin/env python3
"""
Test script to verify API key fallback behavior.

This script demonstrates the enhanced fallback logic when API keys are missing.
"""

import asyncio
import os
import tempfile
from pathlib import Path

from workspace_fs import Workspace
from crud_tools.question_tool import answer_question_about_files


async def test_gemini_api_key_fallback():
    """Test fallback behavior when Gemini API key is missing."""
    print("=== Testing Gemini API Key Fallback ===")
    
    # Create temporary workspace
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        # Create test file
        test_file = Path(temp_dir) / "example.py"
        test_file.write_text("""
def hello_world():
    '''Simple greeting function.'''
    return "Hello, World!"

def add_numbers(a, b):
    '''Add two numbers together.'''
    return a + b

if __name__ == "__main__":
    print(hello_world())
    print(f"2 + 3 = {add_numbers(2, 3)}")
""")
        
        print(f"Created test workspace: {temp_dir}")
        print(f"Test file content preview: {test_file.read_text()[:100]}...")
        
        # Test with explicit Gemini model (will likely fail due to missing API key)
        print("\n--- Testing with explicit Gemini model ---")
        try:
            result = await answer_question_about_files(
                workspace=workspace,
                query="What functions are defined in this Python code?",
                llm_model="gemini:gemini-2.5-pro",  # This will likely fail
                max_files=5
            )
            print(f"✅ Gemini result: {result}")
        except Exception as e:
            print(f"❌ Gemini failed as expected: {e}")
        
        # Test fallback to OpenAI (if available)
        print("\n--- Testing fallback to OpenAI ---")
        try:
            result = await answer_question_about_files(
                workspace=workspace,
                query="What functions are defined in this Python code?",
                llm_model="openai:gpt-4o-mini",
                max_files=5
            )
            print(f"✅ OpenAI result: {result}")
        except Exception as e:
            print(f"❌ OpenAI also failed: {e}")
        
        # Test automatic fallback when configuration fails
        print("\n--- Testing with role-based configuration (may trigger fallback) ---")
        try:
            result = await answer_question_about_files(
                workspace=workspace,
                query="What functions are defined in this Python code?",
                role="file_analysis",  # Will use configuration system
                max_files=5
            )
            print(f"✅ Configuration-based result: {result}")
        except Exception as e:
            print(f"❌ Configuration-based failed: {e}")
            
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir)
        print(f"\n🧹 Cleaned up temporary workspace: {temp_dir}")


async def test_api_key_detection():
    """Test API key detection logic."""
    print("\n=== Testing API Key Detection ===")
    
    # Check what API keys are available
    api_keys = {
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
        "GEMINI_API_KEY": bool(os.getenv("GEMINI_API_KEY")),
        "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
        "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
    }
    
    print("Available API keys:")
    for key, available in api_keys.items():
        status = "✅ Available" if available else "❌ Missing"
        print(f"  {key}: {status}")
    
    if not any(api_keys.values()):
        print("\n⚠️  No API keys found. The question tool will need local models or CLI tools.")
    elif api_keys["OPENAI_API_KEY"]:
        print("\n✅ OpenAI available - can be used as fallback.")
    elif api_keys["GEMINI_API_KEY"]:
        print("\n✅ Gemini available - should work directly.")
    else:
        print("\n⚠️  Only non-OpenAI keys available - fallback may be limited.")


async def main():
    """Run all tests."""
    await test_api_key_detection()
    await test_gemini_api_key_fallback()


if __name__ == "__main__":
    asyncio.run(main())
