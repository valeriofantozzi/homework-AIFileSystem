#!/usr/bin/env python3
"""
Debug script per analizzare perché "list directories" non funziona.
"""

import sys
import os

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def debug_directory_command():
    """Debug del comando 'list directories'."""
    
    print("🔍 DEBUG: 'list directories' command")
    print("=" * 50)
    
    query = "list directories"
    query_lower = query.lower()
    
    print(f"Original query: '{query}'")
    print(f"Query lowercase: '{query_lower}'")
    
    # Test conditions like in react_loop.py
    
    # Check for directory-specific requests first
    condition1 = ("directories" in query_lower or "directory" in query_lower or "folders" in query_lower or 
                 "folder" in query_lower or "cartelle" in query_lower)
    
    condition2 = ("list" in query_lower or "show" in query_lower or "mostra" in query_lower or 
                 "lista" in query_lower)
    
    print(f"\nCondition checks:")
    print(f"  directories/directory/folders/folder/cartelle in query: {condition1}")
    print(f"    - 'directories' in query_lower: {'directories' in query_lower}")
    print(f"    - 'directory' in query_lower: {'directory' in query_lower}")
    print(f"    - 'folders' in query_lower: {'folders' in query_lower}")
    print(f"    - 'folder' in query_lower: {'folder' in query_lower}")
    print(f"    - 'cartelle' in query_lower: {'cartelle' in query_lower}")
    
    print(f"  list/show/mostra/lista in query: {condition2}")
    print(f"    - 'list' in query_lower: {'list' in query_lower}")
    print(f"    - 'show' in query_lower: {'show' in query_lower}")
    print(f"    - 'mostra' in query_lower: {'mostra' in query_lower}")
    print(f"    - 'lista' in query_lower: {'lista' in query_lower}")
    
    overall_condition = condition1 and condition2
    print(f"\nOverall condition (both must be True): {overall_condition}")
    
    if overall_condition:
        print("✅ Should call list_directories")
    else:
        print("❌ Will NOT call list_directories")
        
    # Check fallback conditions
    print(f"\nFallback checks:")
    print(f"  'list' in thought_lower (if this was thought): {'list' in query_lower}")
    print(f"  'files' in thought_lower: {'files' in query_lower}")
    print(f"  'what files' in query_lower: {'what files' in query_lower}")
    
    fallback_condition = "list" in query_lower or "files" in query_lower or "what files" in query_lower
    print(f"  Fallback condition (would call list_files): {fallback_condition}")
    
    # Test with other directory commands
    test_commands = [
        "show directories",
        "list folders", 
        "show folders",
        "lista directory",
        "mostra cartelle",
        "directories",
        "folders"
    ]
    
    print(f"\n🧪 Testing other directory commands:")
    for cmd in test_commands:
        cmd_lower = cmd.lower()
        c1 = ("directories" in cmd_lower or "directory" in cmd_lower or "folders" in cmd_lower or 
              "folder" in cmd_lower or "cartelle" in cmd_lower)
        c2 = ("list" in cmd_lower or "show" in cmd_lower or "mostra" in cmd_lower or 
              "lista" in cmd_lower)
        result = c1 and c2
        print(f"  '{cmd}' → {'✅' if result else '❌'}")

if __name__ == "__main__":
    debug_directory_command()
