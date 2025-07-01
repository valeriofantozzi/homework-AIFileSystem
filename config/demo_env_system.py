#!/usr/bin/env python3
"""
Example usage of the environment management system.

This demonstrates how the environment templates and loader work together
to provide a complete configuration management solution.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.env_loader import load_env_for_context, get_env_loader
from config import get_model_for_role, set_environment


def demonstrate_environment_switching():
    """Demonstrate environment switching capabilities."""
    print("🔄 ENVIRONMENT SWITCHING DEMONSTRATION")
    print("=" * 60)
    
    environments = ['development', 'testing', 'production']
    
    for env in environments:
        print(f"\n--- {env.upper()} Environment ---")
        
        try:
            # Load environment
            load_env_for_context(env)
            set_environment(env)
            
            loader = get_env_loader()
            
            # Show environment info
            print(f"✅ Environment: {loader.get_current_environment()}")
            print(f"📁 Loaded files: {len(loader.get_loaded_files())}")
            
            # Show API key status
            api_status = loader.validate_api_keys()
            print("🔑 API Keys:")
            for provider, available in api_status.items():
                status = "✅" if available else "❌"
                print(f"   {status} {provider}")
            
            # Show model assignments
            print("🤖 Model assignments:")
            try:
                roles = ['orchestrator', 'agent', 'file_analysis']
                for role in roles:
                    model = get_model_for_role(role)
                    print(f"   {role}: {model.provider_name}:{model.model_name}")
            except Exception as e:
                print(f"   Error getting models: {e}")
                
        except Exception as e:
            print(f"❌ Error loading {env}: {e}")


def show_template_info():
    """Show information about available templates."""
    print("\n📋 AVAILABLE ENVIRONMENT TEMPLATES")
    print("=" * 60)
    
    templates = {
        ".env.local.template": {
            "purpose": "Quick local development setup",
            "features": ["Minimal configuration", "Essential API keys only", "Quick start instructions"],
            "use_case": "New developers, quick prototyping"
        },
        ".env.development.template": {
            "purpose": "Full development environment",
            "features": ["All provider support", "Cost optimization", "Debug settings", "Local model integration"],
            "use_case": "Active development, feature work"
        },
        ".env.testing.template": {
            "purpose": "Automated testing environment",
            "features": ["Local models preferred", "Mock responses", "No API costs", "CI/CD ready"],
            "use_case": "Unit tests, integration tests, CI/CD"
        },
        ".env.production.template": {
            "purpose": "Production deployment",
            "features": ["Security hardened", "Monitoring enabled", "Cost tracking", "High availability"],
            "use_case": "Production deployments, staging"
        }
    }
    
    for template, info in templates.items():
        print(f"\n📄 {template}")
        print(f"   Purpose: {info['purpose']}")
        print(f"   Use case: {info['use_case']}")
        print("   Features:")
        for feature in info['features']:
            print(f"     • {feature}")


def show_quick_start_guide():
    """Show quick start guide for new users."""
    print("\n🚀 QUICK START GUIDE")
    print("=" * 60)
    
    steps = [
        {
            "step": "1. Setup your environment",
            "command": "python config/manage_env.py setup local",
            "description": "Creates .env.local from template"
        },
        {
            "step": "2. Add your API keys",
            "command": "nano config/.env.local",
            "description": "Edit the file and add your OpenAI API key"
        },
        {
            "step": "3. Validate configuration",
            "command": "python config/manage_env.py validate local",
            "description": "Check that your API keys are properly set"
        },
        {
            "step": "4. Test the system",
            "command": "python -c \"from config import get_model_for_role; print(get_model_for_role('agent'))\"",
            "description": "Verify that model configuration works"
        }
    ]
    
    for step_info in steps:
        print(f"\n{step_info['step']}")
        print(f"   Command: {step_info['command']}")
        print(f"   Description: {step_info['description']}")
    
    print(f"\n🔑 Get API keys from:")
    print(f"   • OpenAI: https://platform.openai.com/api-keys")
    print(f"   • Gemini: https://aistudio.google.com/app/apikey")
    print(f"   • Anthropic: https://console.anthropic.com/account/keys")
    print(f"   • Groq: https://console.groq.com/keys")


def show_architecture_benefits():
    """Show how the system follows architectural principles."""
    print("\n🏗️ ARCHITECTURE BENEFITS")
    print("=" * 60)
    
    principles = {
        "High Cohesion": [
            "Each environment template has a single purpose",
            "EnvironmentLoader only manages environment variables",
            "Clear separation between templates and logic"
        ],
        "Low Coupling": [
            "Environment config independent of application code",
            "No hardcoded API keys or environment logic",
            "Easy to add new providers without code changes"
        ],
        "Security": [
            "API keys externalized from codebase",
            "Environment isolation prevents key leakage",
            "Templates provide secure defaults"
        ],
        "SOLID Principles": [
            "Single Responsibility: Each template serves one environment",
            "Open/Closed: Easy to add new environments",
            "Dependency Inversion: Depends on abstractions (env vars)"
        ]
    }
    
    for principle, benefits in principles.items():
        print(f"\n✅ {principle}:")
        for benefit in benefits:
            print(f"   • {benefit}")


def main():
    """Run the demonstration."""
    print("ENVIRONMENT MANAGEMENT SYSTEM DEMONSTRATION")
    print("=" * 70)
    
    show_template_info()
    demonstrate_environment_switching()
    show_quick_start_guide()
    show_architecture_benefits()
    
    print("\n" + "=" * 70)
    print("🎯 SUMMARY")
    print("• Environment templates provide secure, structured configuration")
    print("• CLI tools make setup and validation simple")
    print("• Architecture follows high-cohesion, low-coupling principles") 
    print("• Security through externalized configuration")
    print("• Easy environment switching for dev/test/prod workflows")


if __name__ == "__main__":
    main()
