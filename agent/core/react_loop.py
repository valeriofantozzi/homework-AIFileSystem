"""
ReAct reasoning loop implementation.

This module implements the ReAct (Reasoning-Action-Observation) pattern for
autonomous agent reasoning. The loop enables the agent to think through problems
step by step, take actions with tools, and observe results to continue reasoning.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel

from config.model_config import ModelProvider
# Import diagnostics for tool usage tracking
from agent.diagnostics import log_tool_usage
# Import the LLM tool selector for intelligent tool selection
from agent.core.llm_tool_selector import LLMToolSelector, ToolSelectionResult


class ReActPhase(Enum):
    """Phases        # Check for "largest" file multi-step operations
        if "largest" in query_lower or "biggest" in query_lower:
            actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
            if len(actions_taken) == 1 and actions_taken[0].tool_name == "list_files":
                # We listed files, now need to find the largest
                return True
            elif len(actions_taken) == 2 and actions_taken[-1].tool_name == "find_largest_file":
                # We found the largest file, continue if user wants to read it
                if "read" in query_lower or "content" in query_lower or "what" in query_lower:
                    return True
                return False  # Just wanted to know the largest file
            return len(actions_taken) < 3  # Allow up to 3 steps for this queryct reasoning loop."""
    THINK = "think"
    ACT = "act"
    OBSERVE = "observe"
    COMPLETE = "complete"


@dataclass
class ReActStep:
    """A single step in the ReAct reasoning process."""
    phase: ReActPhase
    step_number: int
    content: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    tool_result: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class ToolChainContext:
    """Enhanced context for tool chaining with better memory management."""
    tool_outputs: Dict[str, Any] = field(default_factory=dict)
    file_context: Dict[str, str] = field(default_factory=dict)  # filename -> content cache
    discovered_files: List[str] = field(default_factory=list)
    operation_history: List[str] = field(default_factory=list)
    
    def add_tool_output(self, tool_name: str, output: Any) -> None:
        """Add tool output to context for future reference."""
        self.tool_outputs[tool_name] = output
        self.operation_history.append(f"{tool_name}: {str(output)[:100]}...")
    
    def get_recent_files(self) -> List[str]:
        """Get recently discovered files."""
        return self.discovered_files[-10:]  # Last 10 files
    
    def cache_file_content(self, filename: str, content: str) -> None:
        """Cache file content for efficient access."""
        self.file_context[filename] = content
    
    def get_cached_content(self, filename: str) -> Optional[str]:
        """Get cached file content if available."""
        return self.file_context.get(filename)
    
    def get_context_summary(self) -> str:
        """Get a summary of the current context for reasoning."""
        summary = []
        if self.discovered_files:
            summary.append(f"Files discovered: {', '.join(self.get_recent_files())}")
        if self.tool_outputs:
            recent_tools = list(self.tool_outputs.keys())[-3:]  # Last 3 tools
            summary.append(f"Recent tools used: {', '.join(recent_tools)}")
        return "; ".join(summary) if summary else "No context available"


@dataclass
class ReActResult:
    """Result from a complete ReAct reasoning loop."""
    response: str
    tools_used: List[str] = field(default_factory=list)
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    iterations: int = 0
    tool_chain_context: Optional[ToolChainContext] = None


@dataclass
class ConsolidatedReActResponse:
    """Structured response from a single LLM call containing all ReAct phases."""
    thinking: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    continue_reasoning: bool = True
    final_response: Optional[str] = None
    confidence: float = 0.8
    
    @classmethod
    def from_json_string(cls, json_str: str) -> 'ConsolidatedReActResponse':
        """Parse JSON response from LLM into structured format."""
        try:
            data = json.loads(json_str)
            return cls(
                thinking=data.get("thinking", "No thinking provided"),
                tool_name=data.get("tool_name"),
                tool_args=data.get("tool_args", {}),
                continue_reasoning=data.get("continue_reasoning", True),
                final_response=data.get("final_response"),
                confidence=data.get("confidence", 0.8)
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Fallback to text parsing if JSON fails
            return cls(
                thinking=f"Failed to parse structured response: {json_str}",
                continue_reasoning=False,
                final_response=json_str
            )


class ReActLoop:
    """
    Implementation of the ReAct (Reasoning-Action-Observation) pattern.
    
    This class manages the reasoning loop that allows an AI agent to:
    1. THINK: Reason about the problem and plan next actions
    2. ACT: Execute tools to gather information or make changes
    3. OBSERVE: Process tool results and continue reasoning
    4. COMPLETE: Provide final response when done
    
    The loop maintains a scratchpad of all reasoning steps for transparency
    and debugging purposes.
    """
    
    def __init__(
        self,
        model_provider: ModelProvider,
        tools: Dict[str, Any],
        logger: Optional[structlog.BoundLogger] = None,
        max_iterations: int = 10,
        debug_mode: bool = False,
        llm_response_func: Optional[callable] = None,
        mcp_thinking_tool: Optional[callable] = None,
        use_llm_tool_selector: bool = True
    ) -> None:
        """
        Initialize the ReAct loop.
        
        Args:
            model_provider: Configured model provider for reasoning
            tools: Dictionary of available tools
            logger: Structured logger instance
            max_iterations: Maximum reasoning iterations to prevent infinite loops
            debug_mode: Enable detailed step tracking
            llm_response_func: Function to get LLM responses for reasoning
            mcp_thinking_tool: MCP sequential thinking tool for LLM-based tool selection
            use_llm_tool_selector: Whether to use LLM-based tool selection instead of pattern matching
        """
        self.model_provider = model_provider
        self.tools = tools
        self.logger = logger or structlog.get_logger(__name__)
        self.max_iterations = max_iterations
        self.debug_mode = debug_mode
        self.llm_response_func = llm_response_func
        self.use_llm_tool_selector = use_llm_tool_selector
        
        # Initialize LLM tool selector if enabled and thinking tool is available
        self.llm_tool_selector = None
        if use_llm_tool_selector and mcp_thinking_tool:
            try:
                self.llm_tool_selector = LLMToolSelector(mcp_thinking_tool)
                self.logger.info("Initialized LLM-based tool selector")
            except Exception as e:
                self.logger.warning(f"Failed to initialize LLM tool selector: {e}, falling back to pattern matching")
                self.use_llm_tool_selector = False
        elif use_llm_tool_selector:
            self.logger.warning("LLM tool selector requested but no MCP thinking tool provided, using pattern matching")
            self.use_llm_tool_selector = False
        
        # Reasoning state
        self.scratchpad: List[ReActStep] = []
        self.current_phase = ReActPhase.THINK
        self.iteration_count = 0
    
    def _reset_state(self) -> None:
        """Reset the reasoning state for a new conversation."""
        self.scratchpad = []
        self.current_phase = ReActPhase.THINK
        self.iteration_count = 0
    
    def _build_context_summary(self) -> str:
        """Build a summary of the current reasoning context."""
        if not self.scratchpad:
            return "No previous reasoning steps."
        
        context_parts = []
        for step in self.scratchpad[-3:]:  # Last 3 steps for context
            if step.phase == ReActPhase.ACT and step.tool_result:
                context_parts.append(f"Used {step.tool_name}: {step.tool_result[:100]}...")
            elif step.phase == ReActPhase.THINK:
                context_parts.append(f"Thought: {step.content[:100]}...")
        
        return "\n".join(context_parts) if context_parts else "No relevant context."
    
    async def _translate_to_english(self, query: str) -> tuple[str, str]:
        """
        Translate user query to English if needed.
        
        Args:
            query: Original user query in any language
            
        Returns:
            Tuple of (translated_query, original_query)
        """
        # Check if query appears to be in English already
        # Simple heuristic: if query contains mostly English words, skip translation
        english_indicators = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        words = query.lower().split()
        english_word_count = sum(1 for word in words if any(indicator in word for indicator in english_indicators))
        
        # If more than 30% of words contain English indicators, assume it's English
        if len(words) > 0 and (english_word_count / len(words)) > 0.3:
            return query, query
        
        # Attempt translation using LLM
        if self.llm_response_func:
            translation_prompt = f"""Translate the following text to English. If the text is already in English, return it unchanged. Only return the translated text, no explanations:

"{query}"

Translation:"""
            
            try:
                translated = await self.llm_response_func(translation_prompt)
                # Clean up the response - remove quotes, extra whitespace
                translated = translated.strip().strip('"').strip("'").strip()
                
                self.logger.info(
                    "Query translation completed",
                    original=query,
                    translated=translated,
                    was_translated=(translated != query)
                )
                
                return translated, query
                
            except Exception as e:
                self.logger.warning(f"Translation failed, using original query: {e}")
                return query, query
        else:
            # No LLM function available, use original query
            return query, query

    async def execute(self, query: str, context: Any) -> ReActResult:
        """
        Execute the ReAct reasoning loop for a given query.
        
        Uses consolidated single-call approach for efficiency when llm_response_func is available,
        otherwise falls back to traditional multi-call approach.
        
        Args:
            query: User query to process
            context: Conversation context
            
        Returns:
            ReActResult with final response and reasoning trace
        """
        # Use consolidated approach if LLM response function is available
        if self.llm_response_func:
            return await self.execute_consolidated_iteration(query, context)
        
        # Fallback to traditional approach
        return await self.execute_traditional(query, context)

    async def execute_traditional(self, query: str, context: Any) -> ReActResult:
        """
        Execute the traditional multi-call ReAct reasoning loop (legacy method).
        
        This method is kept for compatibility when llm_response_func is not available.
        """
        self.logger.info(
            "Starting traditional ReAct reasoning loop",
            conversation_id=getattr(context, 'conversation_id', 'unknown'),
            query=query
        )
        
        # Initialize reasoning state
        self._reset_state()
        
        # FIRST STEP: Translate query to English for better tool selection and reasoning
        translated_query, original_query = await self._translate_to_english(query)
        
        # Update context with translated query for tool selection
        if hasattr(context, 'user_query'):
            context.original_user_query = context.user_query  # Store original
            context.user_query = translated_query  # Use translated for tool selection
        else:
            setattr(context, 'user_query', translated_query)
            setattr(context, 'original_user_query', query)
        
        # Add translation step to reasoning trace if translation occurred
        if translated_query != original_query:
            translation_step = ReActStep(
                phase=ReActPhase.THINK,
                step_number=len(self.scratchpad) + 1,
                content=f"TRANSLATION: Original query '{original_query}' translated to English: '{translated_query}'"
            )
            self.scratchpad.append(translation_step)
        
        # Start with initial thinking phase using the translated query
        current_thought = f"I need to help the user with: {translated_query}\n\nLet me think about what I need to do."
        
        try:
            while (self.iteration_count < self.max_iterations and 
                   self.current_phase != ReActPhase.COMPLETE):
                
                self.iteration_count += 1
                
                if self.current_phase == ReActPhase.THINK:
                    await self._think_phase(current_thought, context)
                    
                elif self.current_phase == ReActPhase.ACT:
                    tool_result = await self._act_phase(context)
                    current_thought = f"I observed: {tool_result}\n\nLet me think about what to do next."
                    
                elif self.current_phase == ReActPhase.OBSERVE:
                    await self._observe_phase(context)
            
            # Generate final response
            final_response = await self._generate_final_response(translated_query, context)
            
            result = ReActResult(
                response=final_response,
                tools_used=self._get_tools_used(),
                reasoning_steps=self._format_reasoning_steps(),
                success=True,
                iterations=self.iteration_count
            )
            
            self.logger.info(
                "ReAct loop completed successfully",
                conversation_id=getattr(context, 'conversation_id', 'unknown'),
                iterations=self.iteration_count,
                tools_used=result.tools_used,
                original_query=original_query,
                translated_query=translated_query
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "ReAct loop failed",
                conversation_id=getattr(context, 'conversation_id', 'unknown'),
                error=str(e),
                iterations=self.iteration_count
            )
            
            return ReActResult(
                response=f"I encountered an error during reasoning: {str(e)}",
                success=False,
                iterations=self.iteration_count
            )
    
    async def _think_phase(self, thought: str, context: Any) -> None:
        """Execute the THINK phase of reasoning."""
        step = ReActStep(
            phase=ReActPhase.THINK,
            step_number=len(self.scratchpad) + 1,
            content=thought
        )
        self.scratchpad.append(step)
        
        if self.debug_mode:
            self.logger.debug("THINK phase", content=thought)
        
        # Analyze if we need to take action
        if await self._should_take_action(thought):
            self.current_phase = ReActPhase.ACT
        else:
            self.current_phase = ReActPhase.COMPLETE
    
    async def _act_phase(self, context: Any) -> str:
        """Execute the ACT phase - call tools."""
        # Determine which tool to use and with what arguments
        tool_decision = await self._decide_tool_action(context)
        
        if not tool_decision:
            self.current_phase = ReActPhase.COMPLETE
            return "No action needed."
        
        tool_name = tool_decision.get("tool")
        tool_args = tool_decision.get("args", {})
        
        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not available"
            self.logger.warning("Invalid tool requested", tool=tool_name)
            self.current_phase = ReActPhase.COMPLETE
            return error_msg
        
        try:
            # Handle special cases
            if tool_name == "read_file" and tool_args.get("filename") == "LATEST_FILE":
                # First get the file list to find the latest file
                list_result = self.tools["list_files"]()
                if isinstance(list_result, list) and list_result:
                    latest_file = list_result[0]  # list_files returns newest first
                    tool_args["filename"] = latest_file
                    self.logger.info("Resolved LATEST_FILE", filename=latest_file)
                elif isinstance(list_result, str) and list_result.strip():
                    files = list_result.strip().split('\n')
                    if files and files[0]:  # list_files returns newest first
                        latest_file = files[0]
                        tool_args["filename"] = latest_file
                        self.logger.info("Resolved LATEST_FILE", filename=latest_file)
                    else:
                        self.current_phase = ReActPhase.COMPLETE
                        return "No files found in workspace"
                else:
                    self.current_phase = ReActPhase.COMPLETE
                    return "Could not list files to find latest"
            
            # Execute the tool
            tool_func = self.tools[tool_name]
            
            # Log tool usage for diagnostics
            log_tool_usage(tool_name, tool_args)
            
            # Handle both sync and async tools
            import asyncio
            import inspect
            
            if tool_args:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func(**tool_args)
                else:
                    result = tool_func(**tool_args)
            else:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func()
                else:
                    result = tool_func()
            
            # Record the action
            step = ReActStep(
                phase=ReActPhase.ACT,
                step_number=len(self.scratchpad) + 1,
                content=f"Calling {tool_name} with args: {tool_args}",
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=str(result)
            )
            self.scratchpad.append(step)
            
            if self.debug_mode:
                self.logger.debug("ACT phase", tool=tool_name, args=tool_args, result=result)
            
            self.current_phase = ReActPhase.OBSERVE
            return str(result)
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            step = ReActStep(
                phase=ReActPhase.ACT,
                step_number=len(self.scratchpad) + 1,
                content=error_msg,
                tool_name=tool_name,
                tool_args=tool_args,
                tool_result=error_msg  # Store the error in tool_result too
            )
            self.scratchpad.append(step)
            
            self.logger.error("Tool execution failed", tool=tool_name, error=str(e))
            self.current_phase = ReActPhase.COMPLETE
            return error_msg
    
    async def _observe_phase(self, context: Any) -> None:
        """Execute the OBSERVE phase - process tool results."""
        if not self.scratchpad:
            self.current_phase = ReActPhase.COMPLETE
            return
        
        last_step = self.scratchpad[-1]
        observation = f"I used {last_step.tool_name} and got: {last_step.tool_result}"
        
        step = ReActStep(
            phase=ReActPhase.OBSERVE,
            step_number=len(self.scratchpad) + 1,
            content=observation
        )
        self.scratchpad.append(step)
        
        if self.debug_mode:
            self.logger.debug("OBSERVE phase", observation=observation)
        
        # Decide if we need more actions or can complete
        if await self._should_continue_reasoning():
            self.current_phase = ReActPhase.THINK
        else:
            self.current_phase = ReActPhase.COMPLETE
    
    async def _should_take_action(self, thought: str) -> bool:
        """
        Determine if the current thought requires taking an action.
        
        Uses LLM reasoning to decide if an action is needed based on the current thought
        and reasoning context.
        """
        # Build context from scratchpad
        context_summary = self._build_context_summary()
        
        # Create a prompt to determine if action is needed
        decision_prompt = f"""
Based on the following thought and context, should I take an action with a tool?

Current thought: {thought}

Context from previous steps:
{context_summary}

Available tools: {', '.join(self.tools.keys())}

Respond with only 'YES' if I should take an action, or 'NO' if I can provide a final response.
Think about whether I have enough information to answer the user's question or if I need to use tools to gather more information.
"""
        
        try:
            # Use a lightweight decision - you could make this more sophisticated
            action_keywords = [
                "need to", "should", "let me", "i'll", "i will", "must",
                "list", "read", "write", "delete", "check", "find", "search",
                "create", "remove", "look", "see", "get", "fetch"
            ]
            
            thought_lower = thought.lower()
            has_action_keyword = any(keyword in thought_lower for keyword in action_keywords)
            
            # Also check if we haven't taken any actions yet
            actions_taken = len([s for s in self.scratchpad if s.phase == ReActPhase.ACT])
            
            # Take action if we have keywords or haven't done anything yet
            return has_action_keyword or actions_taken == 0
            
        except Exception as e:
            self.logger.warning("Error in action decision", error=str(e))
            # Default to taking action if uncertain
            return True
    
    async def _decide_tool_action(self, context: Any) -> Optional[Dict[str, Any]]:
        """
        Decide which tool to use based on current reasoning state.
        
        Analyzes the conversation context and reasoning history to determine
        the appropriate tool and arguments. Uses LLM-based selection when available,
        falls back to pattern matching.
        """
        if not self.scratchpad:
            return None
        
        # Try LLM-based tool selection first if enabled
        if self.use_llm_tool_selector and self.llm_tool_selector:
            llm_result = await self._llm_based_tool_selection(context)
            if llm_result:
                self.logger.info(f"Using LLM-selected tool: {llm_result['tool']}")
                return llm_result
            else:
                self.logger.warning("LLM tool selection failed, falling back to pattern matching")
        
        # Fallback to pattern-based tool selection
        return await self._pattern_based_tool_selection(context)
    
    async def _pattern_based_tool_selection(self, context: Any) -> Optional[Dict[str, Any]]:
        """
        Original pattern-based tool selection logic as fallback.
        
        This method contains the original tool selection logic based on keyword
        and pattern matching, kept as a reliable fallback.
        """
        # Get the current thought and build context
        last_thought = self.scratchpad[-1].content
        context_summary = self._build_context_summary()
        user_query = getattr(context, 'user_query', '')
        
        # Enhanced tool selection logic with better pattern matching
        thought_lower = last_thought.lower()
        query_lower = user_query.lower()
        
        # Check for multi-step operations first
        actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
        
        # Handle "largest" file queries (multi-step: list → find_largest → read)
        if ("largest" in query_lower or "biggest" in query_lower):
            if len(actions_taken) == 0:
                # First step: list files to see what's available
                return {"tool": "list_files", "args": {}}
            elif len(actions_taken) == 1 and actions_taken[0].tool_name == "list_files":
                # Second step: find the largest file
                return {"tool": "find_largest_file", "args": {}}
            elif len(actions_taken) == 2 and actions_taken[-1].tool_name == "find_largest_file":
                # Third step: read the largest file if requested
                if "read" in query_lower or "content" in query_lower or "what" in query_lower:
                    # Extract filename from the find_largest_file result
                    largest_result = actions_taken[-1].tool_result
                    if largest_result and largest_result.strip():
                        # Parse the formatted result to extract filename
                        # Expected format: "✅ Largest file: filename.txt (123 bytes) (0.00s)"
                        import re
                        filename_match = re.search(r'Largest file:\s*([^\s(]+)', largest_result)
                        if filename_match:
                            filename = filename_match.group(1)
                            return {"tool": "read_file", "args": {"filename": filename}}
                return None  # Just wanted to know the largest file
        
        # If this is a multi-step request ("first X, then Y"), continue with next step
        elif ("first" in query_lower and "then" in query_lower) or ("list" in query_lower and "read" in query_lower):
            if len(actions_taken) == 1 and actions_taken[0].tool_name == "list_files":
                # We did list_files, now check if we need to read something
                if "read" in query_lower:
                    filename = self._extract_filename(last_thought, user_query)
                    if filename:
                        return {"tool": "read_file", "args": {"filename": filename}}
        
        # Check for explicit tool mentions first
        if "find_files_by_pattern" in query_lower:
            # Extract pattern from query
            pattern = self._extract_pattern(user_query)
            if pattern:
                return {"tool": "find_files_by_pattern", "args": {"pattern": pattern}}
        
        if "get_file_info" in query_lower:
            # Extract filename from query
            filename = self._extract_filename(last_thought, user_query)
            if filename:
                return {"tool": "get_file_info", "args": {"filename": filename}}
        
        if "read_newest_file" in query_lower:
            return {"tool": "read_newest_file", "args": {}}
        
        # Analyze what the user wants and what we've learned so far
        
        # Check for directory-specific requests first
        if (("directories" in query_lower or "directory" in query_lower or "folders" in query_lower or 
             "folder" in query_lower or "cartelle" in query_lower) and
            ("list" in query_lower or "show" in query_lower or "mostra" in query_lower or 
             "lista" in query_lower) and
            not ("file" in query_lower)):  # Only directories, not files+directories
            if self.logger:
                self.logger.debug("Directory listing request detected", query=user_query)
            return {"tool": "list_directories", "args": {}}
        
        # Check for Italian "tutti i file e cartelle" pattern - this should select list_all
        elif (("tutti" in query_lower or "all" in query_lower) and 
              (("file" in query_lower and ("cartelle" in query_lower or "directory" in query_lower or "directories" in query_lower)) or
               ("files" in query_lower and ("cartelle" in query_lower or "directory" in query_lower or "directories" in query_lower)) or
               ("lista" in query_lower and "file" in query_lower and "cartelle" in query_lower))):
            if self.logger:
                self.logger.debug("Italian files and directories request detected", query=user_query)
            return {"tool": "list_all", "args": {}}
        
        # Check for "list all" or "show all" - use list_all that shows both files and directories
        elif (("list" in query_lower and "all" in query_lower) or 
              ("show" in query_lower and "all" in query_lower) or
              ("lista" in query_lower and "tutti" in query_lower) or
              # Handle "file e cartelle" - files and directories together
              ("file" in query_lower and "cartelle" in query_lower) or
              ("files" in query_lower and "cartelle" in query_lower)):
            return {"tool": "list_all", "args": {}}
        
        # Check for explicit file listing (avoid conflict with directory listing)
        elif ("list" in query_lower and "files" in query_lower) or "what files" in query_lower:
            return {"tool": "list_files", "args": {}}
        
        # Default file listing only if "list" appears without directory context
        elif ("list" in thought_lower and 
              not any(dir_word in thought_lower for dir_word in ["directories", "directory", "folders", "folder", "cartelle"])):
            if self.logger:
                self.logger.debug("Default file listing triggered", thought=last_thought[:100], query=user_query)
            return {"tool": "list_files", "args": {}}
        
        # Look for "newest" or "latest" file patterns
        elif ("newest" in query_lower or "latest" in query_lower or "most recent" in query_lower):
            if "read" in query_lower or "content" in query_lower or "what" in query_lower:
                # Use the direct newest file function
                return {"tool": "read_newest_file", "args": {}}
            else:
                return {"tool": "list_files", "args": {}}
        
        # Look for pattern matching requests
        elif ("find" in query_lower and "pattern" in query_lower) or ("containing" in query_lower):
            pattern = self._extract_pattern(user_query)
            if pattern:
                return {"tool": "find_files_by_pattern", "args": {"pattern": pattern}}
            else:
                return {"tool": "list_files", "args": {}}
        
        # Look for file information requests
        elif ("information" in query_lower or "info" in query_lower or "details" in query_lower or "metadata" in query_lower):
            filename = self._extract_filename(last_thought, user_query)
            if filename:
                return {"tool": "get_file_info", "args": {"filename": filename}}
            else:
                return {"tool": "list_files", "args": {}}
        
        # Look for filename extraction patterns for reading
        elif "read" in thought_lower or "content" in thought_lower or "open" in thought_lower:
            filename = self._extract_filename(last_thought, user_query)
            if filename and filename != "LATEST_FILE":
                return {"tool": "read_file", "args": {"filename": filename}}
            elif filename == "LATEST_FILE":
                return {"tool": "read_newest_file", "args": {}}
            else:
                # If no specific filename, might need to list files first
                return {"tool": "list_files", "args": {}}
        
        elif "write" in thought_lower or "create" in thought_lower or "save" in thought_lower:
            filename = self._extract_filename(last_thought, user_query)
            content = self._extract_content(last_thought, user_query)
            if filename and content:
                return {"tool": "write_file", "args": {"filename": filename, "content": content}}
            else:
                return None  # Need more information
        
        elif "delete" in thought_lower or "remove" in thought_lower:
            filename = self._extract_filename(last_thought, user_query)
            if filename:
                return {"tool": "delete_file", "args": {"filename": filename}}
            else:
                return {"tool": "list_files", "args": {}}  # List files to see what can be deleted
        
        elif "question" in thought_lower or "answer" in thought_lower or "about" in thought_lower:
            query_text = self._extract_question(last_thought, user_query)
            if query_text:
                return {"tool": "answer_question_about_files", "args": {"query": query_text}}
        
        # If we can't determine a specific action, default to listing files
        # This helps the agent understand what's available
        actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
        if not actions_taken:
            return {"tool": "list_files", "args": {}}
        
        return None
    
    async def _llm_based_tool_selection(self, context: Any) -> Optional[Dict[str, Any]]:
        """
        Use LLM-based reasoning to select the most appropriate tool.
        
        This method leverages the LLMToolSelector to make intelligent tool choices
        based on semantic understanding rather than simple pattern matching.
        """
        if not self.llm_tool_selector:
            return None
            
        # Get the current context and user query
        user_query = getattr(context, 'user_query', '')
        if not user_query:
            return None
        
        # Build available tools dictionary with descriptions
        available_tools = self._build_tools_metadata()
        
        # Build context for the LLM selector
        llm_context = self._build_llm_context(context)
        
        try:
            # Use LLM tool selector to choose the best tool
            selection_result: ToolSelectionResult = await self.llm_tool_selector.select_tool(
                user_query=user_query,
                available_tools=available_tools,
                context=llm_context
            )
            
            self.logger.info(
                f"LLM selected tool: {selection_result.selected_tool} "
                f"(confidence: {selection_result.confidence:.2f})"
            )
            
            # Log the reasoning for debugging
            if self.debug_mode:
                self.logger.debug(f"LLM tool selection reasoning: {selection_result.reasoning[:200]}...")
            
            # Convert to the expected format
            tool_action = {"tool": selection_result.selected_tool, "args": {}}
            
            # Add suggested parameters if available
            if selection_result.suggested_parameters:
                tool_action["args"].update(selection_result.suggested_parameters)
            
            # Handle special cases where we need to extract parameters from context
            if selection_result.selected_tool in ["read_file", "write_file", "delete_file", "get_file_info"]:
                if "filename" not in tool_action["args"]:
                    # Try to extract filename from reasoning or context
                    filename = self._extract_filename_from_context(context, selection_result)
                    if filename:
                        tool_action["args"]["filename"] = filename
            
            return tool_action
            
        except Exception as e:
            self.logger.error(f"Error in LLM tool selection: {e}")
            return None  # Fall back to pattern matching
    
    def _build_tools_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Build metadata about available tools for the LLM selector."""
        tools_metadata = {}
        
        # Define tool descriptions - these would ideally come from tool definitions
        tool_descriptions = {
            "list_files": {
                "description": "List all files in the current directory",
                "parameters": {}
            },
            "list_directories": {
                "description": "List only directories/folders in the current directory",
                "parameters": {}
            },
            "list_all": {
                "description": "List both files and directories in the current directory",
                "parameters": {}
            },
            "read_file": {
                "description": "Read the contents of a specific file",
                "parameters": {"filename": "string"}
            },
            "write_file": {
                "description": "Write content to a file",
                "parameters": {"filename": "string", "content": "string"}
            },
            "delete_file": {
                "description": "Delete a specific file",
                "parameters": {"filename": "string"}
            },
            "get_file_info": {
                "description": "Get detailed information about a file (size, dates, permissions)",
                "parameters": {"filename": "string"}
            },
            "find_files_by_pattern": {
                "description": "Find files matching a specific pattern or containing text",
                "parameters": {"pattern": "string"}
            },
            "read_newest_file": {
                "description": "Read the contents of the most recently modified file",
                "parameters": {}
            },
            "find_largest_file": {
                "description": "Find the largest file in the directory",
                "parameters": {}
            },
            "answer_question_about_files": {
                "description": "Answer questions about files using AI analysis",
                "parameters": {"query": "string"}
            },
            "help": {
                "description": "Get help and list available commands",
                "parameters": {}
            }
        }
        
        # Only include tools that are actually available
        for tool_name in self.tools.keys():
            if tool_name in tool_descriptions:
                tools_metadata[tool_name] = tool_descriptions[tool_name]
            else:
                # Fallback for unknown tools
                tools_metadata[tool_name] = {
                    "description": f"Tool: {tool_name}",
                    "parameters": {}
                }
        
        return tools_metadata
    
    def _build_llm_context(self, context: Any) -> Dict[str, Any]:
        """Build context information for the LLM tool selector."""
        llm_context = {}
        
        # Add current directory if available
        if hasattr(context, 'current_directory'):
            llm_context['current_directory'] = context.current_directory
        
        # Add previous actions from scratchpad
        actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
        if actions_taken:
            llm_context['previous_action'] = actions_taken[-1].tool_name
            llm_context['actions_history'] = [s.tool_name for s in actions_taken]
        
        # Add any discovered files from tool chain context
        if hasattr(context, 'tool_chain_context') and context.tool_chain_context:
            if context.tool_chain_context.discovered_files:
                llm_context['discovered_files'] = context.tool_chain_context.get_recent_files()
        
        # Detect language from user query if possible
        user_query = getattr(context, 'user_query', '')
        if any(italian_word in user_query.lower() for italian_word in ['lista', 'cartelle', 'directory', 'mostra']):
            llm_context['user_language'] = 'Italian'
        
        return llm_context
    
    def _extract_filename_from_context(self, context: Any, selection_result: ToolSelectionResult) -> Optional[str]:
        """Extract filename from context or reasoning for file operations."""
        # First check suggested parameters
        if 'filename' in selection_result.suggested_parameters:
            return selection_result.suggested_parameters['filename']
        
        # Try to extract from reasoning
        reasoning_lower = selection_result.reasoning.lower()
        user_query = getattr(context, 'user_query', '')
        
        # Use existing extraction method
        filename = self._extract_filename("", user_query)
        if filename and filename != "LATEST_FILE":
            return filename
            
        return None
    
    async def _should_continue_reasoning(self) -> bool:
        """Determine if reasoning should continue or if we can complete."""
        # Check if we've hit the max iterations
        if self.iteration_count >= self.max_iterations:
            return False
        
        # Check if we have enough information to provide a response
        actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
        if not actions_taken:
            return True  # Haven't taken any actions yet
        
        # If we've taken actions, check if the last one was successful
        last_action = actions_taken[-1]
        if last_action.tool_result and "error" not in last_action.tool_result.lower():
            return False  # Successful action, can complete
        
        return len(actions_taken) < 3  # Allow up to 3 actions
    
    async def _generate_final_response(self, query: str, context: Any) -> str:
        """Generate the final response based on reasoning steps."""
        # Find the most recent successful tool result
        for step in reversed(self.scratchpad):
            if step.phase == ReActPhase.ACT and step.tool_result:
                if "error" not in step.tool_result.lower():
                    return step.tool_result
        
        # If no successful tool execution, provide a helpful message
        return "I wasn't able to complete your request successfully. Please try rephrasing your question."
    
    def _get_tools_used(self) -> List[str]:
        """Get list of tools used during reasoning."""
        tools_used = []
        for step in self.scratchpad:
            if step.phase == ReActPhase.ACT and step.tool_name:
                tools_used.append(step.tool_name)
        return tools_used
    
    def _format_reasoning_steps(self) -> List[Dict[str, Any]]:
        """Format reasoning steps for the result."""
        formatted_steps = []
        for step in self.scratchpad:
            step_dict = {
                "phase": step.phase.value,
                "step_number": step.step_number,
                "content": step.content
            }
            if step.tool_name:
                step_dict["tool_name"] = step.tool_name
            if step.tool_args:
                step_dict["tool_args"] = step.tool_args
            if step.tool_result:
                step_dict["tool_result"] = step.tool_result
            formatted_steps.append(step_dict)
        return formatted_steps
    
    def _extract_filename(self, thought: str, query: str) -> Optional[str]:
        """Extract filename from thought or query text."""
        import re
        
        # Look for common filename patterns
        filename_patterns = [
            r"filename[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)",
            r"file[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)",
            r"read[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)",
            r"([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)",  # General filename pattern
            r"'([^']+\.[a-zA-Z0-9]+)'",  # Quoted filename
            r'"([^"]+\.[a-zA-Z0-9]+)"'   # Double quoted filename
        ]
        
        text = f"{thought} {query}".lower()
        
        for pattern in filename_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        # Special keywords
        if "newest" in text or "latest" in text:
            return "LATEST_FILE"
        
        return None
    
    def _extract_pattern(self, query: str) -> Optional[str]:
        """Extract search pattern from query text."""
        import re
        
        # Look for pattern in quotes
        pattern_matches = re.findall(r"pattern[:\s]+[\"']([^\"']+)[\"']", query.lower())
        if pattern_matches:
            return pattern_matches[0]
        
        # Look for file extensions
        ext_matches = re.findall(r"\*\.([a-zA-Z0-9]+)", query)
        if ext_matches:
            return f"*.{ext_matches[0]}"
        
        # Look for "containing" patterns
        containing_matches = re.findall(r"containing[:\s]+[\"']([^\"']+)[\"']", query.lower())
        if containing_matches:
            return containing_matches[0]
        
        return None
    
    def _extract_content(self, thought: str, query: str) -> Optional[str]:
        """Extract content to write from thought or query."""
        import re
        
        text = f"{thought} {query}"
        
        # Look for content in quotes
        content_patterns = [
            r"content[:\s]+[\"']([^\"']+)[\"']",
            r"write[:\s]+[\"']([^\"']+)[\"']",
            r"save[:\s]+[\"']([^\"']+)[\"']"
        ]
        
        for pattern in content_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_question(self, thought: str, query: str) -> Optional[str]:
        """Extract question text for question answering tool."""
        # Use the original query as the question
        if query.strip():
            return query.strip()
        
        # Fall back to extracting from thought
        if "question" in thought.lower():
            return thought.strip()
        
        return None

    async def execute_consolidated_iteration(self, query: str, context: Any) -> ReActResult:
        """
        Execute ReAct reasoning loop with consolidated single-call approach for cost efficiency.
        
        This method makes a single LLM call per iteration that includes all phases:
        THINK → DECIDE → ACT → CONTINUE evaluation in one structured response.
        
        Args:
            query: User query to process
            context: Conversation context
            
        Returns:
            ReActResult with final response and reasoning trace
        """
        self.logger.info(
            "Starting consolidated ReAct reasoning loop",
            conversation_id=getattr(context, 'conversation_id', 'unknown'),
            query=query
        )
        
        # Initialize reasoning state
        self._reset_state()
        
        # FIRST STEP: Translate query to English for better tool selection and reasoning
        translated_query, original_query = await self._translate_to_english(query)
        
        # Update context with translated query for tool selection
        if hasattr(context, 'user_query'):
            context.original_user_query = context.user_query  # Store original
            context.user_query = translated_query  # Use translated for tool selection
        else:
            setattr(context, 'user_query', translated_query)
            setattr(context, 'original_user_query', query)
        
        # Add translation step to reasoning trace if translation occurred
        if translated_query != original_query:
            translation_step = ReActStep(
                phase=ReActPhase.THINK,
                step_number=len(self.scratchpad) + 1,
                content=f"TRANSLATION: Original query '{original_query}' translated to English: '{translated_query}'"
            )
            self.scratchpad.append(translation_step)
        
        # Initialize tool chain context for better multi-step operations
        tool_chain_context = ToolChainContext()
        
        try:
            while (self.iteration_count < self.max_iterations):
                self.iteration_count += 1
                
                # Build consolidated prompt for this iteration
                consolidated_prompt = self._build_consolidated_prompt(
                    query=translated_query,
                    context=context,
                    reasoning_history=self.scratchpad,
                    available_tools=list(self.tools.keys()),
                    tool_chain_context=tool_chain_context
                )
                
                # Make single LLM call for all reasoning phases
                try:
                    response_text = await self.llm_response_func(consolidated_prompt)
                    parsed_response = ConsolidatedReActResponse.from_json_string(response_text)
                except Exception as e:
                    self.logger.warning(f"Failed to get LLM response or parse: {e}")
                    # Fallback to text-based processing with a safe default
                    error_text = f"Error in LLM call: {str(e)}"
                    parsed_response = ConsolidatedReActResponse(
                        thinking=error_text,
                        continue_reasoning=False,
                        final_response=error_text
                    )
                
                # Record the thinking step
                thinking_step = ReActStep(
                    phase=ReActPhase.THINK,
                    step_number=len(self.scratchpad) + 1,
                    content=parsed_response.thinking
                )
                self.scratchpad.append(thinking_step)
                
                if self.debug_mode:
                    self.logger.debug("THINK phase", content=parsed_response.thinking)
                
                # Execute tool if one was selected
                tool_result = None
                if parsed_response.tool_name:
                    tool_result = await self._execute_selected_tool(
                        parsed_response.tool_name,
                        parsed_response.tool_args or {},
                        tool_chain_context
                    )
                    
                    # Record the action step
                    action_step = ReActStep(
                        phase=ReActPhase.ACT,
                        step_number=len(self.scratchpad) + 1,
                        content=f"Calling {parsed_response.tool_name} with args: {parsed_response.tool_args}",
                        tool_name=parsed_response.tool_name,
                        tool_args=parsed_response.tool_args,
                        tool_result=tool_result
                    )
                    self.scratchpad.append(action_step)
                    
                    # Add tool output to context for future iterations
                    tool_chain_context.add_tool_output(parsed_response.tool_name, tool_result)
                    
                    if self.debug_mode:
                        self.logger.debug("ACT phase", 
                                        tool=parsed_response.tool_name, 
                                        args=parsed_response.tool_args, 
                                        result=tool_result)
                
                # Check if we should continue reasoning
                if not parsed_response.continue_reasoning or parsed_response.final_response:
                    # We have a final response, complete the loop
                    final_response = parsed_response.final_response or self._generate_response_from_context(
                        translated_query, tool_chain_context
                    )
                    break
                
                # If we executed a tool but no final response, continue iterating
                if tool_result is None and not parsed_response.continue_reasoning:
                    # No tool was executed and no continuation requested, complete
                    final_response = parsed_response.thinking
                    break
            
            # If we exceeded max iterations, generate response from context
            if self.iteration_count >= self.max_iterations:
                final_response = self._generate_response_from_context(translated_query, tool_chain_context)
                self.logger.warning("Max iterations reached, generating response from context")
            
            result = ReActResult(
                response=final_response,
                tools_used=self._get_tools_used(),
                reasoning_steps=self._format_reasoning_steps(),
                success=True,
                iterations=self.iteration_count,
                tool_chain_context=tool_chain_context
            )
            
            self.logger.info(
                "Consolidated ReAct loop completed successfully",
                conversation_id=getattr(context, 'conversation_id', 'unknown'),
                iterations=self.iteration_count,
                tools_used=result.tools_used,
                original_query=original_query,
                translated_query=translated_query
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Consolidated ReAct loop failed",
                conversation_id=getattr(context, 'conversation_id', 'unknown'),
                error=str(e),
                iterations=self.iteration_count
            )
            
            return ReActResult(
                response=f"I encountered an error during reasoning: {str(e)}",
                success=False,
                iterations=self.iteration_count
            )

    def _build_consolidated_prompt(
        self, 
        query: str, 
        context: Any, 
        reasoning_history: List[ReActStep], 
        available_tools: List[str],
        tool_chain_context: ToolChainContext
    ) -> str:
        """
        Build a comprehensive prompt that includes all ReAct phases in a single call.
        
        This prompt guides the LLM through thinking, tool selection, and continuation
        decisions in one structured response.
        """
        # Build context from previous reasoning steps
        previous_steps = ""
        if reasoning_history:
            step_summaries = []
            for step in reasoning_history[-5:]:  # Last 5 steps for context
                if step.phase == ReActPhase.THINK:
                    step_summaries.append(f"THOUGHT: {step.content}")
                elif step.phase == ReActPhase.ACT:
                    step_summaries.append(f"ACTION: Used {step.tool_name} → {step.tool_result}")
            previous_steps = "\n".join(step_summaries)
        
        # Build tool descriptions
        tool_descriptions = {
            "list_files": "List all files in the workspace",
            "list_directories": "List all directories in the workspace", 
            "list_all": "List both files and directories in the workspace",
            "read_file": "Read content of a specific file (args: filename)",
            "write_file": "Write content to a file (args: filename, content)",
            "delete_file": "Delete a specific file (args: filename)",
            "answer_question_about_files": "Answer questions about file content (args: question)",
            "read_newest_file": "Read the most recently modified file",
            "find_files_by_pattern": "Find files matching a pattern (args: pattern)",
            "get_file_info": "Get metadata about a file (args: filename)",
            "find_largest_file": "Find the largest file in the workspace",
            "find_files_by_extension": "Find files with specific extension (args: extension)"
        }
        
        available_tool_info = []
        for tool_name in available_tools:
            description = tool_descriptions.get(tool_name, f"Tool: {tool_name}")
            available_tool_info.append(f"- {tool_name}: {description}")
        
        # Get context summary from tool chain
        context_summary = tool_chain_context.get_context_summary()
        
        return f"""You are a file system assistant using ReAct reasoning. Analyze the user's query and decide your next action.

USER QUERY: {query}
WORKSPACE: {getattr(context, 'workspace_path', 'Unknown')}

PREVIOUS REASONING STEPS:
{previous_steps or "None - this is the first iteration"}

CONTEXT FROM TOOLS:
{context_summary}

AVAILABLE TOOLS:
{chr(10).join(available_tool_info)}

INSTRUCTIONS:
1. THINK through the problem step by step
2. DECIDE if you need to use a tool or can provide a final answer
3. If using a tool, specify the exact tool name and arguments
4. Determine if more reasoning will be needed after this action

Respond with a JSON object in this exact format:
{{
  "thinking": "Your step-by-step reasoning about what to do next",
  "tool_name": "exact_tool_name_or_null",
  "tool_args": {{"param": "value"}},
  "continue_reasoning": true/false,
  "final_response": "Complete answer if reasoning is done, otherwise null",
  "confidence": 0.8
}}

IMPORTANT:
- Use "null" for tool_name if no tool is needed
- Set continue_reasoning to false only when you have a complete answer
- If you use a tool, set continue_reasoning to true unless you're certain this will be the final step
- The final_response should only be provided when continue_reasoning is false"""

    async def _execute_selected_tool(
        self, 
        tool_name: str, 
        tool_args: Dict[str, Any], 
        tool_chain_context: ToolChainContext
    ) -> str:
        """
        Execute a tool selected by the consolidated reasoning process.
        
        Handles tool execution with enhanced error handling and context management.
        """
        if tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not available"
            self.logger.warning("Invalid tool requested", tool=tool_name)
            return error_msg
        
        try:
            # Handle special cases for tool arguments
            if tool_name == "read_file" and tool_args.get("filename") == "LATEST_FILE":
                # Resolve latest file from context or by listing files
                if tool_chain_context.discovered_files:
                    latest_file = tool_chain_context.discovered_files[-1]
                    tool_args["filename"] = latest_file
                    self.logger.info("Resolved LATEST_FILE from context", filename=latest_file)
                else:
                    # Get file list to find latest
                    list_result = self.tools["list_files"]()
                    if isinstance(list_result, list) and list_result:
                        latest_file = list_result[0]
                        tool_args["filename"] = latest_file
                        tool_chain_context.discovered_files.extend(list_result)
                    elif isinstance(list_result, str) and list_result.strip():
                        files = list_result.strip().split('\n')
                        if files and files[0]:
                            latest_file = files[0]
                            tool_args["filename"] = latest_file
                            tool_chain_context.discovered_files.extend(files)
                        else:
                            return "No files found in workspace"
                    else:
                        return "Could not list files to find latest"
            
            # Execute the tool
            tool_func = self.tools[tool_name]
            
            # Log tool usage for diagnostics
            log_tool_usage(tool_name, tool_args)
            
            # Handle both sync and async tools
            import asyncio
            import inspect
            
            if tool_args:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func(**tool_args)
                else:
                    result = tool_func(**tool_args)
            else:
                if inspect.iscoroutinefunction(tool_func):
                    result = await tool_func()
                else:
                    result = tool_func()
            
            # Update tool chain context based on tool type
            if tool_name in ["list_files", "list_all"]:
                if isinstance(result, list):
                    tool_chain_context.discovered_files.extend(result)
                elif isinstance(result, str):
                    files = [f.strip() for f in result.split('\n') if f.strip()]
                    tool_chain_context.discovered_files.extend(files)
            elif tool_name == "read_file" and "filename" in tool_args:
                # Cache file content for future reference
                tool_chain_context.cache_file_content(tool_args["filename"], str(result))
            
            return str(result)
            
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            self.logger.error("Tool execution failed", tool=tool_name, error=str(e))
            return error_msg
