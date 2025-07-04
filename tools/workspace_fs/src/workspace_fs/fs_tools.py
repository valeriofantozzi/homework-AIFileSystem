"""
FileSystemTools class for controlled file operations within a workspace.

Provides rate-limited, size-controlled file operations with comprehensive
error handling and security enforcement.
"""

import time
import os
from pathlib import Path
from typing import Optional

from .exceptions import (
    InvalidMode,
    RateLimitError,
    SizeLimitExceeded,
    WorkspaceError,
)
from .workspace import Workspace


class FileSystemTools:
    """
    Rate-limited and size-controlled file operations within a workspace.

    This class provides secure file operations with configurable limits
    on file sizes and operation rates to prevent resource exhaustion
    and abuse.

    Example:
        >>> workspace = Workspace("/safe/dir")
        >>> fs_tools = FileSystemTools(workspace, max_read=1024*1024)  # 1MB max read
        >>> content = fs_tools.read_file("data.txt")
    """

    def __init__(
        self,
        workspace: Workspace,
        max_read: int = 10 * 1024 * 1024,  # 10MB default
        max_write: int = 10 * 1024 * 1024,  # 10MB default
        rate_limit: float = 10.0,  # 10 operations per second default
    ) -> None:
        """
        Initialize FileSystemTools with workspace and limits.

        Args:
            workspace: The workspace instance for secure path operations.
            max_read: Maximum bytes to read from a single file.
            max_write: Maximum bytes to write to a single file.
            rate_limit: Maximum operations per second allowed.

        Raises:
            ValueError: If any limit values are invalid.
        """
        if max_read <= 0:
            raise ValueError("max_read must be positive")
        if max_write <= 0:
            raise ValueError("max_write must be positive")
        if rate_limit <= 0:
            raise ValueError("rate_limit must be positive")

        self._workspace = workspace
        self._max_read = max_read
        self._max_write = max_write
        self._rate_limit = rate_limit

        # Rate limiting state
        self._operation_times: list[float] = []

    @property
    def workspace(self) -> Workspace:
        """Get the workspace instance."""
        return self._workspace

    @property
    def max_read(self) -> int:
        """Get the maximum read size in bytes."""
        return self._max_read

    @property
    def max_write(self) -> int:
        """Get the maximum write size in bytes."""
        return self._max_write

    @property
    def rate_limit(self) -> float:
        """Get the rate limit in operations per second."""
        return self._rate_limit

    def _check_rate_limit(self) -> None:
        """
        Check if current operation exceeds rate limit.

        Raises:
            RateLimitError: If rate limit is exceeded.
        """
        current_time = time.time()

        # Remove operations older than 1 second
        cutoff_time = current_time - 1.0
        self._operation_times = [t for t in self._operation_times if t > cutoff_time]

        # Check if adding this operation would exceed limit
        if len(self._operation_times) >= self._rate_limit:
            current_rate = len(self._operation_times)
            raise RateLimitError(current_rate, self._rate_limit)

        # Record this operation
        self._operation_times.append(current_time)

    def list_files(self) -> list[str]:
        """
        List all files in the workspace, sorted by modification time.

        Returns files only (not directories), excluding hidden files,
        sorted by modification time (newest first).

        Returns:
            List of filenames sorted by modification time.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            files_with_mtime = []

            for item in self._workspace.root.iterdir():
                # Skip directories and hidden files
                if item.is_file() and not item.name.startswith("."):
                    try:
                        mtime = item.stat().st_mtime
                        files_with_mtime.append((item.name, mtime))
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue

            # Sort by modification time (newest first)
            files_with_mtime.sort(key=lambda x: x[1], reverse=True)

            return [filename for filename, _ in files_with_mtime]

        except Exception as e:
            raise WorkspaceError(f"Failed to list files: {e}") from e

    def read_file(self, filename: str) -> str:
        """
        Read content from a file in the workspace.

        Args:
            filename: Name of the file to read.

        Returns:
            File content as string.

        Raises:
            RateLimitError: If rate limit is exceeded.
            SizeLimitExceeded: If file size exceeds max_read limit.
            FileNotFoundError: If file doesn't exist.
            WorkspaceError: If file cannot be read.
        """
        self._check_rate_limit()

        safe_path = self._workspace.safe_join(filename)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        if not safe_path.is_file():
            raise WorkspaceError(f"Path is not a file: {filename}")

        # Check file size
        try:
            file_size = safe_path.stat().st_size
            if file_size > self._max_read:
                raise SizeLimitExceeded("read", file_size, self._max_read, filename)
        except OSError as e:
            raise WorkspaceError(f"Cannot access file stats: {filename}") from e

        # Read file content
        try:
            with safe_path.open("r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for binary-like files
            try:
                with safe_path.open("r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                raise WorkspaceError(f"Cannot decode file content: {filename}") from e
        except Exception as e:
            raise WorkspaceError(f"Cannot read file: {filename}") from e

    def write_file(self, filename: str, content: str, mode: str = "w") -> str:
        """
        Write content to a file in the workspace.

        Args:
            filename: Name of the file to write.
            content: Content to write to the file.
            mode: Write mode - 'w' for overwrite, 'a' for append.

        Returns:
            Success message.

        Raises:
            RateLimitError: If rate limit is exceeded.
            SizeLimitExceeded: If content size exceeds max_write limit.
            InvalidMode: If mode is not valid.
            WorkspaceError: If file cannot be written.
        """
        self._check_rate_limit()

        # Validate mode
        valid_modes = ["w", "a"]
        if mode not in valid_modes:
            raise InvalidMode(mode, valid_modes)

        # Check content size
        content_bytes = content.encode("utf-8")
        if len(content_bytes) > self._max_write:
            raise SizeLimitExceeded(
                "write", len(content_bytes), self._max_write, filename
            )

        safe_path = self._workspace.safe_join(filename)

        try:
            with safe_path.open(mode, encoding="utf-8") as f:
                f.write(content)

            action = "appended" if mode == "a" else "written"
            return f"Content {action} to {filename}"

        except Exception as e:
            raise WorkspaceError(f"Cannot write file: {filename}") from e

    def delete_file(self, filename: str) -> str:
        """
        Delete a file from the workspace.

        Args:
            filename: Name of the file to delete.

        Returns:
            Success message.

        Raises:
            RateLimitError: If rate limit is exceeded.
            FileNotFoundError: If file doesn't exist.
            WorkspaceError: If file cannot be deleted.
        """
        self._check_rate_limit()

        safe_path = self._workspace.safe_join(filename)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")

        if not safe_path.is_file():
            raise WorkspaceError(f"Path is not a file: {filename}")

        try:
            safe_path.unlink()
            return f"File deleted: {filename}"

        except Exception as e:
            raise WorkspaceError(f"Cannot delete file: {filename}") from e

    def list_directories(self) -> list[str]:
        """
        List all directories in the workspace, sorted by modification time.

        Returns directories only (not files), excluding hidden directories,
        sorted by modification time (newest first).

        Returns:
            List of directory names sorted by modification time.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            dirs_with_mtime = []

            for item in self._workspace.root.iterdir():
                # Skip files and hidden directories
                if item.is_dir() and not item.name.startswith("."):
                    try:
                        mtime = item.stat().st_mtime
                        dirs_with_mtime.append((item.name, mtime))
                    except (OSError, PermissionError):
                        # Skip directories we can't access
                        continue

            # Sort by modification time (newest first)
            dirs_with_mtime.sort(key=lambda x: x[1], reverse=True)

            return [dirname for dirname, _ in dirs_with_mtime]

        except OSError as e:
            raise WorkspaceError(f"Failed to list directories in workspace: {e}")

    def list_all(self) -> list[str]:
        """
        List all files and directories in the workspace, sorted by modification time.

        Returns both files and directories, excluding hidden items.
        Directories are suffixed with '/' for easy identification.
        Sorted by modification time (newest first).

        Returns:
            List of file and directory names, with directories suffixed by '/'.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            items_with_mtime = []

            for item in self._workspace.root.iterdir():
                # Skip hidden items
                if item.name.startswith("."):
                    continue

                try:
                    mtime = item.stat().st_mtime
                    if item.is_file():
                        items_with_mtime.append((item.name, mtime))
                    elif item.is_dir():
                        # Add '/' suffix to indicate directory
                        items_with_mtime.append((f"{item.name}/", mtime))
                except (OSError, PermissionError):
                    # Skip items we can't access
                    continue

            # Sort by modification time (newest first)
            items_with_mtime.sort(key=lambda x: x[1], reverse=True)

            return [item_name for item_name, _ in items_with_mtime]

        except OSError as e:
            raise WorkspaceError(f"Failed to list workspace contents: {e}")

    def list_tree(self) -> str:
        """
        Generate a tree view of the workspace structure.

        Creates a hierarchical visualization of all files and directories
        in the workspace, similar to the Unix 'tree' command. Shows the
        complete directory structure recursively.

        Returns:
            Formatted tree string showing the workspace hierarchy.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            def _build_tree(path, prefix="", is_last=True):
                """
                Recursively build tree structure for a directory.

                Args:
                    path: Path object to process
                    prefix: Current line prefix for indentation
                    is_last: Whether this is the last item in current level
                """
                items = []

                # Get the name to display
                if path == self._workspace.root:
                    # For the root directory, don't show the line, just process contents
                    name = None
                else:
                    name = path.name
                    if path.is_dir():
                        name += "/"

                # Create the current line (skip for root)
                if name is not None:
                    connector = "└── " if is_last else "├── "
                    current_line = f"{prefix}{connector}{name}"
                    items.append(current_line)

                # If it's a directory, process its contents
                if path.is_dir():
                    try:
                        # Get all items, excluding hidden files and __pycache__
                        children = [item for item in path.iterdir() 
                                  if not item.name.startswith(".") and item.name != "__pycache__"]

                        # Sort children: directories first, then files, alphabetically within each group
                        children.sort(key=lambda x: (not x.is_dir(), x.name.lower()))

                        # Process each child
                        for i, child in enumerate(children):
                            is_child_last = (i == len(children) - 1)

                            # Determine new prefix for child
                            if path == self._workspace.root:
                                # For root directory, start fresh without prefix
                                new_prefix = ""
                            elif is_last:
                                new_prefix = prefix + "    "  # Empty space for last items
                            else:
                                new_prefix = prefix + "│   "  # Vertical line for continuing branches

                            # Recursively build subtree
                            child_items = _build_tree(child, new_prefix, is_child_last)
                            items.extend(child_items)

                    except (OSError, PermissionError):
                        # Add error indicator for inaccessible directories
                        error_prefix = prefix + ("    " if is_last else "│   ")
                        items.append(f"{error_prefix}└── [Permission Denied]")

                return items

            # Build the complete tree starting from workspace root
            tree_lines = _build_tree(self._workspace.root)
            
            # Add header with directory name
            workspace_name = self._workspace.root.name or "workspace"
            header = f"{workspace_name}/"
            
            # Combine header with tree content
            if tree_lines:
                result_lines = [header] + tree_lines
            else:
                result_lines = [header, "└── (empty)"]

            # Join all lines and return
            return "\n".join(result_lines)

        except Exception as e:
            raise WorkspaceError(f"Failed to generate tree view: {e}") from e

    def list_files_recursive(self) -> list[str]:
        """
        List all files in the workspace recursively, including subdirectories.

        Returns files from all subdirectories with relative paths,
        excluding hidden files, sorted by modification time (newest first).

        Returns:
            List of relative file paths sorted by modification time.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            files_with_mtime = []

            # Walk through all subdirectories
            for root, dirs, files in os.walk(self._workspace.root):
                # Filter out hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                for file in files:
                    # Skip hidden files
                    if file.startswith('.'):
                        continue
                    
                    full_path = Path(root) / file
                    try:
                        mtime = full_path.stat().st_mtime
                        # Get relative path from workspace root
                        relative_path = full_path.relative_to(self._workspace.root)
                        files_with_mtime.append((str(relative_path), mtime))
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue

            # Sort by modification time (newest first)
            files_with_mtime.sort(key=lambda x: x[1], reverse=True)

            return [filepath for filepath, _ in files_with_mtime]

        except Exception as e:
            raise WorkspaceError(f"Failed to list files recursively: {e}") from e

    def find_file_by_name(self, filename: str) -> Optional[str]:
        """
        Find a file by exact name searching recursively in all subdirectories.

        Args:
            filename: Exact filename to search for (e.g., "secure_agent.py")

        Returns:
            Relative path to the file if found, None otherwise.

        Raises:
            RateLimitError: If rate limit is exceeded.
            WorkspaceError: If workspace access fails.
        """
        self._check_rate_limit()

        try:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(self._workspace.root):
                # Filter out hidden directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
                
                if filename in files:
                    full_path = Path(root) / filename
                    # Get relative path from workspace root
                    relative_path = full_path.relative_to(self._workspace.root)
                    return str(relative_path)

            return None

        except Exception as e:
            raise WorkspaceError(f"Failed to find file '{filename}': {e}") from e

    def read_file_by_path(self, filepath: str) -> str:
        """
        Read content from a file using relative path (supports subdirectories).

        Args:
            filepath: Relative path to the file (e.g., "agent/core/secure_agent.py")

        Returns:
            File content as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
            WorkspaceError: If file cannot be read.
        """
        self._check_rate_limit()

        # Use safe_join which handles relative paths
        safe_path = self._workspace.safe_join(filepath)

        if not safe_path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        if not safe_path.is_file():
            raise WorkspaceError(f"Path is not a file: {filepath}")

        # Check file size
        try:
            file_size = safe_path.stat().st_size
            if file_size > self._max_read:
                raise SizeLimitExceeded(file_size, self._max_read)
        except OSError as e:
            raise WorkspaceError(f"Cannot access file '{filepath}': {e}") from e

        # Read file content
        try:
            return safe_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                return safe_path.read_text(encoding="latin-1")
            except Exception as e:
                raise WorkspaceError(f"Failed to decode file '{filepath}': {e}") from e
        except Exception as e:
            raise WorkspaceError(f"Failed to read file '{filepath}': {e}") from e

    def __str__(self) -> str:
        """Return string representation of FileSystemTools."""
        return f"FileSystemTools(workspace={self._workspace}, limits=r:{self._max_read}/w:{self._max_write}/rate:{self._rate_limit})"

    def __repr__(self) -> str:
        """Return detailed string representation of FileSystemTools."""
        return (
            f"FileSystemTools(workspace={self._workspace!r}, "
            f"max_read={self._max_read}, max_write={self._max_write}, "
            f"rate_limit={self._rate_limit})"
        )
