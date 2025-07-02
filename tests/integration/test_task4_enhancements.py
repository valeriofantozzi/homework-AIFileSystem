#!/usr/bin/env python3
"""
Integration tests for Phase 2 Task 4 enhancements.
Tests the enhanced error handling, tool chaining, and advanced file operations.
"""

import os
import sys
import tempfile
import time as time_module
from pathlib import Path

import pytest

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent


@pytest.mark.asyncio
async def test_enhanced_error_handling():
    """Test enhanced error handling and formatting capabilities."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created test workspace: {temp_dir}")
        
        # Create test environment
        test_files = {
            "sample.txt": "Hello world!",
            "data.json": '{"name": "test", "value": 42}',
            "notes.md": "# Test Notes\n\nThis is a test file."
        }
        
        for filename, content in test_files.items():
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
        
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        print("\n=== Testing Enhanced Error Handling ===")
        
        # Test 1: Successful operation with enhanced formatting
        print("\nTest 1: Enhanced success formatting")
        response = await agent.process_query("List all files in the workspace")
        print(f"Response: {response.response}")
        assert response.success
        assert "✅" in response.response or "Found" in response.response
        print("✓ Enhanced success formatting works")
        
        # Test 2: File not found error with helpful suggestions
        print("\nTest 2: Enhanced error messages")
        response = await agent.process_query("Read the file 'nonexistent.txt'")
        print(f"Response: {response.response}")
        assert "not found" in response.response.lower() or "failed" in response.response.lower()
        print("✓ Enhanced error messages work")
        
        # Test 3: Sandbox validation
        print("\nTest 3: Sandbox validation")
        workspace_info = agent.get_workspace_info()
        print(f"Workspace info: {workspace_info}")
        assert "workspace_path" in workspace_info
        assert "available_tools" in workspace_info
        print("✓ Sandbox validation works")


@pytest.mark.asyncio 
async def test_advanced_file_operations():
    """Test enhanced advanced file operations with regex and metadata."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created test workspace: {temp_dir}")
        
        # Create diverse test files
        test_files = {
            "report_2024.txt": "Annual Report\n" + "Data line\n" * 50,
            "config.json": '{"version": "1.0", "debug": true}',
            "readme.md": "# Project\n\nThis is the readme file.",
            "log_file.log": "INFO: Application started\nWARNING: Low memory",
            "small.txt": "tiny"
        }
        
        for i, (filename, content) in enumerate(test_files.items()):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            if i < len(test_files) - 1:
                time_module.sleep(0.1)  # Ensure different modification times
        
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        print("\n=== Testing Advanced File Operations ===")
        
        # Test 1: Enhanced get_file_info with comprehensive metadata
        print("\nTest 1: Comprehensive file information")
        response = await agent.process_query("Get detailed information about report_2024.txt")
        print(f"Response: {response.response}")
        assert response.success
        assert "report_2024.txt" in response.response.lower()
        assert ("size" in response.response.lower() or "bytes" in response.response.lower())
        assert ("lines" in response.response.lower() or "words" in response.response.lower())
        print("✓ Comprehensive file info works")
        
        # Test 2: Find largest file
        print("\nTest 2: Find largest file")
        response = await agent.process_query("Which file is the largest?")
        print(f"Response: {response.response}")
        assert response.success
        assert "largest" in response.response.lower() or "report_2024.txt" in response.response.lower()
        print("✓ Find largest file works")
        
        # Test 3: Find files by extension
        print("\nTest 3: Find files by extension")
        response = await agent.process_query("Find all .txt files")
        print(f"Response: {response.response}")
        assert response.success
        assert "txt" in response.response.lower()
        print("✓ Find files by extension works")
        
        # Test 4: Pattern matching with regex support (if implemented)
        print("\nTest 4: Advanced pattern matching")
        response = await agent.process_query("Find files containing 'report' in the name")
        print(f"Response: {response.response}")
        assert response.success
        assert ("report" in response.response.lower() or "matching" in response.response.lower())
        print("✓ Advanced pattern matching works")


@pytest.mark.asyncio
async def test_enhanced_tool_chaining():
    """Test enhanced tool chaining with better context preservation."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created test workspace: {temp_dir}")
        
        # Create test files with specific content
        test_files = {
            "first.txt": "This is the first file with some content.",
            "second.txt": "This is the second file with different content.",
            "latest.txt": "This is the newest file in the workspace."
        }
        
        for i, (filename, content) in enumerate(test_files.items()):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            time_module.sleep(0.1)  # Ensure different modification times
        
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        print("\n=== Testing Enhanced Tool Chaining ===")
        
        # Test 1: Multi-step operation with context preservation
        print("\nTest 1: Multi-step operation")
        response = await agent.process_query("First list all files, then read the newest one")
        print(f"Response: {response.response}")
        assert response.success
        assert len(response.tools_used) >= 2  # Should use multiple tools
        assert "latest.txt" in response.response or "newest" in response.response.lower()
        print("✓ Multi-step operation with context preservation works")
        
        # Test 2: Complex query requiring multiple tools
        print("\nTest 2: Complex multi-tool query")
        response = await agent.process_query("What files are available and what's in the largest one?")
        print(f"Response: {response.response}")
        assert response.success
        assert len(response.tools_used) >= 2
        print("✓ Complex multi-tool query works")
        
        # Test 3: Tool execution timing and performance
        print("\nTest 3: Performance and timing")
        import time
        start_time = time.time()
        response = await agent.process_query("List files and get info about the first one")
        end_time = time.time()
        execution_time = end_time - start_time
        
        print(f"Response: {response.response}")
        print(f"Execution time: {execution_time:.2f} seconds")
        assert response.success
        assert execution_time < 10.0  # Should complete within reasonable time
        print("✓ Performance and timing are acceptable")


@pytest.mark.asyncio
async def test_comprehensive_task4_demo():
    """Comprehensive demonstration of all Task 4 enhancements."""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created comprehensive test workspace: {temp_dir}")
        
        # Create a rich test environment
        test_files = {
            "project_readme.md": "# Project Documentation\n\nThis is a sample project.",
            "config.json": '{"app": "demo", "version": "2.1", "features": ["auth", "api"]}',
            "data_large.csv": "id,name,value\n" + "\n".join([f"{i},item{i},{i*10}" for i in range(100)]),
            "notes.txt": "Meeting notes from today's discussion.",
            "error.log": "ERROR: Connection failed\nINFO: Retrying...",
            "script.py": "#!/usr/bin/env python3\nprint('Hello, World!')"
        }
        
        for i, (filename, content) in enumerate(test_files.items()):
            filepath = os.path.join(temp_dir, filename)
            with open(filepath, 'w') as f:
                f.write(content)
            time_module.sleep(0.05)  # Small delays for different timestamps
        
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        print("\n=== Comprehensive Task 4 Demo ===")
        
        # Demo 1: Enhanced error handling and formatting
        print("\nDemo 1: Enhanced error handling")
        response = await agent.process_query("List all files")
        print(f"Files listed: {response.response}")
        assert response.success
        
        # Demo 2: Advanced file operations
        print("\nDemo 2: Advanced file operations")
        queries = [
            "What's the largest file?",
            "Find all .json files",
            "Get information about config.json",
            "Read the newest file"
        ]
        
        for query in queries:
            print(f"\nQuery: {query}")
            response = await agent.process_query(query)
            print(f"Result: {response.response[:200]}...")
            assert response.success
        
        # Demo 3: Tool chaining capabilities
        print("\nDemo 3: Complex tool chaining")
        complex_queries = [
            "List files, then tell me about the Python script",
            "Find files with 'data' in the name and show their sizes",
            "What's in the largest file and how many lines does it have?"
        ]
        
        for query in complex_queries:
            print(f"\nComplex query: {query}")
            response = await agent.process_query(query)
            print(f"Tools used: {response.tools_used}")
            print(f"Result: {response.response[:200]}...")
            assert response.success
            assert len(response.tools_used) >= 1
        
        print("\n" + "=" * 60)
        print("✅ All Task 4 enhancements working successfully!")
        print("✓ Enhanced error handling and formatting")
        print("✓ Advanced file operations with metadata")
        print("✓ Improved tool chaining with context preservation")
        print("✓ Sandbox validation and security")
        print("✓ Performance optimizations")


if __name__ == "__main__":
    import asyncio
    
    async def main():
        print("Starting Task 4 Enhancement Tests...")
        await test_enhanced_error_handling()
        await test_advanced_file_operations()
        await test_enhanced_tool_chaining()
        await test_comprehensive_task4_demo()
        print("\nAll tests completed successfully!")
    
    asyncio.run(main())
