"""
Intelligent file analysis tool using LLM integration.

This module provides tools for answering questions about file contents by
reading multiple files and synthesizing information using a lightweight LLM.
The LLM model selection is configurable through the centralized model configuration.
"""

from typing import Any

from workspace_fs import FileSystemTools, Workspace, WorkspaceError

try:
    from pydantic_ai import Agent
    PYDANTIC_AI_AVAILABLE = True
except ImportError:
    PYDANTIC_AI_AVAILABLE = False

try:
    from config import get_model_for_role
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False


def _extract_result_content(result: Any) -> str:
    """
    Extract content from pydantic-ai result object.

    Handles different possible result structures that pydantic-ai might return.

    Args:
        result: Result object from pydantic-ai agent.run()

    Returns:
        String content from the result.
    """
    # Try different possible attributes that pydantic-ai might use
    if hasattr(result, 'output'):
        return str(result.output)
    elif hasattr(result, 'data'):
        return str(result.data)
    elif hasattr(result, 'content'):
        return str(result.content)
    elif hasattr(result, 'text'):
        return str(result.text)
    elif hasattr(result, 'message'):
        return str(result.message)
    else:
        # Fallback: convert result to string directly
        return str(result)


async def answer_question_about_files(
    workspace: Workspace,
    query: str,
    max_files: int = 10,
    max_content_per_file: int = 2048,
    llm_model: str | None = None,
    role: str = "file_analysis",
    **fs_kwargs: Any
) -> str:
    """
    Answer a question about files in the workspace using LLM analysis.

    This function reads a sample of files from the workspace and uses an LLM
    to analyze their contents and answer the user's question. The LLM model
    is selected based on the configured role assignment.

    Args:
        workspace: The workspace instance for secure operations.
        query: The question to answer about the files.
        max_files: Maximum number of files to analyze.
        max_content_per_file: Maximum characters to read from each file.
        llm_model: Override LLM model (if None, uses configured model for role).
        role: Role-based model selection (default: 'file_analysis').
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
        # Determine which model to use
        if llm_model is None:
            if CONFIG_AVAILABLE:
                try:
                    model_provider = get_model_for_role(role)
                    # For pydantic-ai, we need the provider:model format
                    llm_model = f"{model_provider.provider_name}:{model_provider.model_name}"
                except Exception:
                    # Fallback to default if configuration fails
                    llm_model = "openai:gpt-4o-mini"
            else:
                # Fallback when configuration is not available
                llm_model = "openai:gpt-4o-mini"

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
        try:
            result = await analysis_agent.run(prompt)
            # Use helper function to extract content from different result structures
            return _extract_result_content(result)
        except Exception as llm_error:
            # If the primary model fails (e.g., missing API key), try fallback
            error_msg = str(llm_error).lower()
            if any(keyword in error_msg for keyword in ['api key', 'authentication', 'key', 'unauthorized']):
                # Try fallback to OpenAI if primary model fails due to API key issues
                if llm_model != "openai:gpt-4o-mini":
                    try:
                        fallback_agent = Agent(
                            model="openai:gpt-4o-mini",
                            system_prompt=(
                                "You are a helpful assistant that analyzes file contents and "
                                "answers questions about them. You will be given the contents "
                                "of multiple files and a question. Provide a concise, accurate "
                                "answer based on the file contents. If the files don't contain "
                                "relevant information, say so clearly."
                            ),
                        )
                        fallback_result = await fallback_agent.run(prompt)
                        # Use helper function to extract content from fallback result
                        response = _extract_result_content(fallback_result)
                        return f"[Using fallback model due to {llm_model.split(':')[0]} API key issue] {response}"
                    except Exception:
                        # If fallback also fails, return informative error
                        return f"Unable to analyze files: {llm_model.split(':')[0]} API key not configured and OpenAI fallback also failed. Please configure API keys or use local models."
                else:
                    # Already using OpenAI, no fallback available
                    return f"Unable to analyze files: OpenAI API key not configured. Please set OPENAI_API_KEY environment variable."
            else:
                # Re-raise non-API-key related errors
                raise llm_error

    except Exception as e:
        raise WorkspaceError(f"Failed to analyze files for query '{query}': {e}") from e


def create_question_tool_function(workspace: Workspace, role: str = "file_analysis", **kwargs: Any):
    """
    Create a question tool function for manual registration with agents.

    The created function uses the centralized model configuration to select
    the appropriate LLM for the specified role.

    Args:
        workspace: The workspace instance for secure operations.
        role: Role-based model selection (default: 'file_analysis').
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
        return await answer_question_about_files(
            workspace=workspace,
            query=query,
            role=role,
            **kwargs
        )

    return question_tool_func
