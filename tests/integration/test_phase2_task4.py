#!/usr/bin/env python3
"""
Test script for Phase 2 - Task 4: Integrate File System Tools
Tests all file system tool integration, tool chaining, and advanced operations.
"""

import sys
import asyncio
import tempfile
import os
import time as time_module
from pathlib import Path
# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.core.secure_agent import SecureAgent


async def test_task4_file_system_integration():
    """Test comprehensive file system tool integration."""
    try:
        print("=" * 60)
        print("Testing Phase 2 - Task 4: File System Tool Integration")
        print("=" * 60)
        
        # Test with a real workspace
        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"Using temporary workspace: {temp_dir}")
            
            # Create test files with different timestamps
            test_files = {
                'readme.txt': 'This is a README file with project information.',
                'config.json': '{"name": "test-project", "version": "1.0.0", "author": "AI Agent"}',
                'data.txt': 'Sample data file\nLine 2\nLine 3\nImportant data here',
                'old_log.txt': 'Old log entry from yesterday',
                'notes_meeting.txt': 'Meeting notes from project discussion'
            }
            
            # Create files with slight delays to ensure different timestamps
            for i, (filename, content) in enumerate(test_files.items()):
                filepath = os.path.join(temp_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                if i < len(test_files) - 1:  # Small delay except for last file
                    time_module.sleep(0.1)
            
            print(f"Created {len(test_files)} test files")
            
            # Initialize agent
            agent = SecureAgent(temp_dir, debug_mode=True)
            print('✓ SecureAgent initialization successful')
            
            # Test 4.1: Verify all required tools are connected
            print("\n--- Test 4.1: Tool Registration ---")
            available_tools = agent.get_available_tools()
            print(f'Available tools: {available_tools}')
            
            required_tools = [
                'list_files', 'read_file', 'write_file', 'delete_file', 
                'answer_question_about_files'
            ]
            advanced_tools = [
                'read_newest_file', 'find_files_by_pattern', 'get_file_info'
            ]
            
            for tool in required_tools:
                assert tool in available_tools, f"Required tool '{tool}' not found"
                print(f'✓ {tool} - registered')
            
            for tool in advanced_tools:
                assert tool in available_tools, f"Advanced tool '{tool}' not found"
                print(f'✓ {tool} - registered')
            
            print('✓ All required tools are properly registered')
            
            # Test 4.2: Tool Chaining - Complex multi-step operations
            print("\n--- Test 4.2: Tool Chaining ---")
            
            # Test case 1: Find newest file and read its content
            print("\nTest case 1: Read newest file content")
            response = await agent.process_query("What's in the newest file?")
            print(f"Response: {response.response}")
            assert response.success, "Failed to process newest file query"
            assert 'notes_meeting.txt' in response.response.lower() or 'meeting' in response.response.lower()
            print('✓ Successfully chained list_files → read_file')
            
            # Test case 2: Search pattern and analyze content
            print("\nTest case 2: Find files with pattern and analyze")
            response = await agent.process_query("Find all files with 'config' in the name and tell me what they contain")
            print(f"Response: {response.response}")
            assert response.success, "Failed to process pattern search query"
            assert 'config.json' in response.response.lower()
            assert 'test-project' in response.response.lower()
            print('✓ Successfully chained find_files_by_pattern → read_file')
            
            # Test case 3: Complex analysis with multiple tools
            print("\nTest case 3: Complex multi-tool analysis")
            response = await agent.process_query("How many files are there, what's the newest one, and what does it contain?")
            print(f"Response: {response.response}")
            assert response.success, "Failed to process complex query"
            assert '5' in response.response or 'five' in response.response.lower()
            print('✓ Successfully used multiple tools in sequence')
            
            # Test 4.3: Advanced File Operations
            print("\n--- Test 4.3: Advanced Operations ---")
            
            # Test read_newest_file directly
            print("\nTesting read_newest_file()")
            response = await agent.process_query("Use the read_newest_file function to show me the latest content")
            print(f"Response: {response.response}")
            assert response.success, "Failed to use read_newest_file"
            print('✓ read_newest_file works correctly')
            
            # Test find_files_by_pattern
            print("\nTesting find_files_by_pattern()")
            response = await agent.process_query("Find all files containing 'txt' in their name")
            print(f"Response: {response.response}")
            assert response.success, "Failed to find files by pattern"
            assert 'readme.txt' in response.response.lower()
            print('✓ find_files_by_pattern works correctly')
            
            # Test get_file_info
            print("\nTesting get_file_info()")
            response = await agent.process_query("Get detailed information about config.json")
            print(f"Response: {response.response}")
            assert response.success, "Failed to get file info"
            assert 'size' in response.response.lower() or 'bytes' in response.response.lower()
            print('✓ get_file_info works correctly')
            
            # Test error handling
            print("\n--- Error Handling ---")
            response = await agent.process_query("Read a file called nonexistent.txt")
            print(f"Response: {response.response}")
            # Should handle error gracefully
            assert 'not found' in response.response.lower() or 'error' in response.response.lower()
            print('✓ Error handling works correctly')
            
            # Test tool result parsing between calls
            print("\n--- Test Output Parsing Between Tools ---")
            response = await agent.process_query("List all files, then read the content of the first one you find")
            print(f"Response: {response.response}")
            assert response.success, "Failed to parse tool outputs"
            print('✓ Tool output parsing works correctly')
            
            # Performance test - ensure reasonable response times
            print("\n--- Performance Test ---")
            import time
            start_time = time.time()
            response = await agent.process_query("Quick test - just list the files")
            end_time = time.time()
            response_time = end_time - start_time
            print(f"Response time: {response_time:.2f} seconds")
            assert response_time < 10.0, f"Response too slow: {response_time:.2f}s"
            print('✓ Performance is acceptable')
            
            print("\n" + "=" * 60)
            print("✅ Phase 2 Task 4: All tests passed!")
            print("✅ File System Tools Integration: COMPLETE")
            print("✅ Tool Chaining: WORKING")
            print("✅ Advanced Operations: IMPLEMENTED")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_chaining_edge_cases():
    """Test edge cases for tool chaining."""
    print("\n--- Testing Tool Chaining Edge Cases ---")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create edge case scenario
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        # Test empty workspace
        response = await agent.process_query("What files are available?")
        assert response.success, "Failed to handle empty workspace"
        assert 'no files' in response.response.lower() or 'empty' in response.response.lower() or '[]' in response.response
        print('✓ Empty workspace handled correctly')
        
        # Create a file and test
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('Test content')
        
        response = await agent.process_query("Read the newest file and tell me about it")
        assert response.success, "Failed to chain tools with single file"
        assert 'test content' in response.response.lower()
        print('✓ Single file tool chaining works')


if __name__ == "__main__":
    async def main():
        print("Running Phase 2 Task 4 Integration Tests...")
        
        # Run main test
        success1 = await test_task4_file_system_integration()
        
        # Run edge cases
        success2 = await test_tool_chaining_edge_cases()
        
        if success1 and success2:
            print("\n🎉 All Phase 2 Task 4 tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    
    asyncio.run(main())
