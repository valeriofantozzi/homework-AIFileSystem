# workspace-fs

Secure file system operations with sandbox enforcement.

This package provides tools for secure file operations within a controlled workspace, enforcing path safety, size limits, and rate limiting.

## Features

- **Sandbox enforcement**: All operations restricted to a predefined workspace directory
- **Path safety**: Prevents directory traversal and symlink attacks
- **Size limits**: Configurable read/write size limits
- **Rate limiting**: Prevents runaway operations
- **Safe CRUD operations**: List, read, write, and delete files securely

## Installation

```bash
pip install -e .
```

## Development

```bash
# Install development dependencies
poetry install

# Run tests
poetry run pytest

# Run linting
poetry run ruff .

# Run security checks
poetry run bandit -r src/
```

## Usage

```python
from workspace_fs import Workspace, FileSystemTools

# Initialize workspace
workspace = Workspace("/path/to/workspace")
fs_tools = FileSystemTools(workspace)

# Use file operations
files = fs_tools.list_files()
content = fs_tools.read_file("example.txt")
fs_tools.write_file("new_file.txt", "content")
fs_tools.delete_file("old_file.txt")
```

## API Reference

Documentation for the public API will be available after implementation.
