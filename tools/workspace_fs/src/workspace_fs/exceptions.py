"""
Custom exceptions for workspace_fs package.

All exceptions inherit from WorkspaceError base class to allow
unified error handling while providing specific error types
for different failure modes.
"""


class WorkspaceError(Exception):
    """Base exception for all workspace-related errors."""

    def __init__(self, message: str, path: str | None = None) -> None:
        """Initialize workspace error with message and optional path context."""
        super().__init__(message)
        self.message = message
        self.path = path

    def __str__(self) -> str:
        """Return formatted error message with path context if available."""
        if self.path:
            return f"{self.message} (path: {self.path})"
        return self.message


class PathTraversalError(WorkspaceError):
    """Raised when a path attempts to escape the workspace sandbox."""

    def __init__(self, path: str, workspace_root: str) -> None:
        """Initialize path traversal error with attempted path and workspace root."""
        message = f"Path traversal attempt blocked: '{path}' outside workspace '{workspace_root}'"
        super().__init__(message, path)
        self.workspace_root = workspace_root


class SymlinkError(WorkspaceError):
    """Raised when attempting to access or create symbolic links."""

    def __init__(self, path: str) -> None:
        """Initialize symlink error for blocked symlink access."""
        message = f"Symbolic link access denied for security reasons: '{path}'"
        super().__init__(message, path)


class SizeLimitExceeded(WorkspaceError):
    """Raised when file operation exceeds configured size limits."""

    def __init__(
        self, operation: str, size: int, limit: int, path: str | None = None
    ) -> None:
        """Initialize size limit error with operation details."""
        message = f"{operation} size {size} bytes exceeds limit of {limit} bytes"
        super().__init__(message, path)
        self.operation = operation
        self.size = size
        self.limit = limit


class InvalidMode(WorkspaceError):
    """Raised when an invalid file operation mode is specified."""

    def __init__(self, mode: str, valid_modes: list[str]) -> None:
        """Initialize invalid mode error with attempted and valid modes."""
        valid_modes_str = "', '".join(valid_modes)
        message = f"Invalid mode '{mode}'. Valid modes are: '{valid_modes_str}'"
        super().__init__(message)
        self.mode = mode
        self.valid_modes = valid_modes


class RateLimitError(WorkspaceError):
    """Raised when rate limit for file operations is exceeded."""

    def __init__(self, operations_per_second: float, limit: float) -> None:
        """Initialize rate limit error with current and limit rates."""
        message = f"Rate limit exceeded: {operations_per_second:.2f} ops/sec > {limit:.2f} ops/sec limit"
        super().__init__(message)
        self.operations_per_second = operations_per_second
        self.limit = limit
