# CRUD Tools

High-level CRUD operations for the AI File System agent.

This package provides Pydantic-AI tool wrappers around the `workspace_fs` package, exposing secure file operations and intelligent file querying capabilities for use by autonomous agents.

## Features

- **list_files()**: List all files in workspace, sorted by modification time
- **read_file(filename)**: Read file content with size limits and error handling
- **write_file(filename, content, mode)**: Write content to files with validation
- **delete_file(filename)**: Safely delete files with security checks
- **answer_question_about_files(query)**: Intelligent multi-file analysis using LLM

## Installation

This package is designed to be installed as part of the AI File System project:

```bash
cd tools/crud_tools
poetry install
```

## Usage

```python
from crud_tools import create_file_tools
from workspace_fs import Workspace

# Create workspace and tools
workspace = Workspace("/path/to/workspace")
tools = create_file_tools(workspace)

# Tools are ready for use with Pydantic-AI agents
```

## Architecture

This package follows high cohesion, low coupling principles:

- **High Cohesion**: Each tool has a single, well-defined responsibility
- **Low Coupling**: Depends only on workspace_fs abstractions
- **Security**: All operations are sandboxed and rate-limited
- **Testability**: Mock-friendly design with dependency injection

## License

This project is part of the AI File System assignment.
