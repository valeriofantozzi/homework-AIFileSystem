"""
Model configuration system for AI File System Agent.

This module provides centralized configuration management for LLM providers
and role-based model assignments, supporting multiple providers and
environment-based API key management.
"""

__version__ = "0.1.0"

from .model_config import ModelConfig, ModelProvider, ProviderConfig
from .exceptions import ConfigurationError, ModelNotFoundError, ProviderNotFoundError
from .env_loader import load_env_for_context, get_env_loader

# Global configuration instance - lazy loaded for efficiency
_global_config: ModelConfig | None = None

def get_model_config() -> ModelConfig:
    """
    Get the global model configuration instance.
    
    Lazy-loads the configuration on first access to avoid
    circular imports and unnecessary startup overhead.
    
    Returns:
        Global ModelConfig instance
    """
    global _global_config
    if _global_config is None:
        _global_config = ModelConfig()
    return _global_config

def get_model_for_role(role: str) -> ModelProvider:
    """
    Convenience function to get model configuration for a role.
    
    This is the primary function that components should use to obtain
    their configured LLM model. It handles all the complexity of
    provider resolution, environment overrides, and API key validation.
    
    Args:
        role: The role name (e.g., 'file_analysis', 'supervisor', 'agent')
        
    Returns:
        ModelProvider ready for use with LLM clients
        
    Example:
        >>> model = get_model_for_role('file_analysis')
        >>> client_params = model.get_client_params()
        >>> # Use client_params to initialize your LLM client
    """
    config = get_model_config()
    return config.get_model_for_role(role)

def set_environment(environment: str) -> None:
    """
    Set the environment for model configuration.
    
    Changes the active environment which affects model selection
    through environment-specific overrides defined in models.yaml.
    
    Args:
        environment: Environment name ('development', 'testing', 'production')
    """
    config = get_model_config()
    config.set_environment(environment)

__all__ = [
    "ModelConfig",
    "ModelProvider", 
    "ProviderConfig",
    "ConfigurationError",
    "ModelNotFoundError",
    "ProviderNotFoundError",
    "get_model_config",
    "get_model_for_role", 
    "set_environment",
    "load_env_for_context",
    "get_env_loader",
]
