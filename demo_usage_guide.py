#!/usr/bin/env python3
"""
Demo script following the Usage Guide steps.
This script demonstrates the basic operations from the usage guide.
"""

import sys
import os
sys.path.append('tools/workspace_fs/src')

# Add the project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from workspace_fs import Workspace, FileSystemTools

def main():
    print("🎯 Following Usage Guide Steps - Basic Operations Demo")
    print("=" * 60)
    
    # Initialize workspace (Step from usage guide)
    workspace_path = "/Users/valeriofantozzi/Developer/Personal🦄/homework-AIFileSystem/sandbox"
    workspace = Workspace(workspace_path)
    fs_tools = FileSystemTools(workspace)
    
    print(f"📁 Workspace: {workspace_path}")
    print(f"🛠️  Tools initialized: {fs_tools}")
    print()
    
    # Basic Operations from Usage Guide
    
    # 1. File Listing and Exploration
    print("1️⃣  FILE LISTING AND EXPLORATION")
    print("-" * 40)
    files = fs_tools.list_files()
    if files:
        print("📋 Files in workspace:")
        for i, filename in enumerate(files, 1):
            print(f"   {i}. {filename}")
    else:
        print("📋 No files found in workspace")
    print()
    
    # 2. File Reading
    print("2️⃣  FILE READING")
    print("-" * 40)
    if files:
        # Read the first file
        first_file = files[0]
        print(f"📖 Reading '{first_file}':")
        try:
            content = fs_tools.read_file(first_file)
            # Show first 200 characters
            preview = content[:200] + "..." if len(content) > 200 else content
            print(f"   Content preview: {preview}")
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
    print()
    
    # 3. File Creation  
    print("3️⃣  FILE CREATION")
    print("-" * 40)
    try:
        demo_content = "This is a demo file created by following the usage guide steps!"
        result = fs_tools.write_file("demo_guide.txt", demo_content)
        print(f"✅ {result}")
    except Exception as e:
        print(f"❌ Error creating file: {e}")
    print()
    
    # 4. File Modification
    print("4️⃣  FILE MODIFICATION")
    print("-" * 40)
    try:
        append_content = "\nThis line was added by the modification demo."
        result = fs_tools.write_file("demo_guide.txt", append_content, mode="a")
        print(f"✅ {result}")
        
        # Read back to verify
        updated_content = fs_tools.read_file("demo_guide.txt")
        print(f"📖 Updated content: {updated_content}")
    except Exception as e:
        print(f"❌ Error modifying file: {e}")
    print()
    
    # 5. Final file listing
    print("5️⃣  FINAL FILE LISTING")
    print("-" * 40)
    final_files = fs_tools.list_files()
    print("📋 Final files in workspace:")
    for i, filename in enumerate(final_files, 1):
        print(f"   {i}. {filename}")
    
    print("\n🎉 Usage Guide Basic Operations Demo Complete!")
    print("✅ All steps from the usage guide have been demonstrated")

if __name__ == "__main__":
    main()
