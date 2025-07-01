"""
Environment variable loader for different deployment environments.

This module provides high-cohesion environment management with secure API key
loading and environment-specific configuration without coupling to specific providers.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, List

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class EnvironmentLoader:
    """
    Loads environment-specific configuration with secure API key management.
    
    High Cohesion: Single responsibility for environment variable management
    Low Coupling: No dependencies on specific LLM providers or configurations
    """
    
    def __init__(self, project_root: Optional[Path] = None) -> None:
        """
        Initialize environment loader.
        
        Args:
            project_root: Root directory to search for .env files
        """
        self.project_root = project_root or self._find_project_root()
        self.current_env: Optional[str] = None
        self.loaded_files: List[Path] = []
    
    def _find_project_root(self) -> Path:
        """Find project root by looking for config directory."""
        current = Path.cwd()
        
        for parent in [current] + list(current.parents):
            if (parent / "config").exists():
                return parent
        
        return current
    
    def load_environment(self, environment: str) -> None:
        """
        Load environment-specific variables.
        
        Strategy: Load base .env first, then environment-specific overrides.
        This allows shared configuration with environment-specific API keys.
        
        Args:
            environment: Environment name ('development', 'testing', 'production')
        """
        self.loaded_files.clear()
        
        if not DOTENV_AVAILABLE:
            # Fallback to system environment variables
            os.environ.setdefault("AI_ENVIRONMENT", environment)
            self.current_env = environment
            return
        
        # Load base .env file first (shared configuration)
        base_env_file = self.project_root / "config" / ".env"
        if base_env_file.exists():
            load_dotenv(base_env_file)
            self.loaded_files.append(base_env_file)
        
        # Load environment-specific file (overrides base configuration)
        env_file = self.project_root / "config" / f".env.{environment}"
        if env_file.exists():
            load_dotenv(env_file, override=True)
            self.loaded_files.append(env_file)
        
        # Set the environment variable
        os.environ["AI_ENVIRONMENT"] = environment
        self.current_env = environment
    
    def get_current_environment(self) -> str:
        """Get the currently loaded environment."""
        return self.current_env or os.getenv("AI_ENVIRONMENT", "production")
    
    def get_loaded_files(self) -> List[Path]:
        """Get list of loaded .env files for debugging."""
        return self.loaded_files.copy()
    
    def validate_api_keys(self) -> Dict[str, bool]:
        """
        Validate that required API keys are available.
        
        Returns:
            Dictionary mapping provider names to availability status
        """
        required_keys = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY", 
            "anthropic": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY"
        }
        
        return {
            provider: bool(os.getenv(env_var) and len(os.getenv(env_var).strip()) > 0)
            for provider, env_var in required_keys.items()
        }
    
    def get_missing_keys(self) -> List[str]:
        """Get list of missing API keys for current environment."""
        validation = self.validate_api_keys()
        return [provider for provider, available in validation.items() if not available]
    
    def get_api_key_info(self) -> Dict[str, str]:
        """
        Get API key information for debugging (masked for security).
        
        Returns:
            Dictionary with masked API key values
        """
        keys = {
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
            "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        }
        
        # Mask keys for security (show first 8 and last 4 chars)
        masked_keys = {}
        for key, value in keys.items():
            if value and len(value) > 12:
                masked_keys[key] = f"{value[:8]}...{value[-4:]}"
            elif value:
                masked_keys[key] = "***"
            else:
                masked_keys[key] = "Not set"
        
        return masked_keys
    
    def create_env_template(self, environment: str, target_path: Optional[Path] = None) -> Path:
        """
        Create a template .env file for the specified environment.
        
        Args:
            environment: Environment name
            target_path: Optional custom path for the template
            
        Returns:
            Path to the created template file
        """
        if target_path is None:
            target_path = self.project_root / "config" / "env" / f".env.{environment}.template"
        
        template_content = self._get_env_template_content(environment)
        
        with open(target_path, 'w') as f:
            f.write(template_content)
        
        return target_path
    
    def _get_env_template_content(self, environment: str) -> str:
        """Generate environment-specific template content."""
        # Base template content varies by environment
        templates = {
            "development": self._get_development_template(),
            "testing": self._get_testing_template(),
            "production": self._get_production_template()
        }
        
        return templates.get(environment, self._get_base_template())
    
    def _get_base_template(self) -> str:
        """Get base template content."""
        return """# Environment Configuration Template
# Copy this file to .env.{environment} and fill in your API keys

# Environment identifier
AI_ENVIRONMENT=base

# LLM Provider API Keys
# Get these from your provider dashboards:
# - OpenAI: https://platform.openai.com/api-keys
# - Gemini: https://aistudio.google.com/app/apikey
# - Anthropic: https://console.anthropic.com/account/keys
# - Groq: https://console.groq.com/keys

OPENAI_API_KEY=sk-your-openai-key-here
GEMINI_API_KEY=your-gemini-key-here
ANTHROPIC_API_KEY=your-anthropic-key-here
GROQ_API_KEY=your-groq-key-here

# Optional: Local model configurations
OLLAMA_HOST=http://localhost:11434
"""
    
    def _get_development_template(self) -> str:
        """Get development environment template."""
        return """# Development Environment Configuration
# Use cheaper/faster models for development work

# Environment identifier
AI_ENVIRONMENT=development

# LLM Provider API Keys for Development
# You can use the same keys as production, or separate dev keys if available

OPENAI_API_KEY=sk-your-dev-openai-key-here
GEMINI_API_KEY=your-dev-gemini-key-here
ANTHROPIC_API_KEY=your-dev-anthropic-key-here
GROQ_API_KEY=your-dev-groq-key-here

# Development-specific settings
DEBUG=true
LOG_LEVEL=debug

# Optional: Local development tools
OLLAMA_HOST=http://localhost:11434
"""
    
    def _get_testing_template(self) -> str:
        """Get testing environment template."""
        return """# Testing Environment Configuration
# Use local models when possible to avoid API costs during testing

# Environment identifier
AI_ENVIRONMENT=testing

# API Keys (optional for testing with local models)
# Only needed if testing with actual API providers
# OPENAI_API_KEY=sk-your-test-openai-key-here
# GEMINI_API_KEY=your-test-gemini-key-here

# Local model configurations (preferred for testing)
OLLAMA_HOST=http://localhost:11434
GEMINI_CLI_PATH=gemini

# Testing-specific settings
RUN_INTEGRATION_TESTS=false
MOCK_LLM_RESPONSES=true
"""
    
    def _get_production_template(self) -> str:
        """Get production environment template."""
        return """# Production Environment Configuration
# Use production-grade API keys and settings

# Environment identifier
AI_ENVIRONMENT=production

# Production LLM Provider API Keys
# Use dedicated production keys with appropriate rate limits
OPENAI_API_KEY=sk-your-production-openai-key-here
GEMINI_API_KEY=your-production-gemini-key-here
ANTHROPIC_API_KEY=your-production-anthropic-key-here
GROQ_API_KEY=your-production-groq-key-here

# Production settings
DEBUG=false
LOG_LEVEL=info

# Monitoring and observability
ENABLE_TELEMETRY=true
ENABLE_COST_TRACKING=true

# Security settings
MAX_REQUEST_SIZE=10MB
RATE_LIMIT_ENABLED=true
"""


# Global instance for easy access
_env_loader: Optional[EnvironmentLoader] = None

def get_env_loader() -> EnvironmentLoader:
    """
    Get global environment loader instance.
    
    Lazy-loads for efficiency and to avoid circular imports.
    """
    global _env_loader
    if _env_loader is None:
        _env_loader = EnvironmentLoader()
    return _env_loader

def load_env_for_context(environment: str) -> None:
    """
    Load environment variables for specific context.
    
    Primary function for switching environments throughout the application.
    
    Args:
        environment: Environment to load ('development', 'testing', 'production')
    """
    loader = get_env_loader()
    loader.load_environment(environment)

def create_all_env_templates(target_dir: Optional[Path] = None) -> List[Path]:
    """
    Create all environment template files.
    
    Args:
        target_dir: Directory to create templates in (defaults to project root)
        
    Returns:
        List of created template file paths
    """
    loader = get_env_loader()
    environments = ['development', 'testing', 'production']
    
    created_files = []
    for env in environments:
        template_path = loader.create_env_template(env, target_dir)
        created_files.append(template_path)
    
    return created_files
