"""
Intelligent file analysis tool using LLM integration.

This module provides tools for answering questions about file contents by
reading multiple files and synthesizing information using a lightweight LLM.
"""

from typing import Any

from workspace_fs import FileSystemTools, Workspace, WorkspaceError

try:
    from pydantic_ai import Agent
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False


async def answer_question_about_files(
    workspace: Workspace,
    query: str,
    max_files: int = 10,
    max_content_per_file: int = 2048,
    llm_model: str = "openai:gpt-4o-mini",
    **fs_kwargs: Any
) -> str:
    """
    Answer a question about files in the workspace using LLM analysis.

    This function reads a sample of files from the workspace and uses an LLM
    to analyze their contents and answer the user's question.

    Args:
        workspace: The workspace instance for secure operations.
        query: The question to answer about the files.
        max_files: Maximum number of files to analyze.
        max_content_per_file: Maximum characters to read from each file.
        llm_model: The LLM model to use for analysis.
        **fs_kwargs: Additional arguments for FileSystemTools.

    Returns:
        A synthesized answer based on file contents.

    Raises:
        WorkspaceError: If files cannot be read or analyzed.
        ImportError: If pydantic-ai is not available.
    """
    if not PYDANTIC_AI_AVAILABLE:
        raise ImportError(
            "pydantic-ai is required for file question functionality. "
            "Install it with: pip install pydantic-ai"
        )

    try:
        # Create FileSystemTools with size limit for content reading
        fs_tools = FileSystemTools(workspace, **fs_kwargs)

        # Get list of files
        files = fs_tools.list_files()

        if not files:
            return "No files found in the workspace to analyze."

        # Limit number of files to analyze
        files_to_analyze = files[:max_files]

        # Read file contents
        file_contents = {}
        for filename in files_to_analyze:
            try:
                content = fs_tools.read_file(filename)
                # Truncate content if too long
                if len(content) > max_content_per_file:
                    content = content[:max_content_per_file] + "...[truncated]"
                file_contents[filename] = content
            except Exception as e:
                # Skip files that can't be read
                file_contents[filename] = f"[Error reading file: {e}]"

        # Prepare context for LLM
        context = "File contents:\n\n"
        for filename, content in file_contents.items():
            context += f"=== {filename} ===\n{content}\n\n"

        # Construct prompt
        prompt = (
            f"{context}\nQuestion: {query}\n\n"
            "Please provide a helpful answer based on the file contents above."
        )

        # Create LLM agent for analysis
        analysis_agent = Agent(
            model=llm_model,
            system_prompt=(
                "You are a helpful assistant that analyzes file contents and "
                "answers questions about them. You will be given the contents "
                "of multiple files and a question. Provide a concise, accurate "
                "answer based on the file contents. If the files don't contain "
                "relevant information, say so clearly."
            ),
        )

        # Get response from LLM
        result = await analysis_agent.run(prompt)
        return result.output

    except Exception as e:
        raise WorkspaceError(f"Failed to analyze files for query '{query}': {e}") from e


def create_question_tool_function(workspace: Workspace, **kwargs: Any):
    """
    Create a question tool function for manual registration with agents.

    Args:
        workspace: The workspace instance for secure operations.
        **kwargs: Additional arguments for the question tool.

    Returns:
        Function that can be manually registered as a tool.
    """
    async def question_tool_func(query: str) -> str:
        """
        Answer questions about files in the workspace by analyzing their contents.

        This tool reads multiple files from the workspace and uses AI analysis
        to provide comprehensive answers about their contents, relationships,
        and patterns.

        Args:
            query: The question to answer about the files.

        Returns:
            A synthesized answer based on analysis of file contents.
        """
        return await answer_question_about_files(workspace, query, **kwargs)

    return question_tool_func
