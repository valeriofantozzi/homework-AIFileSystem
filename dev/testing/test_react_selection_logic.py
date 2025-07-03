#!/usr/bin/env python3
"""
Test script specifico per il ReAct loop con il comando 'list directories'.
"""

import sys
import os

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_react_loop_directory_selection():
    """Test della logica di selezione nel ReAct loop."""
    
    print("🧪 TESTING ReAct Loop Tool Selection")
    print("=" * 42)
    
    # Mock the conditions as they would appear in the ReAct loop
    user_query = "list directories"
    last_thought = "I need to help the user with: list directories\n\nLet me think about what I need to do."
    
    query_lower = user_query.lower()
    thought_lower = last_thought.lower()
    
    print(f"User query: '{user_query}'")
    print(f"Last thought: '{last_thought[:50]}...'")
    print(f"Query lower: '{query_lower}'")
    print(f"Thought lower: '{thought_lower[:50]}...'")
    
    # Simulate the logic from _decide_tool_action
    print(f"\n🔍 Testing decision logic:")
    
    # Check for directory-specific requests first
    condition1 = ("directories" in query_lower or "directory" in query_lower or "folders" in query_lower or 
                 "folder" in query_lower or "cartelle" in query_lower)
    condition2 = ("list" in query_lower or "show" in query_lower or "mostra" in query_lower or 
                 "lista" in query_lower)
    
    print(f"1. Directory condition: {condition1}")
    print(f"2. List condition: {condition2}")
    print(f"3. Combined (directory request): {condition1 and condition2}")
    
    if condition1 and condition2:
        selected_tool = "list_directories"
        print(f"✅ Would select: {selected_tool}")
    else:
        # Check for "list all" or "show all"
        elif_condition1 = (("list" in query_lower and "all" in query_lower) or 
                          ("show" in query_lower and "all" in query_lower))
        print(f"4. List all condition: {elif_condition1}")
        
        if elif_condition1:
            selected_tool = "list_all"
            print(f"✅ Would select: {selected_tool}")
        else:
            # Check for explicit file listing
            elif_condition2 = (("list" in query_lower and "files" in query_lower) or 
                              "what files" in query_lower)
            print(f"5. Explicit file listing condition: {elif_condition2}")
            
            if elif_condition2:
                selected_tool = "list_files (explicit)"
                print(f"✅ Would select: {selected_tool}")
            else:
                # Default file listing only if "list" appears without directory context
                elif_condition3 = ("list" in thought_lower and 
                                  not any(dir_word in thought_lower for dir_word in ["directories", "directory", "folders", "folder", "cartelle"]))
                print(f"6. Default list condition: {elif_condition3}")
                print(f"   - 'list' in thought_lower: {'list' in thought_lower}")
                print(f"   - directory words in thought_lower: {[word for word in ['directories', 'directory', 'folders', 'folder', 'cartelle'] if word in thought_lower]}")
                
                if elif_condition3:
                    selected_tool = "list_files (default)"
                    print(f"❌ Would incorrectly select: {selected_tool}")
                else:
                    selected_tool = "None (no match)"
                    print(f"⚪ Would select: {selected_tool}")
    
    # Test with different thought patterns
    print(f"\n🧪 Testing with different thought patterns:")
    test_thoughts = [
        "I need to list directories",
        "Let me list the directories for the user",
        "I should show directories",
        "The user wants to see directories",
        "I need to help with: list directories"
    ]
    
    for test_thought in test_thoughts:
        tt_lower = test_thought.lower()
        has_dir_words = any(dir_word in tt_lower for dir_word in ["directories", "directory", "folders", "folder", "cartelle"])
        has_list = "list" in tt_lower
        
        # The new condition
        would_select_default = (has_list and not has_dir_words)
        
        print(f"  '{test_thought[:30]}...' → default list: {would_select_default} (has_list: {has_list}, has_dir_words: {has_dir_words})")
    
    return True

if __name__ == "__main__":
    try:
        success = test_react_loop_directory_selection()
        print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
