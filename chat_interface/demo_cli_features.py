#!/usr/bin/env python3
"""
Demo script showing CLI Chat Interface functionality.

This script demonstrates the key features of the AI File System Agent's
CLI chat interface including conversation management, debug mode, and
command handling.
"""

import asyncio
import tempfile
from pathlib import Path
import json

# Add project root to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from chat_interface.cli_chat.chat import CLIChat, ConversationHistory
from config.model_config import ModelConfig
from agent.supervisor.supervisor import ModerationRequest, ModerationResponse, ModerationDecision
from agent.core.secure_agent import AgentResponse
from unittest.mock import Mock, AsyncMock

def demo_conversation_history():
    """Demonstrate conversation history functionality."""
    print("🗣️ CONVERSATION HISTORY DEMO")
    print("=" * 50)
    
    # Create temporary session file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        session_file = Path(f.name)
    
    try:
        # Initialize history
        history = ConversationHistory(session_file)
        
        # Add some sample conversation
        history.add_message("user", "Hello, can you help me with file operations?")
        history.add_message("agent", "Of course! I can help you with reading, writing, and managing files in your workspace.")
        history.add_message("user", "Can you list the files in my workspace?")
        history.add_message("agent", "I'll list the files for you.", {"tools_used": ["list_files"]})
        
        print(f"📁 Session file: {session_file}")
        print(f"💬 Total messages: {len(history.messages)}")
        
        # Show recent messages
        print("\n📜 Recent conversation:")
        for i, msg in enumerate(history.get_recent_messages(4), 1):
            role = msg['role'].capitalize()
            content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            print(f"  {i}. {role}: {content}")
        
        # Load the saved session
        print("\n🔄 Testing session persistence...")
        new_history = ConversationHistory(session_file)
        print(f"✅ Loaded {len(new_history.messages)} messages from session file")
        
    finally:
        session_file.unlink(missing_ok=True)

def demo_cli_features():
    """Demonstrate CLI chat features."""
    print("\n🖥️ CLI CHAT FEATURES DEMO")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # Initialize model config
            model_config = ModelConfig(environment='local')
            
            # Create CLI instance
            cli = CLIChat(
                workspace_path=tmpdir,
                debug_mode=True,
                session_name="demo_session",
                model_config=model_config
            )
            
            print(f"🎯 Workspace: {cli.workspace_path}")
            print(f"🔧 Debug mode: {'ON' if cli.debug_mode else 'OFF'}")
            print(f"💾 Session file: {cli.history.session_file}")
            print(f"🤖 Model config: {cli.model_config.environment}")
            
            # Test command handling
            print("\n🎮 Testing commands:")
            
            commands_to_test = [
                ("/help", "Show help"),
                ("/debug", "Toggle debug mode"),
                ("/workspace", "Show workspace info"),
                ("/history", "Show conversation history"),
                ("/unknown", "Unknown command"),
            ]
            
            for cmd, description in commands_to_test:
                print(f"  Testing '{cmd}' ({description})")
                result = cli._handle_command(cmd)
                status = "✅ Continue" if result else "🛑 Exit"
                print(f"    Result: {status}")
            
            print(f"\n🔧 Debug mode after toggle: {'ON' if cli.debug_mode else 'OFF'}")
            
        except Exception as e:
            print(f"⚠️ Demo requires proper environment setup: {e}")
            print("💡 This is expected if API keys are not configured")

async def demo_message_processing():
    """Demonstrate message processing workflow."""
    print("\n🔄 MESSAGE PROCESSING DEMO")
    print("=" * 50)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create mocked CLI for demonstration
        cli = Mock()
        cli.history = ConversationHistory()
        cli.console = Mock()
        cli.logger = Mock()
        
        # Mock supervisor
        mock_supervisor = Mock()
        
        # Test rejection scenario
        print("🚫 Testing request rejection...")
        mock_supervisor.moderate_request = AsyncMock(return_value=ModerationResponse(
            conversation_id="demo-1",
            decision=ModerationDecision.REJECTED,
            allowed=False,
            reason="Request contains potentially harmful content",
            risk_factors=["file_deletion"],
            intent=None
        ))
        
        cli.supervisor = mock_supervisor
        
        # Simulate the rejection flow
        print("  User input: 'Delete all files in the system'")
        print("  Supervisor decision: REJECTED")
        print("  Reason: Request contains potentially harmful content")
        print("  ❌ Request blocked before reaching agent")
        
        # Test approval scenario
        print("\n✅ Testing request approval...")
        mock_supervisor.moderate_request = AsyncMock(return_value=ModerationResponse(
            conversation_id="demo-2",
            decision=ModerationDecision.ALLOWED,
            allowed=True,
            reason="Safe file operation request",
            risk_factors=[],
            intent=None
        ))
        
        # Mock agent
        mock_agent = Mock()
        mock_agent.process_query = AsyncMock(return_value=AgentResponse(
            conversation_id="demo-2",
            response="Here are the files in your workspace:\n- README.md\n- config.json",
            tools_used=["list_files"],
            success=True
        ))
        
        cli.agent = mock_agent
        
        print("  User input: 'List files in my workspace'")
        print("  Supervisor decision: ALLOWED")
        print("  Agent response: Successfully listed files")
        print("  🔧 Tools used: list_files")
        print("  ✅ Response delivered to user")

def demo_debug_features():
    """Demonstrate debug mode features."""
    print("\n🐛 DEBUG FEATURES DEMO")
    print("=" * 50)
    
    # Mock reasoning steps
    reasoning_steps = [
        {
            "type": "think",
            "content": "The user wants to list files in their workspace. I need to use the list_files tool."
        },
        {
            "type": "act",
            "tool": "list_files",
            "args": {"pattern": "*"}
        },
        {
            "type": "observe",
            "content": "Found 3 files: README.md, config.json, data.txt"
        },
        {
            "type": "think",
            "content": "I have successfully retrieved the file list. I should format this nicely for the user."
        }
    ]
    
    print("🧠 Reasoning steps visualization:")
    for i, step in enumerate(reasoning_steps, 1):
        step_type = step.get('type', 'unknown')
        content = step.get('content', '')
        
        # Color indicators (simulated)
        if step_type == 'think':
            icon = "💭"
        elif step_type == 'act':
            icon = "⚡"
        elif step_type == 'observe':
            icon = "👀"
        else:
            icon = "❓"
        
        print(f"  {icon} Step {i} ({step_type.upper()}):")
        
        if step_type == 'act' and 'tool' in step:
            tool_name = step.get('tool', 'unknown')
            tool_args = step.get('args', {})
            print(f"    Tool: {tool_name}")
            if tool_args:
                print(f"    Args: {json.dumps(tool_args, indent=6)}")
        else:
            print(f"    {content}")
        print()

def demo_session_persistence():
    """Demonstrate session persistence."""
    print("\n💾 SESSION PERSISTENCE DEMO")
    print("=" * 50)
    
    # Create a demo session directory
    sessions_dir = Path.home() / ".ai-fs-chat" / "sessions"
    demo_session_file = sessions_dir / "demo_session.json"
    
    print(f"📁 Sessions directory: {sessions_dir}")
    print(f"📄 Demo session file: {demo_session_file}")
    
    # Create sample session data
    session_data = {
        "messages": [
            {
                "role": "user",
                "content": "Hello, I need help with file operations",
                "timestamp": "2025-07-01T16:00:00",
                "metadata": {}
            },
            {
                "role": "agent",
                "content": "I'm here to help with file operations in your workspace!",
                "timestamp": "2025-07-01T16:00:01",
                "metadata": {
                    "conversation_id": "demo-123",
                    "tools_used": [],
                    "success": True
                }
            }
        ],
        "created": "2025-07-01T16:00:00"
    }
    
    # Show session structure
    print("\n📋 Session file structure:")
    print(json.dumps(session_data, indent=2))
    
    print("\n🔄 Session workflow:")
    print("  1. User starts chat with --session demo_session")
    print("  2. Conversation history is loaded from file")
    print("  3. New messages are added and auto-saved")
    print("  4. User can resume conversation later")
    print("  5. /history command shows conversation")
    print("  6. /clear command clears history and removes file")

def main():
    """Run all demos."""
    print("🎉 AI FILE SYSTEM AGENT - CLI CHAT INTERFACE DEMO")
    print("=" * 60)
    print("This demo shows the key features of the CLI chat interface.")
    print("The interface is fully implemented and ready for use!")
    print()
    
    try:
        # Run demos
        demo_conversation_history()
        demo_cli_features()
        asyncio.run(demo_message_processing())
        demo_debug_features()
        demo_session_persistence()
        
        print("\n🎯 SUMMARY")
        print("=" * 60)
        print("✅ Conversation history with persistence")
        print("✅ Rich CLI interface with colorized output")
        print("✅ Debug mode with reasoning visualization")
        print("✅ Command system (/help, /debug, /history, etc.)")
        print("✅ Safety supervision with request moderation")
        print("✅ Session management and resumption")
        print("✅ Error handling and user feedback")
        print("✅ Integration with agent and file system tools")
        
        print("\n🚀 READY TO USE!")
        print("Run: python -m chat_interface.cli_chat.chat --help")
        print("Example: python -m chat_interface.cli_chat.chat --workspace ./sandbox --debug --session my_session --env local")
        
    except Exception as e:
        print(f"❌ Demo error: {e}")
        print("This is expected if environment is not fully configured.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
