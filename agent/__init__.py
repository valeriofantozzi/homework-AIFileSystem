"""
Agent package for autonomous file system operations.

This package contains the core agent logic and orchestration components.
"""

from .core.secure_agent import SecureAgent, AgentResponse, ConversationContext

__all__ = ["SecureAgent", "AgentResponse", "ConversationContext"]

# TODO: Import and register the five tools for later phases
