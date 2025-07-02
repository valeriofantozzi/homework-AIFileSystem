#!/usr/bin/env python3
"""
Simple test script for Phase 2 - Task 4: File System Tool Integration
Tests basic file system tool integration and tool chaining without external API dependencies.
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


async def test_basic_task4_integration():
    """Test basic file system tool integration without external APIs."""
    try:
        print("=" * 60)
        print("Testing Phase 2 - Task 4: Basic File System Integration")
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
            
            # Test 4.2: Basic Tool Operations
            print("\n--- Test 4.2: Basic Tool Operations ---")
            
            # Test case 1: List files
            print("\nTest case 1: List all files")
            response = await agent.process_query("List all files in the workspace")
            print(f"Response: {response.response}")
            assert response.success, "Failed to list files"
            assert 'notes_meeting.txt' in response.response.lower()
            print('✓ Successfully listed files')
            
            # Test case 2: Read newest file using advanced operation
            print("\nTest case 2: Read newest file content using advanced operation")
            response = await agent.process_query("Use the read_newest_file function to show me the latest content")
            print(f"Response: {response.response}")
            assert response.success, "Failed to read newest file"
            assert ('meeting' in response.response.lower() or 'notes' in response.response.lower())
            print('✓ Successfully used read_newest_file advanced operation')
            
            # Test case 3: Find files by pattern
            print("\nTest case 3: Find files with pattern")
            response = await agent.process_query("Find all files containing 'txt' in their name using find_files_by_pattern")
            print(f"Response: {response.response}")
            assert response.success, "Failed to find files by pattern"
            assert 'readme.txt' in response.response.lower()
            print('✓ Successfully used find_files_by_pattern')
            
            # Test case 4: Get file information
            print("\nTest case 4: Get detailed file information")
            response = await agent.process_query("Get detailed information about config.json using get_file_info")
            print(f"Response: {response.response}")
            assert response.success, "Failed to get file info"
            assert ('size' in response.response.lower() or 'bytes' in response.response.lower())
            print('✓ Successfully used get_file_info')
            
            # Test case 5: Read specific file
            print("\nTest case 5: Read a specific file")
            response = await agent.process_query("Read the content of config.json")
            print(f"Response: {response.response}")
            assert response.success, "Failed to read specific file"
            assert 'test-project' in response.response.lower()
            print('✓ Successfully read specific file')
            
            # Test 4.3: Tool Chaining - Multi-step operations
            print("\n--- Test 4.3: Tool Chaining ---")
            
            # Test case 1: List then read operation
            print("\nTest case 1: List files then read one")
            response = await agent.process_query("First list all files, then read the content of readme.txt")
            print(f"Response: {response.response}")
            assert response.success, "Failed multi-step operation"
            print('✓ Successfully chained list and read operations')
            
            # Test error handling
            print("\n--- Error Handling ---")
            response = await agent.process_query("Read a file called nonexistent.txt")
            print(f"Response: {response.response}")
            # Should handle error gracefully
            assert ('not found' in response.response.lower() or 
                   'error' in response.response.lower() or
                   'does not exist' in response.response.lower())
            print('✓ Error handling works correctly')
            
            print("\n" + "=" * 60)
            print("✅ Phase 2 Task 4: Basic Integration Tests Passed!")
            print("✅ File System Tools: CONNECTED")
            print("✅ Advanced Operations: WORKING")
            print("✅ Tool Chaining: FUNCTIONING")
            print("=" * 60)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_edge_cases():
    """Test edge cases for tool operations."""
    print("\n--- Testing Edge Cases ---")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create edge case scenario
        agent = SecureAgent(temp_dir, debug_mode=True)
        
        # Test empty workspace
        response = await agent.process_query("List all files")
        assert response.success, "Failed to handle empty workspace"
        print('✓ Empty workspace handled correctly')
        
        # Create a single file and test
        test_file = os.path.join(temp_dir, 'test.txt')
        with open(test_file, 'w') as f:
            f.write('Test content for single file')
        
        response = await agent.process_query("Read the newest file")
        assert response.success, "Failed to read single file"
        assert 'content for single file' in response.response.lower()
        print('✓ Single file operations work correctly')


if __name__ == "__main__":
    async def main():
        print("Running Phase 2 Task 4 Basic Integration Tests...")
        
        # Run main test
        success1 = await test_basic_task4_integration()
        
        # Run edge cases
        success2 = await test_edge_cases() 
        
        if success1 and success2:
            print("\n🎉 All Phase 2 Task 4 basic tests passed!")
            print("\nTask 4 Status:")
            print("✅ Task 4.1: Connect crud_tools to agent - COMPLETE")
            print("✅ Task 4.2: Implement tool chaining - FUNCTIONAL")  
            print("✅ Task 4.3: Add advanced file operations - COMPLETE")
            print("\n🎯 Phase 2 Task 4: READY FOR COMPLETION")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    
    asyncio.run(main())
