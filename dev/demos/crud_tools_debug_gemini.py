#!/usr/bin/env python3
"""
Simple test script to debug Gemini CLI adapter issues.
"""

import asyncio
import tempfile
import os
from pathlib import Path

from workspace_fs import Workspace
from crud_tools.gemini_adapter import GeminiCLIAdapter


async def test_gemini_adapter():
    """Test the GeminiCLIAdapter directly."""
    print("=== Testing GeminiCLIAdapter ===")
    
    try:
        adapter = GeminiCLIAdapter()
        print(f"✓ Adapter created successfully")
        
        # Test simple query
        print("--- Testing simple query ---")
        response = await adapter.query("What is 2+2? Just give the number.")
        print(f"Response: {response}")
        
        # Test with file analysis
        print("--- Testing file analysis ---")
        test_files = {
            "example.py": "def hello():\n    print('Hello, world!')\n",
            "data.txt": "This is some test data."
        }
        
        response2 = await adapter.analyze_files(
            test_files, 
            "What programming language is used in these files?"
        )
        print(f"Analysis response: {response2}")
        
    except Exception as e:
        print(f"✗ Error: {e}")


async def test_gemini_cli_direct():
    """Test the Gemini CLI directly with file input."""
    print("\n=== Testing Gemini CLI direct file input ===")
    
    # Create a temporary file with a prompt
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("What is the capital of France? Give a one-word answer.")
        tmp_path = tmp_file.name
    
    try:
        import subprocess
        cmd = ["gemini", "--prompt", f"@{tmp_path}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Direct CLI test successful: {result.stdout.strip()}")
        else:
            print(f"✗ Direct CLI test failed: {result.stderr}")
            
    finally:
        Path(tmp_path).unlink(missing_ok=True)


async def test_workspace_integration():
    """Test the workspace integration with a smaller context."""
    print("\n=== Testing Workspace Integration ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        # Create simple test files
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        fs_tools.write_file("hello.py", "print('Hello, world!')")
        fs_tools.write_file("readme.txt", "This is a simple test project.")
        
        # Test with reduced content limits
        from crud_tools.gemini_adapter import create_gemini_question_tool
        
        question_tool = create_gemini_question_tool(
            workspace,
            max_files=2,
            max_content_per_file=100,  # Very small limit
            gemini_model="gemini-2.5-pro"
        )
        
        response = await question_tool("What files are in this project?")
        print(f"✓ Workspace integration successful: {response[:200]}...")
        
    except Exception as e:
        print(f"✗ Workspace integration error: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def main():
    """Run all tests."""
    await test_gemini_cli_direct()
    await test_gemini_adapter()
    await test_workspace_integration()


if __name__ == "__main__":
    asyncio.run(main())
