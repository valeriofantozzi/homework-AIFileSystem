#!/usr/bin/env python3
"""
Simple environment management CLI.

Provides basic commands for setting up and managing environment configurations
without complex dependencies. Follows high-cohesion, low-coupling principles.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


def find_project_root() -> Path:
    """Find project root by looking for config directory."""
    current = Path.cwd()
    
    for parent in [current] + list(current.parents):
        if (parent / "config").exists():
            return parent
    
    return current


def setup_env_file(environment: str, force: bool = False) -> None:
    """
    Setup environment file from template.
    
    Args:
        environment: Environment name
        force: Overwrite existing file
    """
    project_root = find_project_root()
    
    if environment == "local":
        template_file = project_root / "config" / "env" / ".env.local.template"
        target_file = project_root / "config" / ".env.local"
    else:
        template_file = project_root / "config" / "env" / f".env.{environment}.template"
        target_file = project_root / "config" / f".env.{environment}"
    
    if not template_file.exists():
        print(f"❌ Template not found: {template_file}")
        sys.exit(1)
    
    if target_file.exists() and not force:
        print(f"⚠️  Environment file already exists: {target_file}")
        print("   Use --force to overwrite")
        return
    
    # Copy template to target
    shutil.copy2(template_file, target_file)
    print(f"✅ Created environment file: {target_file}")
    print(f"📝 Edit this file and add your API keys")
    
    if environment == "local":
        print("\n🔑 Get your API keys from:")
        print("   - OpenAI: https://platform.openai.com/api-keys")
        print("   - Gemini: https://aistudio.google.com/app/apikey")


def validate_env_file(environment: str) -> None:
    """Validate environment file exists and has required keys."""
    project_root = find_project_root()
    
    if environment == "local":
        env_file = project_root / "config" / ".env.local"
    else:
        env_file = project_root / "config" / f".env.{environment}"
    
    if not env_file.exists():
        print(f"❌ Environment file not found: {env_file}")
        print(f"   Run: python manage_env.py setup {environment}")
        return
    
    # Read and check for empty API keys
    with open(env_file, 'r') as f:
        content = f.read()
    
    required_keys = ["OPENAI_API_KEY"]
    missing_keys = []
    
    for key in required_keys:
        if f"{key}=" in content:
            # Extract value after =
            lines = content.split('\n')
            for line in lines:
                if line.startswith(f"{key}="):
                    value = line.split('=', 1)[1].strip()
                    if not value or value.endswith('-here'):
                        missing_keys.append(key)
                    break
        else:
            missing_keys.append(key)
    
    if missing_keys:
        print(f"⚠️  Missing or incomplete API keys in {env_file}:")
        for key in missing_keys:
            print(f"   - {key}")
        print(f"\n📝 Edit {env_file} and add your API keys")
    else:
        print(f"✅ Environment file {env_file} is properly configured")


def list_environments() -> None:
    """List available environment templates and files."""
    project_root = find_project_root()
    
    print("📋 Available Environment Templates:")
    templates = list((project_root / "config" / "env").glob(".env.*.template"))
    for template in sorted(templates):
        env_name = template.stem.replace('.env.', '')
        if env_name.endswith('.template'):
            env_name = env_name.replace('.template', '')
        print(f"   - {env_name}")
    
    print("\n📁 Existing Environment Files:")
    env_files = [f for f in (project_root / "config").glob(".env.*") if not f.name.endswith('.template')]
    if env_files:
        for env_file in sorted(env_files):
            env_name = env_file.name.replace('.env.', '')
            status = "✅" if env_file.stat().st_size > 100 else "⚠️"
            print(f"   {status} {env_name}")
    else:
        print("   (none found)")


def show_help() -> None:
    """Show usage help."""
    print("""
Environment Management CLI

Usage:
    python manage_env.py setup <environment>    # Setup environment from template
    python manage_env.py validate <environment> # Validate environment file
    python manage_env.py list                   # List available environments
    python manage_env.py help                   # Show this help

Examples:
    python manage_env.py setup local            # Quick local development setup
    python manage_env.py setup development      # Full development environment
    python manage_env.py validate local         # Check if local env is configured
    python manage_env.py list                   # See all available environments

Environments:
    local       - Quick setup for local development
    development - Full development with all providers
    testing     - Testing with local models
    production  - Production deployment
""")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Manage environment configuration")
    parser.add_argument("command", choices=["setup", "validate", "list", "help"])
    parser.add_argument("environment", nargs='?', help="Environment name")
    parser.add_argument("--force", action="store_true", help="Force overwrite existing files")
    
    args = parser.parse_args()
    
    if args.command == "help":
        show_help()
    elif args.command == "list":
        list_environments()
    elif args.command == "setup":
        if not args.environment:
            print("❌ Environment name required for setup")
            print("   Available: local, development, testing, production")
            sys.exit(1)
        setup_env_file(args.environment, args.force)
    elif args.command == "validate":
        if not args.environment:
            print("❌ Environment name required for validation")
            sys.exit(1)
        validate_env_file(args.environment)


if __name__ == "__main__":
    main()
