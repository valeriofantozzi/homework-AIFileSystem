"""
Pydantic-AI tool wrappers for secure file operations.

This module provides factory functions that create Pydantic-AI compatible tools
for file operations, wrapping the workspace_fs functionality with proper
error handling and validation.
"""

from typing import Any

from workspace_fs import (
    FileSystemTools,
    InvalidMode,
    PathTraversalError,
    SizeLimitExceeded,
    SymlinkError,
    Workspace,
    WorkspaceError,
)

try:
    # Check if pydantic_ai is available without importing
    import importlib.util
    PYDANTIC_AI_AVAILABLE = importlib.util.find_spec("pydantic_ai") is not None
except ImportError:
    PYDANTIC_AI_AVAILABLE = False


def create_file_tools(workspace: Workspace, **fs_kwargs: Any) -> dict[str, Any]:
    """
    Create Pydantic-AI tools for file operations.

    This function creates tool functions that can be registered with Pydantic-AI agents.

    Args:
        workspace: The workspace instance for secure operations.
        **fs_kwargs: Additional arguments for FileSystemTools initialization.

    Returns:
        Dictionary containing tool functions ready for agent registration.

    Example:
        >>> workspace = Workspace("/safe/dir")
        >>> tools = create_file_tools(workspace, max_read=1024*1024)
        >>> # Register tools with your agent
    """
    # Create FileSystemTools instance with dependency injection
    fs_tools = FileSystemTools(workspace, **fs_kwargs)

    def list_files() -> list[str]:
        """
        List all files in the workspace, sorted by modification time (newest first).

        This tool returns only regular files, excluding directories and hidden files.
        Files are sorted by their last modification time with the most recently
        modified files appearing first in the list.

        Returns:
            List of filenames sorted by modification time.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            return fs_tools.list_files()
        except Exception as e:
            raise WorkspaceError(f"Failed to list files: {e}") from e

    def list_directories() -> list[str]:
        """
        List all directories in the workspace, sorted by modification time (newest first).

        This tool returns only directories, excluding files and hidden directories.
        Directories are sorted by their last modification time with the most recently
        modified directories appearing first in the list.

        Returns:
            List of directory names sorted by modification time.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            return fs_tools.list_directories()
        except Exception as e:
            raise WorkspaceError(f"Failed to list directories: {e}") from e

    def list_all() -> list[str]:
        """
        List all files and directories in the workspace, sorted by modification time.

        This tool returns both files and directories, with directories suffixed by '/'
        for easy identification. Items are sorted by their last modification time
        with the most recently modified items appearing first.

        Returns:
            List of file and directory names, directories suffixed with '/'.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            return fs_tools.list_all()
        except Exception as e:
            raise WorkspaceError(f"Failed to list workspace contents: {e}") from e

    def read_file(filename: str) -> str:
        """
        Read the complete content of a file from the workspace.

        This tool safely reads file content with size limits and proper encoding
        handling. The file must exist within the workspace boundaries.

        Args:
            filename: Name of the file to read (no path separators allowed).

        Returns:
            The complete file content as a string.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            WorkspaceError: If the file cannot be read or is outside workspace.
        """
        try:
            return fs_tools.read_file(filename)
        except (
            FileNotFoundError, SizeLimitExceeded, PathTraversalError,
            SymlinkError, ValueError
        ):
            raise
        except Exception as e:
            raise WorkspaceError(f"Failed to read file '{filename}': {e}") from e

    def write_file(filename: str, content: str, mode: str = "w") -> str:
        """
        Write content to a file in the workspace.

        This tool safely writes content to files with size limits and proper
        mode validation. Supports both write ('w') and append ('a') modes.

        Args:
            filename: Name of the file to write (no path separators allowed).
            content: The content to write to the file.
            mode: Write mode - 'w' for overwrite, 'a' for append.

        Returns:
            Success message indicating bytes written.

        Raises:
            WorkspaceError: If the file cannot be written or is outside workspace.
        """
        try:
            return fs_tools.write_file(filename, content, mode)
        except (
            SizeLimitExceeded, PathTraversalError, SymlinkError,
            InvalidMode, ValueError
        ):
            raise
        except Exception as e:
            raise WorkspaceError(f"Failed to write file '{filename}': {e}") from e

    def delete_file(filename: str) -> str:
        """
        Delete a file from the workspace.

        This tool safely removes files with security checks to ensure the file
        is within workspace boundaries and is not a symbolic link or special file.

        Args:
            filename: Name of the file to delete (no path separators allowed).

        Returns:
            Success message confirming deletion.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            WorkspaceError: If the file cannot be deleted or is outside workspace.
        """
        try:
            return fs_tools.delete_file(filename)
        except (FileNotFoundError, PathTraversalError, SymlinkError, ValueError):
            raise
        except Exception as e:
            raise WorkspaceError(f"Failed to delete file '{filename}': {e}") from e

    # Return tool functions as dictionary
    return {
        "list_files": list_files,
        "list_directories": list_directories,
        "list_all": list_all,
        "read_file": read_file,
        "write_file": write_file,
        "delete_file": delete_file,
    }
