#!/usr/bin/env python3
"""
Test script for the model configuration system.

This script validates the centralized model configuration functionality
and demonstrates usage with different roles and providers.
"""

import asyncio
import os
import tempfile
from pathlib import Path

# Set up path to find config module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from workspace_fs import Workspace
from crud_tools.question_tool import answer_question_about_files, create_question_tool_function


def test_config_loading():
    """Test loading the model configuration."""
    print("=== Testing Configuration Loading ===")
    
    try:
        from config import get_model_config
        
        config = get_model_config()
        print(f"✓ Configuration loaded successfully")
        print(f"  Available providers: {config.get_available_providers()}")
        print(f"  Available roles: {config.get_available_roles()}")
        
        # Test role-based model selection
        for role in ["supervisor", "agent", "file_analysis", "chat"]:
            try:
                model_provider = config.get_model_for_role(role)
                print(f"  {role}: {model_provider.provider_name}:{model_provider.model_name}")
            except Exception as e:
                print(f"  {role}: ✗ Error - {e}")
        
        return True
        
    except ImportError:
        print("✗ Configuration module not available")
        return False
    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False


async def test_question_tool_with_config():
    """Test the question tool with configurable models."""
    print("\n=== Testing Question Tool with Configuration ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create test files
        fs_tools.write_file("example.py", """
def hello_world():
    '''A simple greeting function.'''
    return "Hello, World!"

def add_numbers(a, b):
    '''Add two numbers together.'''
    return a + b
""")
        
        fs_tools.write_file("config.json", '{"app": "test", "version": "1.0"}')
        
        # Test with different roles
        roles_to_test = ["file_analysis", "chat", "agent"]
        
        for role in roles_to_test:
            print(f"\n--- Testing role: {role} ---")
            
            try:
                # Test direct function call
                answer = await answer_question_about_files(
                    workspace=workspace,
                    query="What programming language is used and what functions are defined?",
                    role=role,
                    max_files=5
                )
                print(f"✓ Direct call succeeded for role '{role}'")
                print(f"  Answer: {answer[:100]}...")
                
                # Test factory function
                question_func = create_question_tool_function(workspace, role=role)
                answer2 = await question_func("What is the app name in the config?")
                print(f"✓ Factory function succeeded for role '{role}'")
                print(f"  Answer: {answer2[:100]}...")
                
            except Exception as e:
                print(f"✗ Failed for role '{role}': {e}")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_environment_variables():
    """Test environment variable handling."""
    print("\n=== Testing Environment Variables ===")
    
    # Test with mock environment variables
    original_openai_key = os.environ.get("OPENAI_API_KEY")
    
    try:
        # Set a test API key
        os.environ["OPENAI_API_KEY"] = "test-key-12345"
        
        from config import get_model_config
        config = get_model_config()
        
        model_provider = config.get_model_for_role("supervisor")
        params = model_provider.get_client_params()
        
        if params.get("api_key") == "test-key-12345":
            print("✓ Environment variable substitution working")
        else:
            print(f"✗ Environment variable not substituted: {params.get('api_key')}")
            
    except Exception as e:
        print(f"✗ Environment variable test failed: {e}")
        
    finally:
        # Restore original environment
        if original_openai_key is not None:
            os.environ["OPENAI_API_KEY"] = original_openai_key
        elif "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]


async def test_fallback_behavior():
    """Test fallback behavior when configuration is not available."""
    print("\n=== Testing Fallback Behavior ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        fs_tools.write_file("test.txt", "This is a test file.")
        
        # Test with explicit model override
        answer = await answer_question_about_files(
            workspace=workspace,
            query="What is in this file?",
            llm_model="openai:gpt-4o-mini",  # Explicit override
            max_files=1
        )
        
        print("✓ Model override working")
        print(f"  Answer: {answer[:100]}...")
        
    except Exception as e:
        print(f"✗ Fallback test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


async def main():
    """Run all configuration tests."""
    print("MODEL CONFIGURATION SYSTEM TESTING")
    print("=" * 60)
    
    # Test configuration loading
    config_works = test_config_loading()
    
    # Test environment variables
    test_environment_variables()
    
    # Test question tool integration (only if config works)
    if config_works:
        await test_question_tool_with_config()
    else:
        print("⚠️  Skipping question tool tests due to config issues")
    
    # Test fallback behavior
    await test_fallback_behavior()
    
    print("\n" + "=" * 60)
    print("CONFIGURATION TESTING COMPLETED")
    
    # Show configuration file location
    try:
        from config import get_model_config
        config = get_model_config()
        print(f"\nConfiguration file: {config.config_path}")
        print("To customize models, edit the configuration file and set environment variables for API keys.")
    except:
        print("\nTo enable configuration, ensure config/models.yaml exists and dependencies are installed.")


if __name__ == "__main__":
    asyncio.run(main())
