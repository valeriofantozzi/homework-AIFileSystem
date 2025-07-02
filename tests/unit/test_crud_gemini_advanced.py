#!/usr/bin/env python3
"""
Advanced testing script for our custom Gemini CLI adapter.

This script tests edge cases, performance, and different scenarios
for our custom file analysis mechanism.
"""

import asyncio
import tempfile
import time
from pathlib import Path

from workspace_fs import Workspace
from crud_tools.gemini_adapter import GeminiCLIAdapter, create_gemini_question_tool


async def test_large_files():
    """Test with larger files to check performance and truncation."""
    print("=== Testing Large Files ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create a large Python file
        large_code = """
def fibonacci_sequence(n):
    '''Generate Fibonacci sequence up to n terms.'''
    sequence = []
    a, b = 0, 1
    for i in range(n):
        sequence.append(a)
        a, b = b, a + b
    return sequence

def prime_numbers(limit):
    '''Find all prime numbers up to limit using Sieve of Eratosthenes.'''
    if limit < 2:
        return []
    
    sieve = [True] * (limit + 1)
    sieve[0] = sieve[1] = False
    
    for i in range(2, int(limit**0.5) + 1):
        if sieve[i]:
            for j in range(i*i, limit + 1, i):
                sieve[j] = False
    
    return [i for i in range(2, limit + 1) if sieve[i]]

class MathUtils:
    '''Utility class for mathematical operations.'''
    
    @staticmethod
    def factorial(n):
        '''Calculate factorial of n.'''
        if n < 0:
            raise ValueError("Factorial is not defined for negative numbers")
        if n == 0 or n == 1:
            return 1
        result = 1
        for i in range(2, n + 1):
            result *= i
        return result
    
    @staticmethod
    def gcd(a, b):
        '''Calculate Greatest Common Divisor using Euclidean algorithm.'''
        while b:
            a, b = b, a % b
        return a
    
    @staticmethod
    def lcm(a, b):
        '''Calculate Least Common Multiple.'''
        return abs(a * b) // MathUtils.gcd(a, b)

""" * 10  # Repeat 10 times to make it large
        
        fs_tools.write_file("large_math.py", large_code)
        fs_tools.write_file("config.json", '{"max_iterations": 1000, "algorithms": ["fibonacci", "prime", "factorial"]}')
        
        # Test with size limits
        question_tool = create_gemini_question_tool(
            workspace,
            max_files=5,
            max_content_per_file=1000,  # Small limit to test truncation
            gemini_model="gemini-2.5-pro"
        )
        
        start_time = time.time()
        response = await question_tool("What mathematical algorithms are implemented in this codebase?")
        end_time = time.time()
        
        print(f"✓ Large file test completed in {end_time - start_time:.2f}s")
        print(f"Response: {response[:200]}...")
        
    except Exception as e:
        print(f"✗ Large file test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def test_mixed_file_types():
    """Test with different file types and formats."""
    print("\n=== Testing Mixed File Types ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create various file types
        files = {
            "app.py": """
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True)
""",
            "requirements.txt": """
flask==2.3.0
requests==2.31.0
pytest==7.4.0
""",
            "README.md": """
# My Flask Application

This is a simple Flask web application with health check endpoint.

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Run: `python app.py`
""",
            "config.yaml": """
server:
  host: localhost
  port: 5000
  debug: true

database:
  url: sqlite:///app.db
  echo: false
""",
            ".env": """
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///production.db
DEBUG=false
"""
        }
        
        for filename, content in files.items():
            fs_tools.write_file(filename, content)
        
        question_tool = create_gemini_question_tool(workspace)
        
        questions = [
            "What type of application is this?",
            "What are the main dependencies?",
            "How do I run this application?",
            "What configuration options are available?"
        ]
        
        for question in questions:
            try:
                response = await question_tool(question)
                print(f"Q: {question}")
                print(f"A: {response[:150]}...\n")
            except Exception as e:
                print(f"Q: {question}")
                print(f"✗ Error: {e}\n")
        
    except Exception as e:
        print(f"✗ Mixed file types test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def test_error_handling():
    """Test error handling with problematic files."""
    print("=== Testing Error Handling ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create files with potential issues
        fs_tools.write_file("valid.py", "print('Hello, world!')")
        fs_tools.write_file("empty.txt", "")
        
        # Create a file with special characters
        fs_tools.write_file("unicode.py", """
# File with unicode characters
def greet():
    return "Hello 🌍 World! αβγ"

data = {"emoji": "🚀", "greek": "αβγδε"}
""")
        
        question_tool = create_gemini_question_tool(workspace)
        
        # Test with various edge case questions
        edge_questions = [
            "What files exist in this project?",
            "Are there any empty files?",
            "What unicode characters are used?",
            "What happens if I ask about non-existent functionality?"
        ]
        
        for question in edge_questions:
            try:
                response = await question_tool(question)
                print(f"✓ Q: {question}")
                print(f"  A: {response[:100]}...\n")
            except Exception as e:
                print(f"✗ Q: {question}")
                print(f"  Error: {e}\n")
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def test_performance_metrics():
    """Test performance with multiple queries."""
    print("=== Testing Performance Metrics ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create a realistic project structure
        fs_tools.write_file("main.py", "from utils import helper\nprint(helper.greet())")
        fs_tools.write_file("utils.py", "def greet(): return 'Hello from utils!'")
        fs_tools.write_file("tests.py", "import unittest\nclass TestUtils(unittest.TestCase): pass")
        
        question_tool = create_gemini_question_tool(workspace)
        
        # Multiple quick queries
        quick_questions = [
            "How many files?",
            "What is main.py?",
            "Any tests?",
            "What imports?",
            "Overall purpose?"
        ]
        
        print("Running performance test...")
        start_time = time.time()
        
        for i, question in enumerate(quick_questions):
            query_start = time.time()
            response = await question_tool(question)
            query_end = time.time()
            
            print(f"{i+1}. {question} ({query_end - query_start:.2f}s)")
            print(f"   {response[:80]}...")
        
        total_time = time.time() - start_time
        print(f"\n✓ Performance test completed in {total_time:.2f}s")
        print(f"Average per query: {total_time / len(quick_questions):.2f}s")
        
    except Exception as e:
        print(f"✗ Performance test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def main():
    """Run all advanced tests."""
    print("ADVANCED GEMINI ADAPTER TESTING")
    print("=" * 60)
    
    await test_large_files()
    await test_mixed_file_types()
    await test_error_handling()
    await test_performance_metrics()
    
    print("\n" + "=" * 60)
    print("ALL ADVANCED TESTS COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
