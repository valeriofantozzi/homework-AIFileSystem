"""Test FileSystemTools behavior and implementation details."""

import tempfile
import time
from pathlib import Path

import pytest
from workspace_fs import (
    FileSystemTools,
    InvalidMode,
    PathTraversalError,
    RateLimitError,
    SizeLimitExceeded,
    Workspace,
    WorkspaceError,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Workspace(temp_dir)
        yield workspace


@pytest.fixture
def fs_tools(temp_workspace):
    """Create FileSystemTools with test-friendly limits."""
    return FileSystemTools(
        temp_workspace,
        max_read=1024,  # 1KB for testing
        max_write=1024,  # 1KB for testing
        rate_limit=5.0,  # 5 ops/sec for testing
    )


class TestFileSystemToolsBehavior:
    """Test actual file operations and behavior."""

    def test_list_files_empty_workspace(self, fs_tools):
        """Test listing files in empty workspace."""
        files = fs_tools.list_files()
        assert files == []

    def test_list_files_with_content(self, fs_tools):
        """Test listing files with actual content."""
        # Create test files
        fs_tools.write_file("file1.txt", "content1")
        time.sleep(0.01)  # Ensure different timestamps
        fs_tools.write_file("file2.txt", "content2")
        time.sleep(0.01)
        fs_tools.write_file("file3.txt", "content3")

        files = fs_tools.list_files()

        # Should return all files, newest first
        assert len(files) == 3
        assert "file3.txt" in files
        assert "file2.txt" in files
        assert "file1.txt" in files
        # Newest should be first (file3.txt was created last)
        assert files[0] == "file3.txt"

    def test_list_files_ignores_hidden_and_directories(self, fs_tools, temp_workspace):
        """Test that list_files ignores hidden files and directories."""
        # Create regular file
        fs_tools.write_file("visible.txt", "content")

        # Create hidden file directly
        hidden_file = temp_workspace.root / ".hidden"
        hidden_file.write_text("hidden content")

        # Create directory
        test_dir = temp_workspace.root / "testdir"
        test_dir.mkdir()

        files = fs_tools.list_files()

        # Should only return visible files
        assert files == ["visible.txt"]

    def test_read_file_success(self, fs_tools):
        """Test successful file reading."""
        content = "Hello, World!"
        fs_tools.write_file("test.txt", content)

        read_content = fs_tools.read_file("test.txt")
        assert read_content == content

    def test_read_file_not_found(self, fs_tools):
        """Test reading non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found: nonexistent.txt"):
            fs_tools.read_file("nonexistent.txt")

    def test_read_file_size_limit(self, fs_tools):
        """Test reading file that exceeds size limit."""
        # Create file larger than max_read (1KB)
        large_content = "x" * 2000  # 2KB content
        fs_tools_large = FileSystemTools(
            fs_tools.workspace, max_read=10000, max_write=10000, rate_limit=10.0
        )
        fs_tools_large.write_file("large.txt", large_content)

        # Now try to read with small limit
        with pytest.raises(SizeLimitExceeded):
            fs_tools.read_file("large.txt")

    def test_read_file_directory_error(self, fs_tools, temp_workspace):
        """Test reading a directory instead of file."""
        # Create directory
        test_dir = temp_workspace.root / "testdir"
        test_dir.mkdir()

        with pytest.raises(WorkspaceError, match="Path is not a file"):
            fs_tools.read_file("testdir")

    def test_write_file_create_new(self, fs_tools):
        """Test writing to new file."""
        content = "New file content"
        result = fs_tools.write_file("new.txt", content)

        assert "written" in result
        assert "new.txt" in result

        # Verify content
        read_content = fs_tools.read_file("new.txt")
        assert read_content == content

    def test_write_file_overwrite(self, fs_tools):
        """Test overwriting existing file."""
        # Create initial file
        fs_tools.write_file("test.txt", "original")

        # Overwrite
        new_content = "overwritten"
        result = fs_tools.write_file("test.txt", new_content, "w")

        assert "written" in result

        # Verify content was overwritten
        read_content = fs_tools.read_file("test.txt")
        assert read_content == new_content

    def test_write_file_append(self, fs_tools):
        """Test appending to existing file."""
        # Create initial file
        original = "original\n"
        fs_tools.write_file("test.txt", original)

        # Append
        append_content = "appended"
        result = fs_tools.write_file("test.txt", append_content, "a")

        assert "appended" in result

        # Verify content was appended
        read_content = fs_tools.read_file("test.txt")
        assert read_content == original + append_content

    def test_write_file_invalid_mode(self, fs_tools):
        """Test writing with invalid mode."""
        with pytest.raises(InvalidMode):
            fs_tools.write_file("test.txt", "content", "x")

    def test_write_file_size_limit(self, fs_tools):
        """Test writing content that exceeds size limit."""
        # Create content larger than max_write (1KB)
        large_content = "x" * 2000  # 2KB content

        with pytest.raises(SizeLimitExceeded):
            fs_tools.write_file("large.txt", large_content)

    def test_delete_file_success(self, fs_tools):
        """Test successful file deletion."""
        # Create file
        fs_tools.write_file("delete_me.txt", "content")

        # Verify it exists
        files = fs_tools.list_files()
        assert "delete_me.txt" in files

        # Delete it
        result = fs_tools.delete_file("delete_me.txt")
        assert "deleted" in result
        assert "delete_me.txt" in result

        # Verify it's gone
        files = fs_tools.list_files()
        assert "delete_me.txt" not in files

    def test_delete_file_not_found(self, fs_tools):
        """Test deleting non-existent file."""
        with pytest.raises(FileNotFoundError, match="File not found: nonexistent.txt"):
            fs_tools.delete_file("nonexistent.txt")

    def test_delete_file_directory_error(self, fs_tools, temp_workspace):
        """Test deleting a directory instead of file."""
        # Create directory
        test_dir = temp_workspace.root / "testdir"
        test_dir.mkdir()

        with pytest.raises(WorkspaceError, match="Path is not a file"):
            fs_tools.delete_file("testdir")

    def test_rate_limiting(self, temp_workspace):
        """Test rate limiting functionality."""
        # Create tools with very strict rate limit
        fs_tools = FileSystemTools(temp_workspace, rate_limit=2.0)  # 2 ops/sec

        # First two operations should succeed
        fs_tools.write_file("test1.txt", "content1")
        fs_tools.write_file("test2.txt", "content2")

        # Third operation should fail due to rate limit
        with pytest.raises(RateLimitError):
            fs_tools.write_file("test3.txt", "content3")

        # After waiting, should work again
        time.sleep(1.1)  # Wait for rate limit window to reset
        fs_tools.write_file("test3.txt", "content3")  # Should succeed

    def test_unicode_handling(self, fs_tools):
        """Test handling of Unicode content."""
        unicode_content = "Hello 世界! 🌍 Café naïve résumé"

        fs_tools.write_file("unicode.txt", unicode_content)
        read_content = fs_tools.read_file("unicode.txt")

        assert read_content == unicode_content

    def test_path_traversal_protection(self, fs_tools):
        """Test protection against path traversal attacks."""
        # Current implementation rejects directory separators at the filename level
        with pytest.raises(ValueError, match="directory separators"):
            fs_tools.read_file("../../../etc/passwd")

        with pytest.raises(ValueError, match="directory separators"):
            fs_tools.write_file("../escape.txt", "content")

        with pytest.raises(ValueError, match="directory separators"):
            fs_tools.delete_file("../../sensitive.txt")

    def test_tool_properties(self, fs_tools):
        """Test FileSystemTools properties."""
        assert fs_tools.max_read == 1024
        assert fs_tools.max_write == 1024
        assert fs_tools.rate_limit == 5.0
        assert isinstance(fs_tools.workspace, Workspace)

    def test_tool_string_representation(self, fs_tools):
        """Test string representations."""
        str_repr = str(fs_tools)
        assert "FileSystemTools" in str_repr
        assert "1024" in str_repr  # max_read/max_write
        assert "5.0" in str_repr  # rate_limit

        repr_str = repr(fs_tools)
        assert "FileSystemTools" in repr_str
        assert "max_read=1024" in repr_str
        assert "max_write=1024" in repr_str
        assert "rate_limit=5.0" in repr_str


class TestWorkspaceBehavior:
    """Test Workspace class behavior."""

    def test_workspace_creates_directory(self):
        """Test that workspace creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_path = Path(temp_dir) / "new_workspace"
            assert not nonexistent_path.exists()

            workspace = Workspace(str(nonexistent_path))
            assert nonexistent_path.exists()
            assert nonexistent_path.is_dir()
            assert workspace.root == nonexistent_path.resolve()

    def test_workspace_symlink_protection(self, temp_workspace):
        """Test protection against symlink attacks."""
        # Create a file outside workspace
        with tempfile.TemporaryDirectory() as outside_dir:
            outside_file = Path(outside_dir) / "secret.txt"
            outside_file.write_text("secret data")

            # Create symlink inside workspace pointing outside
            symlink_path = temp_workspace.root / "symlink_attack"
            try:
                symlink_path.symlink_to(outside_file)

                # Should raise PathTraversalError when symlink resolves outside workspace
                with pytest.raises(PathTraversalError):
                    temp_workspace.safe_join("symlink_attack")
            except OSError:
                # Skip test if symlinks aren't supported on this system
                pytest.skip("Symlinks not supported on this system")

    def test_workspace_safe_join_deep_path(self, temp_workspace):
        """Test safe_join with simple filenames (no nested paths allowed)."""
        # Current implementation only allows simple filenames
        safe_path = temp_workspace.safe_join("file.txt")
        expected = temp_workspace.root / "file.txt"
        assert safe_path == expected

    def test_workspace_string_representation(self, temp_workspace):
        """Test workspace string representations."""
        str_repr = str(temp_workspace)
        assert "Workspace" in str_repr
        assert str(temp_workspace.root) in str_repr

        repr_str = repr(temp_workspace)
        assert "Workspace" in repr_str
        assert str(temp_workspace.root) in repr_str
