#!/usr/bin/env python3
"""
Simple script to demonstrate workspace_fs public API.

This script showcases the basic usage of Workspace and FileSystemTools
classes with proper error handling.
"""

import tempfile
from workspace_fs import (
    Workspace,
    FileSystemTools,
    PathTraversalError,
    SizeLimitExceeded,
    RateLimitError
)


def main():
    """Demonstrate workspace_fs API usage."""
    print("🔧 workspace_fs API Demo")
    print("=" * 40)
    
    # Create temporary workspace for demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"📁 Created temporary workspace: {temp_dir}")
        
        # Initialize workspace and tools
        workspace = Workspace(temp_dir)
        fs_tools = FileSystemTools(
            workspace,
            max_read=1024,  # 1KB limit for demo
            max_write=1024,  # 1KB limit for demo
            rate_limit=5.0   # 5 ops/sec for demo
        )
        
        print(f"🏗️  Workspace: {workspace}")
        print(f"🛠️  Tools: {fs_tools}")
        print()
        
        # Demonstrate file operations
        print("📝 Writing test files...")
        fs_tools.write_file("hello.txt", "Hello, World!")
        fs_tools.write_file("data.txt", "Some data content")
        print("   ✅ Files written successfully")
        
        # List files
        print("\n📋 Listing files:")
        files = fs_tools.list_files()
        for i, filename in enumerate(files, 1):
            print(f"   {i}. {filename}")
        
        # Read file
        print("\n📖 Reading hello.txt:")
        content = fs_tools.read_file("hello.txt")
        print(f"   Content: '{content}'")
        
        # Demonstrate security features
        print("\n🔒 Security demonstration:")
        
        # Path traversal prevention
        try:
            workspace.safe_join("../escape.txt")
        except ValueError as e:
            print(f"   ✅ Path traversal blocked: {e}")
        
        # Size limit enforcement
        try:
            large_content = "x" * 2000  # Exceeds 1KB limit
            fs_tools.write_file("large.txt", large_content)
        except SizeLimitExceeded as e:
            print(f"   ✅ Size limit enforced: {e}")
        
        print("\n🎉 Demo completed successfully!")


if __name__ == "__main__":
    main()
