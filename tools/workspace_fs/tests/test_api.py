"""Test public API imports and basic functionality."""

import tempfile
from pathlib import Path

import pytest

# Test that all public API components can be imported
from workspace_fs import (
    FileSystemTools,
    InvalidMode,
    PathTraversalError,
    RateLimitError,
    SizeLimitExceeded,
    SymlinkError,
    Workspace,
    WorkspaceError,
    __version__,
)


def test_version_available():
    """Test that version is accessible."""
    assert __version__ == "0.1.0"


def test_workspace_creation():
    """Test basic workspace creation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)
        assert workspace.root == Path(temp_dir).resolve()


def test_workspace_safe_join():
    """Test workspace safe_join functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)

        # Valid filename should work
        safe_path = workspace.safe_join("test.txt")
        assert safe_path.parent == workspace.root
        assert safe_path.name == "test.txt"


def test_workspace_safe_join_rejects_traversal():
    """Test that safe_join rejects path traversal attempts."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)

        # These should raise ValueError for directory separators
        with pytest.raises(ValueError, match="directory separators"):
            workspace.safe_join("../escape.txt")

        with pytest.raises(ValueError, match="directory separators"):
            workspace.safe_join("sub/dir/file.txt")


def test_filesystem_tools_creation():
    """Test FileSystemTools creation with workspace."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)
        fs_tools = FileSystemTools(workspace)

        assert fs_tools.workspace == workspace
        assert fs_tools.max_read > 0
        assert fs_tools.max_write > 0
        assert fs_tools.rate_limit > 0


def test_filesystem_tools_invalid_limits():
    """Test FileSystemTools rejects invalid limit values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)

        with pytest.raises(ValueError, match="max_read must be positive"):
            FileSystemTools(workspace, max_read=0)

        with pytest.raises(ValueError, match="max_write must be positive"):
            FileSystemTools(workspace, max_write=-1)

        with pytest.raises(ValueError, match="rate_limit must be positive"):
            FileSystemTools(workspace, rate_limit=0)


def test_custom_exceptions_hierarchy():
    """Test that custom exceptions inherit properly."""
    # All custom exceptions should inherit from WorkspaceError
    assert issubclass(PathTraversalError, WorkspaceError)
    assert issubclass(SymlinkError, WorkspaceError)
    assert issubclass(SizeLimitExceeded, WorkspaceError)
    assert issubclass(InvalidMode, WorkspaceError)
    assert issubclass(RateLimitError, WorkspaceError)


def test_workspace_error_with_path():
    """Test WorkspaceError with path context."""
    error = WorkspaceError("Test message", "/test/path")
    assert "Test message" in str(error)
    assert "/test/path" in str(error)
    assert error.path == "/test/path"


def test_path_traversal_error():
    """Test PathTraversalError formatting."""
    error = PathTraversalError("/bad/path", "/workspace")
    assert "Path traversal attempt blocked" in str(error)
    assert "/bad/path" in str(error)
    assert "/workspace" in str(error)


def test_size_limit_exceeded_error():
    """Test SizeLimitExceeded formatting."""
    error = SizeLimitExceeded("read", 1000, 500, "test.txt")
    assert "read size 1000 bytes exceeds limit of 500 bytes" in str(error)
    assert error.operation == "read"
    assert error.size == 1000
    assert error.limit == 500


def test_invalid_mode_error():
    """Test InvalidMode formatting."""
    error = InvalidMode("x", ["w", "a"])
    assert "Invalid mode 'x'" in str(error)
    assert "'w'" in str(error)
    assert "'a'" in str(error)


def test_rate_limit_error():
    """Test RateLimitError formatting."""
    error = RateLimitError(15.5, 10.0)
    assert "Rate limit exceeded" in str(error)
    assert "15.50 ops/sec" in str(error)
    assert "10.00 ops/sec limit" in str(error)
