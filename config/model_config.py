"""
Model configuration management for the AI File System Agent.

This module provides centralized configuration for LLM providers, model selection,
and role-based assignments. It supports multiple providers, environment variable
substitution for API keys, and extensible provider architecture.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from .exceptions import (
    ConfigurationError,
    InvalidRoleError,
    MissingApiKeyError,
    ModelNotFoundError,
    ProviderNotFoundError,
)


@dataclass
class ProviderConfig:
    """
    Configuration for a single LLM provider.
    
    Contains provider-specific settings including API keys, endpoints,
    available models, and default parameters.
    """
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    models: Dict[str, str] = field(default_factory=dict)
    default_params: Dict[str, Any] = field(default_factory=dict)
    command: Optional[str] = None  # For CLI-based providers
    
    def get_model(self, model_tier: str) -> str:
        """
        Get model name for a specific tier (fast, standard, advanced).
        
        Args:
            model_tier: The tier of model to retrieve
            
        Returns:
            The actual model name for the provider
            
        Raises:
            ModelNotFoundError: If the model tier is not available
        """
        if model_tier not in self.models:
            available = list(self.models.keys())
            raise ModelNotFoundError(model_tier, self.name, available)
        
        return self.models[model_tier]
    
    def has_valid_api_key(self) -> bool:
        """Check if the provider has a valid API key configured."""
        return bool(self.api_key and self.api_key.strip())


@dataclass  
class ModelProvider:
    """
    Resolved model provider with specific model selection.
    
    Represents a fully resolved provider + model combination
    ready for use by the application components.
    """
    provider_name: str
    model_name: str
    config: ProviderConfig
    
    def get_client_params(self) -> Dict[str, Any]:
        """
        Get parameters for initializing the LLM client.
        
        Returns:
            Dictionary of parameters for the specific provider
        """
        params = self.config.default_params.copy()
        
        # Add provider-specific parameters
        if self.config.api_key:
            params["api_key"] = self.config.api_key
        
        if self.config.base_url:
            params["base_url"] = self.config.base_url
            
        if self.config.command:
            params["command"] = self.config.command
        
        # Add model name
        params["model"] = self.model_name
        
        return params


class ModelConfig:
    """
    Central configuration manager for LLM models and providers.
    
    Manages loading configuration from YAML files, environment variable
    substitution, and providing resolved model configurations for
    different roles within the application.
    """
    
    def __init__(self, config_path: Optional[Path] = None, environment: Optional[str] = None) -> None:
        """
        Initialize model configuration.
        
        Args:
            config_path: Path to the configuration YAML file.
                        If None, looks for config/models.yaml in project root.
            environment: Environment name for environment-specific overrides.
                        If None, uses AI_ENVIRONMENT env var or 'production'.
        """
        self.config_path = config_path or self._find_config_path()
        self.environment = environment or os.getenv("AI_ENVIRONMENT", "production")
        self.config_data: Dict[str, Any] = {}
        self.providers: Dict[str, ProviderConfig] = {}
        self.roles: Dict[str, str] = {}
        
        self._load_config()
        self._validate_config()
    
    def _find_config_path(self) -> Path:
        """Find the configuration file in the project structure."""
        # Look for config/models.yaml from current directory up to project root
        current = Path.cwd()
        
        for parent in [current] + list(current.parents):
            config_file = parent / "config" / "models.yaml"
            if config_file.exists():
                return config_file
        
        # Fallback to expected location
        return Path(__file__).parent / "models.yaml"
    
    def _load_config(self) -> None:
        """Load configuration from YAML file with environment variable substitution."""
        try:
            with open(self.config_path, 'r') as f:
                raw_config = f.read()
            
            # Substitute environment variables
            config_with_env = self._substitute_env_vars(raw_config)
            
            # Parse YAML
            self.config_data = yaml.safe_load(config_with_env)
            
            # Process providers
            self._load_providers()
            
            # Process roles
            self._load_roles()
            
        except FileNotFoundError:
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}",
                str(self.config_path)
            )
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}",
                str(self.config_path)
            )
    
    def _substitute_env_vars(self, config_text: str) -> str:
        """
        Substitute environment variables in configuration text.
        
        Supports ${VAR_NAME} and ${VAR_NAME:-default_value} syntax.
        """
        def replace_var(match):
            var_expr = match.group(1)
            
            if ":-" in var_expr:
                var_name, default = var_expr.split(":-", 1)
                return os.getenv(var_name, default)
            else:
                var_name = var_expr
                value = os.getenv(var_name)
                if value is None:
                    # Keep placeholder for validation later
                    return match.group(0)
                return value
        
        return re.sub(r'\$\{([^}]+)\}', replace_var, config_text)
    
    def _load_providers(self) -> None:
        """Load provider configurations from config data."""
        providers_data = self.config_data.get("providers", {})
        
        for provider_name, provider_data in providers_data.items():
            if provider_name == "local":
                # Handle nested local providers
                for local_provider_name, local_provider_data in provider_data.items():
                    full_name = f"{provider_name}:{local_provider_name}"
                    self.providers[full_name] = ProviderConfig(
                        name=full_name,
                        api_key=local_provider_data.get("api_key"),
                        base_url=local_provider_data.get("base_url"),
                        models=local_provider_data.get("models", {}),
                        default_params=local_provider_data.get("default_params", {}),
                        command=local_provider_data.get("command")
                    )
            else:
                # Handle regular providers
                self.providers[provider_name] = ProviderConfig(
                    name=provider_name,
                    api_key=provider_data.get("api_key"),
                    base_url=provider_data.get("base_url"),
                    models=provider_data.get("models", {}),
                    default_params=provider_data.get("default_params", {}),
                    command=provider_data.get("command")
                )
    
    def _load_roles(self) -> None:
        """Load role assignments from config data with environment-specific overrides."""
        # Start with base roles
        self.roles = self.config_data.get("roles", {}).copy()
        
        # Apply environment-specific overrides
        environments = self.config_data.get("environments", {})
        if self.environment in environments:
            env_config = environments[self.environment]
            
            # Apply environment role overrides
            env_roles = env_config.get("roles", {})
            self.roles.update(env_roles)
            
            # Apply environment default provider if no specific role assignment
            default_provider = env_config.get("default_provider")
            if default_provider:
                for role, assignment in self.roles.items():
                    if ":" not in assignment:
                        # If no provider specified, use environment default
                        self.roles[role] = f"{default_provider}:{assignment}"
        
        # Apply manual overrides (always takes precedence)
        overrides = self.config_data.get("overrides", {})
        self.roles.update(overrides)
    
    def _validate_config(self) -> None:
        """Validate the loaded configuration."""
        if not self.providers:
            raise ConfigurationError("No providers configured")
        
        if not self.roles:
            raise ConfigurationError("No roles configured")
        
        # Validate role assignments reference valid providers
        for role, assignment in self.roles.items():
            try:
                self._parse_model_assignment(assignment)
            except (ProviderNotFoundError, ModelNotFoundError) as e:
                raise ConfigurationError(f"Invalid assignment for role '{role}': {e}")
    
    def _parse_model_assignment(self, assignment: str) -> tuple[str, str]:
        """
        Parse a model assignment string like 'openai:fast' or 'local:gemini_cli:standard'.
        
        Returns:
            Tuple of (provider_name, model_tier)
        """
        parts = assignment.split(":")
        
        if len(parts) < 2:
            raise ConfigurationError(f"Invalid model assignment format: {assignment}")
        
        model_tier = parts[-1]  # Last part is always the model tier
        
        if len(parts) == 2:
            # Simple case: 'provider:tier'
            provider_name = parts[0]
        else:
            # Nested case: 'local:gemini_cli:standard' -> provider = 'local:gemini_cli'
            provider_name = ":".join(parts[:-1])
        
        if provider_name not in self.providers:
            available = list(self.providers.keys())
            raise ProviderNotFoundError(provider_name, available)
        
        return provider_name, model_tier
    
    def get_model_for_role(self, role: str) -> ModelProvider:
        """
        Get the configured model provider for a specific role.
        
        Args:
            role: The role name (e.g., 'orchestrator', 'agent', 'file_analysis')
            
        Returns:
            ModelProvider instance ready for use
            
        Raises:
            InvalidRoleError: If the role is not configured
            ProviderNotFoundError: If the assigned provider is not available
            ModelNotFoundError: If the assigned model is not available
            MissingApiKeyError: If required API key is missing
        """
        if role not in self.roles:
            available_roles = list(self.roles.keys())
            raise InvalidRoleError(role, available_roles)
        
        assignment = self.roles[role]
        provider_name, model_tier = self._parse_model_assignment(assignment)
        
        provider_config = self.providers[provider_name]
        model_name = provider_config.get_model(model_tier)
        
        # Validate API key if required
        if not provider_name.startswith("local") and not provider_config.has_valid_api_key():
            # Try to determine environment variable name
            env_var = f"{provider_name.upper()}_API_KEY"
            raise MissingApiKeyError(provider_name, env_var)
        
        return ModelProvider(
            provider_name=provider_name,
            model_name=model_name,
            config=provider_config
        )
    
    def get_environment(self) -> str:
        """Get the current environment name."""
        return self.environment
    
    def set_environment(self, environment: str) -> None:
        """
        Change the environment and reload roles.
        
        Args:
            environment: New environment name
        """
        self.environment = environment
        self._load_roles()
        self._validate_config()
    
    def get_available_roles(self) -> list[str]:
        """Get list of all configured roles."""
        return list(self.roles.keys())
    
    def get_available_providers(self) -> list[str]:
        """Get list of all configured providers."""
        return list(self.providers.keys())
    
    def get_role_assignment(self, role: str) -> str:
        """Get the current model assignment for a role."""
        return self.roles.get(role, "")
    
    def get_config_info(self) -> dict[str, Any]:
        """Get configuration summary for debugging."""
        return {
            "environment": self.environment,
            "config_path": str(self.config_path),
            "providers": list(self.providers.keys()),
            "roles": self.roles.copy(),
            "features": self.config_data.get("features", {}),
            "limits": self.config_data.get("limits", {})
        }
