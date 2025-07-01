#!/usr/bin/env python3
"""
Quick test script to verify CLI chat interface imports and basic functionality.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        from chat_interface.cli_chat import CLIChat, main
        print("✅ CLI chat imports successful")
    except ImportError as e:
        print(f"❌ CLI chat import failed: {e}")
        return False
    
    try:
        from agent.core.secure_agent import SecureAgent
        print("✅ SecureAgent import successful")
    except ImportError as e:
        print(f"❌ SecureAgent import failed: {e}")
        return False
    
    try:
        from agent.supervisor.supervisor import RequestSupervisor, ModerationRequest
        print("✅ Supervisor imports successful")
    except ImportError as e:
        print(f"❌ Supervisor import failed: {e}")
        return False
    
    try:
        from config.model_config import ModelConfig
        print("✅ ModelConfig import successful")
    except ImportError as e:
        print(f"❌ ModelConfig import failed: {e}")
        return False
    
    return True

def test_cli_creation():
    """Test CLI object creation."""
    print("\nTesting CLI creation...")
    
    try:
        from chat_interface.cli_chat import CLIChat
        from config.model_config import ModelConfig
        
        # Create a temporary workspace
        workspace_path = "/tmp/test_workspace"
        Path(workspace_path).mkdir(exist_ok=True)
        
        # Create model config (this will test environment loading too)
        model_config = ModelConfig(environment="development")
        
        # Create CLI instance
        cli = CLIChat(
            workspace_path=workspace_path,
            debug_mode=True,
            model_config=model_config
        )
        
        print("✅ CLI creation successful")
        print(f"   Workspace: {cli.workspace_path}")
        print(f"   Debug mode: {cli.debug_mode}")
        return True
        
    except Exception as e:
        print(f"❌ CLI creation failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing CLI Chat Interface")
    print("=" * 40)
    
    success = True
    
    if not test_imports():
        success = False
    
    if not test_cli_creation():
        success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    exit(main())
