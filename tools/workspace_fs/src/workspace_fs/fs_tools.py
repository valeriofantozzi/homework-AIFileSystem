"""
FileSystemTools class for controlled file operations within a workspace.

Provides rate-limited, size-controlled file operations with comprehensive
error handling and security enforcement.
"""

import time

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
                if item.is_file() and not item.name.startswith('.'):
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
            with safe_path.open('r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Fallback to latin-1 for binary-like files
            try:
                with safe_path.open('r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                raise WorkspaceError(f"Cannot decode file content: {filename}") from e
        except Exception as e:
            raise WorkspaceError(f"Cannot read file: {filename}") from e

    def write_file(self, filename: str, content: str, mode: str = 'w') -> str:
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
        valid_modes = ['w', 'a']
        if mode not in valid_modes:
            raise InvalidMode(mode, valid_modes)

        # Check content size
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self._max_write:
            raise SizeLimitExceeded("write", len(content_bytes), self._max_write, filename)

        safe_path = self._workspace.safe_join(filename)

        try:
            with safe_path.open(mode, encoding='utf-8') as f:
                f.write(content)

            action = "appended" if mode == 'a' else "written"
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
