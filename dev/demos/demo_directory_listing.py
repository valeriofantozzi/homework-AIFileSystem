#!/usr/bin/env python3
"""
Demo delle funzionalità di directory listing.
"""

import sys
import os

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'tools/workspace_fs/src'))
sys.path.append(os.path.join(project_root, 'tools/crud_tools/src'))

from workspace_fs import Workspace, FileSystemTools
from crud_tools import create_file_tools

def demo_directory_listing():
    """Dimostra le funzionalità di directory listing."""
    
    print("📁 DIRECTORY LISTING DEMO")
    print("=" * 40)
    
    # Create workspace and tools
    workspace = Workspace("sandbox")
    fs_tools = FileSystemTools(workspace)
    tools = create_file_tools(workspace)
    
    print("\n1️⃣ LISTING SOLO FILE:")
    files = tools["list_files"]()
    print(f"   Files found: {len(files)}")
    for file in files[:5]:  # Show first 5
        print(f"   📄 {file}")
    if len(files) > 5:
        print(f"   ... and {len(files) - 5} more files")
    
    print("\n2️⃣ LISTING SOLO DIRECTORY:")
    directories = tools["list_directories"]()
    print(f"   Directories found: {len(directories)}")
    for directory in directories:
        print(f"   📁 {directory}")
    
    print("\n3️⃣ LISTING TUTTO (FILES + DIRECTORIES):")
    all_items = tools["list_all"]()
    print(f"   Total items: {len(all_items)}")
    for item in all_items[:10]:  # Show first 10
        if item.endswith("/"):
            print(f"   📁 {item}")
        else:
            print(f"   📄 {item}")
    if len(all_items) > 10:
        print(f"   ... and {len(all_items) - 10} more items")
    
    print("\n📊 SUMMARY:")
    print(f"   ✅ Files: {len(files)}")
    print(f"   ✅ Directories: {len(directories)}")
    print(f"   ✅ Total items: {len(all_items)}")
    
    return True

if __name__ == "__main__":
    try:
        success = demo_directory_listing()
        print(f"\n🎯 Demo {'COMPLETED' if success else 'FAILED'}")
    except Exception as e:
        print(f"❌ Demo error: {e}")
        sys.exit(1)
