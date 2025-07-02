#!/usr/bin/env python3
"""
Interactive demo following the Usage Guide steps.
This shows how to use the AI File System Agent through its chat interface.
"""

import subprocess
import sys
import time
from pathlib import Path

def main():
    print("🎯 INTERACTIVE USAGE GUIDE DEMO")
    print("=" * 50)
    print()
    
    # Check current workspace setup
    sandbox_path = Path("sandbox")
    if not sandbox_path.exists():
        print("📁 Creating sandbox workspace...")
        sandbox_path.mkdir()
    
    print(f"✅ Workspace ready: {sandbox_path.absolute()}")
    print()
    
    # Demo commands to try with the agent
    demo_commands = [
        ("Show me all files in my workspace", "📋 Lists all files in the workspace"),
        ("Read the contents of hello.txt", "📖 Reads specific file content"),
        ("Create a file called test.txt with 'Demo content'", "📝 Creates new file"),
        ("Find all Python files", "🐍 Searches for specific file types"),
        ("Show me the newest file", "🆕 Finds most recently modified file"),
        ("Create a summary of all files", "📊 Advanced analysis across files"),
    ]
    
    print("🤖 SUGGESTED COMMANDS TO TRY:")
    print("-" * 40)
    for i, (command, description) in enumerate(demo_commands, 1):
        print(f"{i}. {command}")
        print(f"   {description}")
        print()
    
    print("🚀 STARTING INTERACTIVE CHAT AGENT...")
    print("=" * 50)
    print()
    print("💡 Tips:")
    print("- Try the commands listed above")
    print("- Type '/help' for available commands")
    print("- Type '/debug' to see reasoning steps")  
    print("- Type '/workspace' to see workspace info")
    print("- Type '/quit' to exit")
    print()
    print("Starting in 3 seconds...")
    time.sleep(3)
    
    # Start the interactive chat
    try:
        cmd = [
            sys.executable, "-m", "chat_interface.cli_chat.chat",
            "--workspace", str(sandbox_path.absolute()),
            "--env", "development"
        ]
        
        # Run with poetry if available
        try:
            subprocess.run(["poetry", "--version"], check=True, capture_output=True)
            cmd = ["poetry", "run"] + cmd
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
            
        subprocess.run(cmd)
        
    except KeyboardInterrupt:
        print("\n\n👋 Chat session ended. Thanks for trying the demo!")
    except Exception as e:
        print(f"\n❌ Error starting chat: {e}")
        print("\n🔧 Alternative: Try running manually:")
        print(f"   poetry run python -m chat_interface.cli_chat.chat --workspace {sandbox_path.absolute()}")

if __name__ == "__main__":
    main()
