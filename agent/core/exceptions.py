"""
Agent-specific exceptions for enhanced error handling and user experience.

This module provides specialized error types for different agent failure modes,
enabling precise error handling and user-friendly recovery suggestions.
"""

from typing import Optional, List, Dict, Any


class AgentError(Exception):
    """Base exception for all agent-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        recovery_suggestions: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Initialize agent error with enhanced context.
        
        Args:
            message: Human-readable error description
            error_code: Machine-readable error code for categorization
            recovery_suggestions: List of actionable recovery steps
            context: Additional context for debugging
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.recovery_suggestions = recovery_suggestions or []
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for structured logging."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "recovery_suggestions": self.recovery_suggestions,
            "context": self.context
        }


class AgentInitializationError(AgentError):
    """Raised when agent fails to initialize properly."""
    
    def __init__(self, message: str, component: Optional[str] = None) -> None:
        recovery_suggestions = [
            "Check workspace path permissions",
            "Verify model configuration",
            "Ensure required dependencies are installed",
            "Review environment variables and API keys"
        ]
        
        context = {"component": component} if component else {}
        
        super().__init__(
            message=message,
            error_code="AGENT_INIT_FAILED",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class ModelConfigurationError(AgentError):
    """Raised when model configuration is invalid or unavailable."""
    
    def __init__(self, message: str, model_name: Optional[str] = None, provider: Optional[str] = None) -> None:
        recovery_suggestions = [
            "Check model configuration in models.yaml",
            "Verify API keys are properly configured",
            "Ensure the model is available in the specified provider",
            "Try using a different model or provider"
        ]
        
        context = {}
        if model_name:
            context["model_name"] = model_name
        if provider:
            context["provider"] = provider
            
        super().__init__(
            message=message,
            error_code="MODEL_CONFIG_ERROR",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class ToolExecutionError(AgentError):
    """Raised when tool execution fails."""
    
    def __init__(
        self, 
        message: str, 
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        recovery_suggestions = [
            "Verify tool arguments are correct",
            "Check if required files exist",
            "Ensure proper permissions",
            "Try with different parameters"
        ]
        
        # Add tool-specific suggestions
        if tool_name:
            tool_suggestions = self._get_tool_specific_suggestions(tool_name)
            recovery_suggestions.extend(tool_suggestions)
        
        context = {}
        if tool_name:
            context["tool_name"] = tool_name
        if tool_args:
            context["tool_args"] = tool_args
        if original_error:
            context["original_error"] = str(original_error)
            context["original_error_type"] = type(original_error).__name__
            
        super().__init__(
            message=message,
            error_code="TOOL_EXECUTION_FAILED",
            recovery_suggestions=recovery_suggestions,
            context=context
        )
    
    @staticmethod
    def _get_tool_specific_suggestions(tool_name: str) -> List[str]:
        """Get tool-specific recovery suggestions."""
        suggestions_map = {
            "list_files": [
                "Check if workspace directory is accessible",
                "Verify directory permissions"
            ],
            "read_file": [
                "Verify the file exists using list_files first",
                "Check file permissions and accessibility",
                "Ensure filename doesn't contain special characters"
            ],
            "write_file": [
                "Check if you have write permissions",
                "Verify disk space is available",
                "Ensure parent directory exists"
            ],
            "delete_file": [
                "Confirm the file exists before deletion",
                "Check if file is in use by another process",
                "Verify you have delete permissions"
            ],
            "answer_question_about_files": [
                "Ensure files exist in the workspace",
                "Try asking more specific questions",
                "Check if the workspace contains relevant files"
            ]
        }
        return suggestions_map.get(tool_name, [])


class ReasoningError(AgentError):
    """Raised when agent's reasoning process fails."""
    
    def __init__(self, message: str, reasoning_step: Optional[str] = None) -> None:
        recovery_suggestions = [
            "Try rephrasing your question",
            "Break down complex requests into simpler steps",
            "Provide more specific context",
            "Check if the request is within agent capabilities"
        ]
        
        context = {"reasoning_step": reasoning_step} if reasoning_step else {}
        
        super().__init__(
            message=message,
            error_code="REASONING_FAILED",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class SafetyViolationError(AgentError):
    """Raised when request violates safety policies."""
    
    def __init__(
        self, 
        message: str, 
        violation_type: Optional[str] = None,
        risk_factors: Optional[List[str]] = None
    ) -> None:
        recovery_suggestions = [
            "Rephrase your request to focus on legitimate file operations",
            "Avoid requests that could be harmful or unsafe",
            "Ensure your request is within the agent's scope",
            "Contact support if you believe this is an error"
        ]
        
        context = {}
        if violation_type:
            context["violation_type"] = violation_type
        if risk_factors:
            context["risk_factors"] = risk_factors
            
        super().__init__(
            message=message,
            error_code="SAFETY_VIOLATION",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class ConversationError(AgentError):
    """Raised when conversation management fails."""
    
    def __init__(self, message: str, conversation_id: Optional[str] = None) -> None:
        recovery_suggestions = [
            "Try starting a new conversation",
            "Check conversation session state",
            "Verify conversation ID is valid",
            "Clear conversation history if corrupted"
        ]
        
        context = {"conversation_id": conversation_id} if conversation_id else {}
        
        super().__init__(
            message=message,
            error_code="CONVERSATION_FAILED",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class RateLimitError(AgentError):
    """Raised when rate limits are exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None) -> None:
        recovery_suggestions = [
            "Wait before making another request",
            "Reduce request frequency",
            "Batch multiple operations if possible",
            "Check rate limit configuration"
        ]
        
        if retry_after:
            recovery_suggestions.insert(0, f"Wait {retry_after} seconds before retrying")
        
        context = {"retry_after": retry_after} if retry_after else {}
        
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            recovery_suggestions=recovery_suggestions,
            context=context
        )


class ErrorFormatter:
    """Formats errors for user-friendly display."""
    
    @staticmethod
    def format_error_for_user(error: AgentError) -> str:
        """Format error for user display with recovery suggestions."""
        formatted = f"❌ **Error**: {error.message}\n"
        
        if error.recovery_suggestions:
            formatted += "\n💡 **Suggestions**:\n"
            for i, suggestion in enumerate(error.recovery_suggestions, 1):
                formatted += f"   {i}. {suggestion}\n"
        
        return formatted
    
    @staticmethod
    def format_error_for_debug(error: AgentError) -> str:
        """Format error for debug display with full context."""
        formatted = f"❌ **Error**: {error.message}\n"
        formatted += f"📋 **Code**: {error.error_code}\n"
        formatted += f"🔧 **Type**: {error.__class__.__name__}\n"
        
        if error.context:
            formatted += f"\n🔍 **Context**:\n"
            for key, value in error.context.items():
                formatted += f"   • {key}: {value}\n"
        
        if error.recovery_suggestions:
            formatted += "\n💡 **Recovery Suggestions**:\n"
            for i, suggestion in enumerate(error.recovery_suggestions, 1):
                formatted += f"   {i}. {suggestion}\n"
        
        return formatted
