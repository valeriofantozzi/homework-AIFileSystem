"""
Configuration exceptions for the model configuration system.

Provides specific exception types for configuration-related errors,
allowing precise error handling and user-friendly error messages.
"""


class ConfigurationError(Exception):
    """Base exception for all configuration-related errors."""
    
    def __init__(self, message: str, config_path: str | None = None) -> None:
        """
        Initialize configuration error.
        
        Args:
            message: Error description
            config_path: Path to the configuration file that caused the error
        """
        self.message = message
        self.config_path = config_path
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """Format the error message with optional config path."""
        if self.config_path:
            return f"{self.message} (config: {self.config_path})"
        return self.message


class ProviderNotFoundError(ConfigurationError):
    """Raised when a requested LLM provider is not configured."""
    
    def __init__(self, provider_name: str, available_providers: list[str] | None = None) -> None:
        """
        Initialize provider not found error.
        
        Args:
            provider_name: Name of the missing provider
            available_providers: List of available providers for suggestions
        """
        self.provider_name = provider_name
        self.available_providers = available_providers or []
        
        message = f"Provider '{provider_name}' not found"
        if self.available_providers:
            message += f". Available providers: {', '.join(self.available_providers)}"
        
        super().__init__(message)


class ModelNotFoundError(ConfigurationError):
    """Raised when a requested model is not available in a provider."""
    
    def __init__(
        self, 
        model_name: str, 
        provider_name: str, 
        available_models: list[str] | None = None
    ) -> None:
        """
        Initialize model not found error.
        
        Args:
            model_name: Name of the missing model
            provider_name: Name of the provider
            available_models: List of available models for suggestions
        """
        self.model_name = model_name
        self.provider_name = provider_name
        self.available_models = available_models or []
        
        message = f"Model '{model_name}' not found in provider '{provider_name}'"
        if self.available_models:
            message += f". Available models: {', '.join(self.available_models)}"
        
        super().__init__(message)


class InvalidRoleError(ConfigurationError):
    """Raised when an invalid role is requested."""
    
    def __init__(self, role_name: str, available_roles: list[str] | None = None) -> None:
        """
        Initialize invalid role error.
        
        Args:
            role_name: Name of the invalid role
            available_roles: List of valid roles for suggestions
        """
        self.role_name = role_name
        self.available_roles = available_roles or []
        
        message = f"Role '{role_name}' is not defined"
        if self.available_roles:
            message += f". Available roles: {', '.join(self.available_roles)}"
        
        super().__init__(message)


class MissingApiKeyError(ConfigurationError):
    """Raised when an API key is required but not available."""
    
    def __init__(self, provider_name: str, env_var_name: str) -> None:
        """
        Initialize missing API key error.
        
        Args:
            provider_name: Name of the provider requiring the API key
            env_var_name: Name of the environment variable for the API key
        """
        self.provider_name = provider_name
        self.env_var_name = env_var_name
        
        message = (
            f"API key required for provider '{provider_name}'. "
            f"Please set the environment variable '{env_var_name}'"
        )
        
        super().__init__(message)
