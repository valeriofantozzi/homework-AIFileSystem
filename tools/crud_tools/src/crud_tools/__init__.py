"""
crud_tools: High-level CRUD operations for the AI File System agent.

This package provides list/read/write/delete/answer tools for use by the agent.
"""

__version__ = "0.1.0"

from .question_tool import answer_question_about_files, create_question_tool_function
from .tools import create_file_tools

__all__ = [
    "create_file_tools",
    "answer_question_about_files",
    "create_question_tool_function"
]
