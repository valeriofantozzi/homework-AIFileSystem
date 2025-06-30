"""
workspace_fs: Secure file system operations with sandbox enforcement.

This package provides tools for secure file operations within a controlled
workspace, enforcing path safety, size limits, and rate limiting.
"""

__version__ = "0.1.0"

# Import public API components
from .exceptions import (
    InvalidMode,
    PathTraversalError,
    RateLimitError,
    SizeLimitExceeded,
    SymlinkError,
    WorkspaceError,
)
from .fs_tools import FileSystemTools
from .workspace import Workspace

__all__ = [
    'Workspace',
    'FileSystemTools',
    'WorkspaceError',
    'PathTraversalError',
    'SymlinkError',
    'SizeLimitExceeded',
    'InvalidMode',
    'RateLimitError'
]
