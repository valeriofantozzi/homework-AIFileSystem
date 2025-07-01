#!/usr/bin/env python3
"""
Practical example of using the model configuration system.

This script shows how different components of the AI agent would use
the centralized configuration to get their assigned models.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from config import get_model_for_role, set_environment


def example_supervisor():
    """Example: How the supervisor component would get its model."""
    print("=== Supervisor Component ===")
    
    try:
        model_provider = get_model_for_role('supervisor')
        client_params = model_provider.get_client_params()
        
        print(f"Supervisor using: {model_provider.provider_name}:{model_provider.model_name}")
        print(f"This is a {client_params.get('model')} model optimized for safety moderation")
        print(f"Temperature: {client_params.get('temperature')} (low for consistency)")
        print()
        
        # This is how the supervisor would initialize its LLM client:
        """
        if model_provider.provider_name == 'openai':
            from openai import AsyncOpenAI
            client = AsyncOpenAI(**client_params)
        elif model_provider.provider_name == 'anthropic':
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(**client_params)
        # etc.
        """
        
    except Exception as e:
        print(f"Error getting supervisor model: {e}")


def example_agent():
    """Example: How the main agent component would get its model."""
    print("=== Main Agent Component ===")
    
    try:
        model_provider = get_model_for_role('agent')
        client_params = model_provider.get_client_params()
        
        print(f"Agent using: {model_provider.provider_name}:{model_provider.model_name}")
        print(f"This is a {client_params.get('model')} model for complex reasoning")
        print(f"Max tokens: {client_params.get('max_tokens')} (higher for detailed reasoning)")
        print()
        
    except Exception as e:
        print(f"Error getting agent model: {e}")


def example_file_analysis():
    """Example: How file analysis tools would get their model."""
    print("=== File Analysis Tools ===")
    
    try:
        model_provider = get_model_for_role('file_analysis')
        client_params = model_provider.get_client_params()
        
        print(f"File analysis using: {model_provider.provider_name}:{model_provider.model_name}")
        print(f"This is a {client_params.get('model')} model specialized for understanding code")
        print()
        
    except Exception as e:
        print(f"Error getting file analysis model: {e}")


def example_environment_switching():
    """Example: How to switch environments for different deployment scenarios."""
    print("=== Environment Switching ===")
    
    environments = ['development', 'testing', 'production']
    
    for env in environments:
        print(f"\n--- {env.upper()} Environment ---")
        try:
            set_environment(env)
            
            # Show how models change based on environment
            roles_to_check = ['supervisor', 'agent', 'file_analysis']
            
            for role in roles_to_check:
                try:
                    model_provider = get_model_for_role(role)
                    print(f"{role}: {model_provider.provider_name}:{model_provider.model_name}")
                except Exception as e:
                    print(f"{role}: Error - {e}")
                    
        except Exception as e:
            print(f"Error switching to {env}: {e}")
    
    # Reset to production
    set_environment('production')


def example_cost_optimization():
    """Example: How to check costs and optimize usage."""
    print("\n=== Cost Optimization Example ===")
    
    expensive_roles = ['agent', 'code_review', 'documentation']
    fast_roles = ['supervisor', 'file_summary', 'development']
    
    print("High-cost operations (use premium models):")
    for role in expensive_roles:
        try:
            model_provider = get_model_for_role(role)
            print(f"  {role}: {model_provider.provider_name}:{model_provider.model_name}")
        except Exception as e:
            print(f"  {role}: Error - {e}")
    
    print("\nFast/cheap operations (use efficient models):")
    for role in fast_roles:
        try:
            model_provider = get_model_for_role(role)
            print(f"  {role}: {model_provider.provider_name}:{model_provider.model_name}")
        except Exception as e:
            print(f"  {role}: Error - {e}")


def main():
    """Run all examples."""
    print("MODEL CONFIGURATION SYSTEM - PRACTICAL EXAMPLES")
    print("=" * 70)
    
    example_supervisor()
    example_agent()
    example_file_analysis()
    example_environment_switching()
    example_cost_optimization()
    
    print("\n" + "=" * 70)
    print("Key Benefits:")
    print("✓ Centralized configuration - no hardcoded models")
    print("✓ Role-based assignments - right model for each task")
    print("✓ Environment switching - dev/test/prod flexibility")
    print("✓ Cost optimization - fast models for simple tasks")
    print("✓ Provider flexibility - easily switch between OpenAI/Gemini/Anthropic")
    print("✓ Secure API key management - environment variables only")


if __name__ == "__main__":
    main()
