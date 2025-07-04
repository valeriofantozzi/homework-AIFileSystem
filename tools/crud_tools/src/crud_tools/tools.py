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

# Tool metadata for self-describing tools
TOOL_METADATA = {
    "list_files": {
        "description": "List all files in the current directory",
        "parameters": {},
        "examples": ["list all files", "show me the files", "what files are here"]
    },
    "list_directories": {
        "description": "List only directories/folders in the current directory",
        "parameters": {},
        "examples": ["list directories", "show folders", "what directories exist"]
    },
    "list_all": {
        "description": "List both files and directories in the current directory",
        "parameters": {},
        "examples": ["list everything", "show all files and folders", "tutti i file e cartelle"]
    },
    "tree": {
        "description": "Display workspace structure in tree format with hierarchical visualization",
        "parameters": {},
        "examples": ["show tree", "tree structure", "mostra albero", "visualizza struttura", "tree view"]
    },
    "read_file": {
        "description": "Read the contents of a specific file",
        "parameters": {"filename": "str"},
        "examples": ["read config.json", "show me the content of readme.txt", "leggi il file"]
    },
    "write_file": {
        "description": "Write content to a file",
        "parameters": {"filename": "str", "content": "str", "mode": "str"},
        "examples": ["create a new file", "write data to file.txt", "scrivi nel file"]
    },
    "delete_file": {
        "description": "Delete a specific file",
        "parameters": {"filename": "str"},
        "examples": ["delete old_file.txt", "remove temporary.log", "elimina il file"]
    }
}

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
            raise RuntimeError(f"Failed to list files: {e}") from e
    
    # Attach metadata to the function
    list_files.tool_metadata = TOOL_METADATA["list_files"]

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
    
    # Attach metadata to the function
    list_directories.tool_metadata = TOOL_METADATA["list_directories"]

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
    
    # Attach metadata to the function
    list_all.tool_metadata = TOOL_METADATA["list_all"]

    def tree() -> str:
        """
        Display workspace structure in tree format with hierarchical visualization.

        This tool generates a visual representation of the workspace directory
        structure, similar to the Unix 'tree' command. It shows all files and
        directories in a hierarchical format with proper indentation and
        connecting lines.

        Returns:
            String representation of the workspace tree structure.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            return fs_tools.list_tree()
        except Exception as e:
            raise WorkspaceError(f"Failed to generate tree view: {e}") from e
    
    # Attach metadata to the function
    tree.tool_metadata = TOOL_METADATA["tree"]

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
    
    # Attach metadata to the function
    read_file.tool_metadata = TOOL_METADATA["read_file"]

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
    
    # Attach metadata to the function
    write_file.tool_metadata = TOOL_METADATA["write_file"]

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
    
    # Attach metadata to the function
    delete_file.tool_metadata = TOOL_METADATA["delete_file"]

    def list_files_recursive() -> list[str]:
        """
        List all files in the workspace recursively, including subdirectories.

        This tool returns files from all subdirectories with relative paths,
        excluding hidden files and __pycache__ directories.
        Files are sorted by their last modification time with the most recently
        modified files appearing first in the list.

        Returns:
            List of relative file paths sorted by modification time.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            return fs_tools.list_files_recursive()
        except Exception as e:
            raise RuntimeError(f"Failed to list files recursively: {e}") from e
    
    # Attach metadata to the function
    list_files_recursive.tool_metadata = {
        "description": "List all files recursively in all subdirectories",
        "parameters": {},
        "examples": [
            "list all files including in subdirectories",
            "show me all files recursively",
            "find all files in the entire workspace"
        ]
    }

    def find_file_by_name(filename: str) -> str:
        """
        Find a file by exact name searching recursively in all subdirectories.

        This tool searches for a file with the exact name in all subdirectories
        and returns the relative path if found. Perfect for locating specific files
        like "secure_agent.py" anywhere in the workspace structure.

        Args:
            filename: Exact filename to search for (e.g., "secure_agent.py")

        Returns:
            Relative path to the file if found, error message if not found.

        Raises:
            WorkspaceError: If the workspace cannot be accessed or read.
        """
        try:
            result = fs_tools.find_file_by_name(filename)
            if result:
                return f"Found file: {result}"
            else:
                return f"File '{filename}' not found in workspace"
        except Exception as e:
            raise RuntimeError(f"Failed to find file '{filename}': {e}") from e
    
    # Attach metadata to the function
    find_file_by_name.tool_metadata = {
        "description": "Find a file by exact name searching recursively in all subdirectories",
        "parameters": {
            "filename": {
                "type": "string",
                "description": "Exact filename to search for (e.g., 'secure_agent.py')",
                "required": True
            }
        },
        "examples": [
            "find file secure_agent.py",
            "locate file config.yaml",
            "search for main.py"
        ]
    }

    def read_file_by_path(filepath: str) -> str:
        """
        Read content from a file using relative path (supports subdirectories).

        This tool can read files from any subdirectory using relative paths
        like "agent/core/secure_agent.py". Much more powerful than the basic
        read_file tool which only works in the root directory.

        Args:
            filepath: Relative path to the file (e.g., "agent/core/secure_agent.py")

        Returns:
            The complete file content as a string.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            WorkspaceError: If the file cannot be read or is outside workspace.
        """
        try:
            return fs_tools.read_file_by_path(filepath)
        except (
            FileNotFoundError, SizeLimitExceeded, PathTraversalError,
            SymlinkError, ValueError
        ):
            raise
        except Exception as e:
            raise WorkspaceError(f"Failed to read file '{filepath}': {e}") from e
    
    # Attach metadata to the function
    read_file_by_path.tool_metadata = {
        "description": "Read content from a file using relative path (supports subdirectories)",
        "parameters": {
            "filepath": {
                "type": "string",
                "description": "Relative path to the file (e.g., 'agent/core/secure_agent.py')",
                "required": True
            }
        },
        "examples": [
            "read file agent/core/secure_agent.py",
            "show content of config/models.yaml",
            "read docs/README.md"
        ]
    }

    # Return tool functions as dictionary
    return {
        "list_files": list_files,
        "list_directories": list_directories,
        "list_all": list_all,
        "tree": tree,
        "read_file": read_file,
        "write_file": write_file,
        "delete_file": delete_file,
        "list_files_recursive": list_files_recursive,
        "find_file_by_name": find_file_by_name,
        "read_file_by_path": read_file_by_path,
    }
