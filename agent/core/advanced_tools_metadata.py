"""
Advanced tool metadata registration for dynamically loaded tools.

This module provides metadata for tools that are created dynamically
or loaded from various modules.
"""

from .tool_metadata import tool_metadata_registry, ToolMetadata

# Register metadata for advanced tools that might be loaded dynamically
ADVANCED_TOOLS_METADATA = {
    "get_file_info": ToolMetadata(
        name="get_file_info",
        description="Get detailed information about a file (size, dates, permissions)",
        parameters={"filename": "str"},
        examples=["get info for config.json", "show file details", "file metadata"]
    ),
    "find_files_by_pattern": ToolMetadata(
        name="find_files_by_pattern",
        description="Find files matching a specific pattern or containing text",
        parameters={"pattern": "str"},
        examples=["find files matching *.py", "search for pattern", "files containing text"]
    ),
    "read_newest_file": ToolMetadata(
        name="read_newest_file",
        description="Read the contents of the most recently modified file",
        parameters={},
        examples=["read newest file", "show latest file", "most recent file content"]
    ),
    "find_largest_file": ToolMetadata(
        name="find_largest_file",
        description="Find the largest file in the directory",
        parameters={},
        examples=["find largest file", "which file is biggest", "largest file size"]
    ),
    "answer_question_about_files": ToolMetadata(
        name="answer_question_about_files",
        description="Answer questions about files using AI analysis",
        parameters={"query": "str"},
        examples=["what do these files contain", "analyze file contents", "question about files"]
    ),
    "help": ToolMetadata(
        name="help",
        description="Get help and list available commands",
        parameters={},
        examples=["help", "show commands", "what can you do"]
    )
}

def register_advanced_tools_metadata():
    """Register metadata for advanced tools in the global registry."""
    for tool_name, metadata in ADVANCED_TOOLS_METADATA.items():
        tool_metadata_registry.register_tool_metadata(tool_name, metadata)

# Auto-register when module is imported
register_advanced_tools_metadata()
