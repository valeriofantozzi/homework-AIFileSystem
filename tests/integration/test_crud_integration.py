#!/usr/bin/env python3
"""
Test script for the CRUD tools with both mock and real LLM backends.

This script demonstrates the question answering functionality using:
1. Mock LLM (for unit                print(f"Error (expected without API key): {        print(f"Files after delete: {files_final}")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(workspace.root)               
        finally:
            # Cleanup  
            import shutil
            shutil.rmtree(workspace.root)ng)
2. Gemini CLI (for local testing)
3. Pydantic-AI with remote APIs (if configured)
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Dict, Any

from workspace_fs import Workspace
from crud_tools.gemini_adapter import create_gemini_question_tool
from crud_tools.question_tool import create_question_tool_function


def create_test_workspace() -> Workspace:
    """Create a temporary workspace with test files."""
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    # Create test files
    test_files = {
        "main.py": '''
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def main():
    """Main function to demonstrate Fibonacci calculation."""
    for i in range(10):
        print(f"F({i}) = {calculate_fibonacci(i)}")

if __name__ == "__main__":
    main()
''',
        "utils.py": '''
import math
from typing import List

def is_prime(n: int) -> bool:
    """Check if a number is prime."""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def get_primes(limit: int) -> List[int]:
    """Get all prime numbers up to the limit."""
    return [i for i in range(2, limit + 1) if is_prime(i)]

def factorial(n: int) -> int:
    """Calculate factorial of n."""
    if n <= 1:
        return 1
    return n * factorial(n - 1)
''',
        "README.md": '''# Test Project

This is a test project for demonstrating the CRUD tools functionality.

## Features

- Fibonacci number calculation
- Prime number utilities
- Factorial calculation

## Files

- `main.py`: Main application with Fibonacci calculator
- `utils.py`: Utility functions for mathematical operations
- `README.md`: This documentation file

## Usage

Run the main script to see Fibonacci numbers:

```bash
python main.py
```
''',
        "config.json": '''
{
    "app_name": "MathUtils",
    "version": "1.0.0",
    "features": {
        "fibonacci": true,
        "primes": true,
        "factorial": true
    },
    "limits": {
        "max_fibonacci": 50,
        "max_prime_search": 1000
    }
}
'''
    }
    
    # Write test files
    for filename, content in test_files.items():
        file_path = Path(temp_dir) / filename
        file_path.write_text(content.strip())
    
    print(f"Created test workspace at: {temp_dir}")
    return workspace


async def test_gemini_cli_integration():
    """Test the Gemini CLI integration."""
    print("\n" + "="*60)
    print("TESTING GEMINI CLI INTEGRATION")
    print("="*60)
    
    workspace = create_test_workspace()
    
    try:
        # Create Gemini CLI question tool
        gemini_tool = create_gemini_question_tool(workspace)
        
        test_questions = [
            "What programming language are these files written in?",
            "What mathematical functions are implemented in this codebase?",
            "How does the Fibonacci calculation work?",
            "What is the purpose of the utils.py file?",
            "What are the configuration options available?",
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- Question {i} ---")
            print(f"Q: {question}")
            print("A: ", end="")
            
            try:
                answer = await gemini_tool(question)
                print(answer)
            except Exception as e:
                print(f"Error: {e}")
                
    except Exception as e:
        print(f"Gemini CLI integration failed: {e}")
        print("Make sure Gemini CLI is installed and configured.")
    
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(workspace.root)


async def test_pydantic_ai_integration():
    """Test the pydantic-ai integration (if available)."""
    print("\n" + "="*60)
    print("TESTING PYDANTIC-AI INTEGRATION")
    print("="*60)
    
    try:
        from crud_tools.question_tool import answer_question_about_files, PYDANTIC_AI_AVAILABLE
        
        if not PYDANTIC_AI_AVAILABLE:
            print("Pydantic-AI not available. Skipping this test.")
            return
        
        workspace = create_test_workspace()
        
        try:
            # Test with a simple question
            question = "What is this codebase about?"
            print(f"\nQ: {question}")
            print("A: ", end="")
            
            # Note: This would require API keys to work with real models
            # For testing, we'll use a mock model or catch the error
            try:
                answer = await answer_question_about_files(
                    workspace, 
                    question,
                    llm_model="openai:gpt-4o-mini"  # This would need API key
                )
                print(answer)
            except Exception as e:
                print(f"Error (expected without API key): {e}")
                
        finally:
            # Cleanup  
            import shutil
            shutil.rmtree(workspace.root)
            
    except ImportError:
        print("Pydantic-AI not available. Install with: pip install pydantic-ai")


def test_crud_tools_basic():
    """Test basic CRUD operations."""
    print("\n" + "="*60)
    print("TESTING BASIC CRUD OPERATIONS")
    print("="*60)
    
    from crud_tools.tools import create_file_tools
    
    workspace = create_test_workspace()
    
    try:
        # Create CRUD tools
        tools = create_file_tools(workspace)
        
        # Test list files
        print("\n--- Testing list_files ---")
        files = tools['list_files']()
        print(f"Found {len(files)} files:")
        for file in files:
            print(f"  - {file}")
        
        # Test read file
        print("\n--- Testing read_file ---")
        content = tools['read_file']("main.py")
        print(f"main.py content (first 200 chars):\n{content[:200]}...")
        
        # Test write file
        print("\n--- Testing write_file ---")
        test_content = "# This is a test file\nprint('Hello, World!')\n"
        tools['write_file']("test.py", test_content)
        print("Created test.py")
        
        # Verify the file was created
        files_after = tools['list_files']()
        print(f"Files after write: {files_after}")
        
        # Test delete file
        print("\n--- Testing delete_file ---")
        tools['delete_file']("test.py")
        print("Deleted test.py")
        
        # Verify the file was deleted
        files_final = tools['list_files']()
        print(f"Files after delete: {files_final}")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(workspace.root)


async def main():
    """Run all tests."""
    print("CRUD TOOLS TESTING SUITE")
    print("="*60)
    
    # Test basic CRUD operations
    test_crud_tools_basic()
    
    # Test Gemini CLI integration
    await test_gemini_cli_integration()
    
    # Test pydantic-ai integration
    await test_pydantic_ai_integration()
    
    print("\n" + "="*60)
    print("ALL TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
