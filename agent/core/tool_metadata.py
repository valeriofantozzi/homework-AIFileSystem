"""
Tool metadata registry and introspection system.

This module provides a standardized way for tools to self-describe their
capabilities, following the principle that each tool should know its own
purpose and interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Protocol, Union, Callable
from dataclasses import dataclass


@dataclass
class ToolMetadata:
    """Metadata description for a tool."""
    name: str
    description: str
    parameters: Dict[str, str]
    examples: list[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for serialization."""
        return {
            "description": self.description,
            "parameters": self.parameters,
            "examples": self.examples or []
        }


class SelfDescribingTool(Protocol):
    """Protocol for tools that can describe themselves."""
    
    def get_tool_metadata(self) -> ToolMetadata:
        """Return metadata describing this tool's purpose and interface."""
        ...


class ToolMetadataRegistry:
    """
    Registry for tool metadata following dependency inversion principle.
    
    This allows tools to register their own metadata rather than having
    it hardcoded in the ReAct loop.
    """
    
    def __init__(self):
        self._metadata: Dict[str, ToolMetadata] = {}
    
    def register_tool_metadata(self, tool_name: str, metadata: ToolMetadata) -> None:
        """Register metadata for a specific tool."""
        self._metadata[tool_name] = metadata
    
    def get_tool_metadata(self, tool_name: str) -> ToolMetadata:
        """Get metadata for a specific tool."""
        return self._metadata.get(tool_name)
    
    def get_all_metadata(self) -> Dict[str, ToolMetadata]:
        """Get metadata for all registered tools."""
        return self._metadata.copy()
    
    def introspect_tool(self, tool_name: str, tool_func: Callable) -> ToolMetadata:
        """
        Try to introspect tool metadata from function annotations or attributes.
        
        This provides a fallback for tools that don't explicitly register metadata.
        """
        # Check if tool has a metadata attribute
        if hasattr(tool_func, 'get_tool_metadata'):
            return tool_func.get_tool_metadata()
        
        # Check if tool has metadata as an attribute
        if hasattr(tool_func, 'tool_metadata'):
            return tool_func.tool_metadata
        
        # Fallback: create basic metadata from function inspection
        return ToolMetadata(
            name=tool_name,
            description=getattr(tool_func, '__doc__', f"Tool: {tool_name}") or f"Tool: {tool_name}",
            parameters=self._extract_parameters_from_signature(tool_func)
        )
    
    def _extract_parameters_from_signature(self, func: Callable) -> Dict[str, str]:
        """Extract parameter information from function signature."""
        import inspect
        
        try:
            sig = inspect.signature(func)
            params = {}
            for param_name, param in sig.parameters.items():
                if param.annotation != inspect.Parameter.empty:
                    params[param_name] = str(param.annotation)
                else:
                    params[param_name] = "Any"
            return params
        except Exception:
            return {}


# Global registry instance
tool_metadata_registry = ToolMetadataRegistry()


def register_tool_metadata(tool_name: str, description: str, parameters: Dict[str, str], examples: list[str] = None):
    """Decorator for registering tool metadata."""
    def decorator(func):
        metadata = ToolMetadata(
            name=tool_name,
            description=description,
            parameters=parameters,
            examples=examples or []
        )
        tool_metadata_registry.register_tool_metadata(tool_name, metadata)
        func.tool_metadata = metadata
        return func
    return decorator


def get_tools_metadata(tools: Dict[str, Callable]) -> Dict[str, Dict[str, Any]]:
    """
    Extract metadata for a collection of tools.
    
    This function provides the interface for the ReAct loop to get tool metadata
    without hardcoding descriptions.
    
    Args:
        tools: Dictionary of tool_name -> tool_function
        
    Returns:
        Dictionary of tool_name -> metadata dictionary
    """
    metadata = {}
    
    for tool_name, tool_func in tools.items():
        # Try to get registered metadata first
        tool_metadata = tool_metadata_registry.get_tool_metadata(tool_name)
        
        # If not registered, try introspection
        if not tool_metadata:
            tool_metadata = tool_metadata_registry.introspect_tool(tool_name, tool_func)
        
        metadata[tool_name] = tool_metadata.to_dict()
    
    return metadata
