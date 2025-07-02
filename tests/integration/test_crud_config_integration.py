#!/usr/bin/env python3
"""
Test script for model configuration system integration.

This script demonstrates how different components can use the centralized
model configuration to get their assigned models and providers.
"""

import asyncio
import tempfile
import os
from pathlib import Path

# Add the project root to Python path for imports
import sys
project_root = Path(__file__).parent.parent.parent  # Go up to project root
sys.path.insert(0, str(project_root))

from workspace_fs import Workspace
from crud_tools.gemini_adapter import create_gemini_question_tool

try:
    from config import get_model_for_role, get_model_config, set_environment
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    print("⚠️  Configuration system not available - using fallback behavior")


def test_config_system():
    """Test the model configuration system."""
    print("=== Testing Model Configuration System ===")
    
    if not CONFIG_AVAILABLE:
        print("❌ Configuration system not available")
        return
    
    try:
        # Test getting model configuration
        config = get_model_config()
        print(f"✓ Configuration loaded from: {config.config_path}")
        print(f"✓ Current environment: {config.get_environment()}")
        
        # Test role assignments
        roles_to_test = ['supervisor', 'agent', 'file_analysis', 'chat']
        
        for role in roles_to_test:
            try:
                model_provider = get_model_for_role(role)
                print(f"✓ {role}: {model_provider.provider_name}:{model_provider.model_name}")
                
                # Show client parameters (without sensitive data)
                params = model_provider.get_client_params()
                safe_params = {k: v for k, v in params.items() if 'key' not in k.lower()}
                print(f"  Parameters: {safe_params}")
                
            except Exception as e:
                print(f"✗ {role}: Error - {e}")
        
        # Test environment switching
        print(f"\n--- Testing Environment Switching ---")
        original_env = config.get_environment()
        
        for env in ['development', 'testing', 'production']:
            try:
                set_environment(env)
                file_analysis_model = get_model_for_role('file_analysis')
                print(f"✓ {env}: file_analysis -> {file_analysis_model.provider_name}:{file_analysis_model.model_name}")
            except Exception as e:
                print(f"✗ {env}: Error - {e}")
        
        # Restore original environment
        set_environment(original_env)
        
    except Exception as e:
        print(f"✗ Configuration system error: {e}")


async def test_gemini_with_config():
    """Test Gemini adapter with configuration system."""
    print("\n=== Testing Gemini Adapter with Configuration ===")
    
    temp_dir = tempfile.mkdtemp()
    workspace = Workspace(temp_dir)
    
    try:
        from workspace_fs import FileSystemTools
        fs_tools = FileSystemTools(workspace)
        
        # Create test files
        fs_tools.write_file("test.py", "def hello(): return 'Hello from config test!'")
        fs_tools.write_file("config.json", '{"test": true, "environment": "testing"}')
        
        # Test with different configurations
        test_scenarios = [
            {"role": "file_analysis", "description": "Default file analysis role"},
            {"role": "development", "description": "Development role"},
            {"gemini_model": "gemini-2.5-pro", "description": "Explicit model override"},
        ]
        
        for scenario in test_scenarios:
            try:
                description = scenario.pop("description")
                print(f"\n--- {description} ---")
                
                question_tool = create_gemini_question_tool(workspace, **scenario)
                response = await question_tool("What files are in this project?")
                
                print(f"✓ Response: {response[:100]}...")
                
            except Exception as e:
                print(f"✗ Error with {description}: {e}")
        
    except Exception as e:
        print(f"✗ Gemini integration test failed: {e}")
        
    finally:
        import shutil
        shutil.rmtree(temp_dir)


def test_environment_variables():
    """Test environment variable handling."""
    print("\n=== Testing Environment Variables ===")
    
    # Test common environment variables
    env_vars_to_check = [
        'OPENAI_API_KEY',
        'GEMINI_API_KEY', 
        'ANTHROPIC_API_KEY',
        'GROQ_API_KEY',
        'AI_ENVIRONMENT'
    ]
    
    for var in env_vars_to_check:
        value = os.getenv(var)
        if value:
            # Show only first and last 4 chars for security
            if len(value) > 8:
                display_value = f"{value[:4]}...{value[-4:]}"
            else:
                display_value = "***"
            print(f"✓ {var}: {display_value}")
        else:
            print(f"⚠️  {var}: Not set")


def test_config_info():
    """Display configuration information."""
    print("\n=== Configuration Information ===")
    
    if not CONFIG_AVAILABLE:
        print("❌ Configuration system not available")
        return
    
    try:
        config = get_model_config()
        info = config.get_config_info()
        
        print(f"Environment: {info['environment']}")
        print(f"Config Path: {info['config_path']}")
        print(f"Available Providers: {', '.join(info['providers'])}")
        print(f"Available Roles: {', '.join(info['roles'].keys())}")
        
        if 'features' in info:
            print(f"Features: {info['features']}")
        
        if 'limits' in info:
            print(f"Limits: {info['limits']}")
            
    except Exception as e:
        print(f"✗ Failed to get config info: {e}")


async def main():
    """Run all configuration tests."""
    print("MODEL CONFIGURATION SYSTEM TESTING")
    print("=" * 60)
    
    test_environment_variables()
    test_config_system()
    test_config_info()
    await test_gemini_with_config()
    
    print("\n" + "=" * 60)
    print("CONFIGURATION TESTING COMPLETED")


if __name__ == "__main__":
    asyncio.run(main())
