#!/usr/bin/env python3
"""
Script per testare direttamente i tools disponibili.
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

def test_tools_directly():
    """Test dei tools direttamente."""
    
    print("🧪 TESTING TOOLS DIRECTLY")
    print("=" * 40)
    
    # Create workspace and tools
    workspace = Workspace("sandbox")
    tools = create_file_tools(workspace)
    
    print(f"Available tools: {list(tools.keys())}")
    
    print("\n1️⃣ Testing list_files:")
    try:
        files = tools["list_files"]()
        print(f"   Success: {len(files)} files found")
        for f in files[:3]:
            print(f"   📄 {f}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n2️⃣ Testing list_directories:")
    try:
        directories = tools["list_directories"]()
        print(f"   Success: {len(directories)} directories found")
        for d in directories:
            print(f"   📁 {d}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3️⃣ Testing list_all:")
    try:
        all_items = tools["list_all"]()
        print(f"   Success: {len(all_items)} items found")
        for item in all_items[:5]:
            if item.endswith("/"):
                print(f"   📁 {item}")
            else:
                print(f"   📄 {item}")
    except Exception as e:
        print(f"   Error: {e}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_tools_directly()
        print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)
