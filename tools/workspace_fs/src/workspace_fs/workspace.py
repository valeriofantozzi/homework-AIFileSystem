"""
Workspace class for secure file system operations.

Provides a sandboxed environment for file operations with guaranteed
path safety and workspace boundary enforcement.
"""

import os
from pathlib import Path

from .exceptions import PathTraversalError, SymlinkError


class Workspace:
    """
    Secure workspace for file operations within a sandboxed directory.

    This class ensures all file operations remain within the workspace
    boundaries, preventing path traversal attacks and symlink exploitation.

    Example:
        >>> workspace = Workspace("/safe/workspace/dir")
        >>> safe_path = workspace.safe_join("myfile.txt")
        >>> # safe_path is guaranteed to be within workspace
    """

    def __init__(self, root_dir: str | Path) -> None:
        """
        Initialize workspace with specified root directory.

        Args:
            root_dir: The root directory for this workspace. Will be created
                     if it doesn't exist.

        Raises:
            OSError: If directory cannot be created or accessed.
        """
        self._root = Path(root_dir).resolve()

        # Create workspace directory if it doesn't exist
        self._root.mkdir(parents=True, exist_ok=True)

        # Verify we can access the directory
        if not self._root.is_dir():
            raise OSError(f"Workspace root is not a directory: {self._root}")

    @property
    def root(self) -> Path:
        """Get the absolute path to the workspace root directory."""
        return self._root

    def safe_join(self, filename: str) -> Path:
        """
        Safely join filename to workspace root, preventing path traversal.

        This method ensures that the resulting path:
        - Stays within the workspace boundaries
        - Does not involve symbolic links
        - Is normalized and absolute

        Args:
            filename: The filename to join to workspace root. Should not
                     contain directory separators or relative path components.

        Returns:
            Absolute path within the workspace.

        Raises:
            PathTraversalError: If the filename would escape the workspace.
            SymlinkError: If the path involves symbolic links.
            ValueError: If filename is empty or contains directory separators.

        Example:
            >>> ws = Workspace("/workspace")
            >>> path = ws.safe_join("file.txt")  # OK
            >>> path = ws.safe_join("../escape.txt")  # Raises PathTraversalError
        """
        if not filename or not filename.strip():
            raise ValueError("Filename cannot be empty")

        # Reject paths containing directory separators
        if os.sep in filename or "/" in filename or "\\" in filename:
            raise ValueError(f"Filename cannot contain directory separators: '{filename}'")

        # Reject relative path components
        if filename in {".", ".."} or filename.startswith("."):
            if filename != "." and filename != ".." and not filename.startswith(".."):
                # Allow hidden files that start with . but aren't .. or .
                pass
            else:
                raise ValueError(f"Relative path components not allowed: '{filename}'")

        # Join and resolve the path
        candidate_path = (self._root / filename).resolve()

        # Verify the resolved path is within workspace
        try:
            candidate_path.relative_to(self._root)
        except ValueError as e:
            raise PathTraversalError(str(candidate_path), str(self._root)) from e

        # Check for symbolic links in the path
        if candidate_path.is_symlink():
            raise SymlinkError(str(candidate_path))

        # Check if any parent directory is a symlink
        current = candidate_path.parent
        while current != self._root:
            if current.is_symlink():
                raise SymlinkError(str(current))
            current = current.parent

        return candidate_path

    def exists(self, filename: str) -> bool:
        """
        Check if a file exists in the workspace.

        Args:
            filename: The filename to check.

        Returns:
            True if file exists, False otherwise.

        Raises:
            PathTraversalError: If filename would escape workspace.
            SymlinkError: If path involves symbolic links.
        """
        safe_path = self.safe_join(filename)
        return safe_path.exists() and safe_path.is_file()

    def __str__(self) -> str:
        """Return string representation of workspace."""
        return f"Workspace(root={self._root})"

    def __repr__(self) -> str:
        """Return detailed string representation of workspace."""
        return f"Workspace(root='{self._root}')"
