"""
ReAct reasoning loop implementation.

This module implements the ReAct (Reasoning-Action-Observation) pattern for
autonomous agent reasoning. The loop enables the agent to think through problems
step by step, take actions with tools, and observe results to continue reasoning.

Enhanced with goal-oriented reasoning for better response alignment.
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
# Import goal compliance validator for response validation
from agent.core.goal_validator import GoalComplianceValidator, GoalComplianceResult
from agent.core.llm_tool_selector import LLMToolSelector, ToolSelectionResult


class ReActPhase(Enum):
    """Phases of the ReAct reasoning loop."""
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
    goal: Optional[str] = None  # Goal for this step if provided by LLM


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
    goal: Optional[str] = None  # The goal that was generated for this request
    goal_compliance: Optional[GoalComplianceResult] = None  # Compliance validation result


@dataclass
class ConsolidatedReActResponse:
    """
    Structured response from a single LLM call containing all ReAct phases.
    
    Enhanced with goal-oriented reasoning for better alignment between
    user requests and agent responses.
    """
    thinking: str
    goal: Optional[str] = None  # Explicit objective generated for the user request
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    continue_reasoning: bool = True
    final_response: Optional[str] = None
    goal_compliance_check: Optional[str] = None  # Verification that response achieves the goal
    clarification_question: Optional[str] = None  # Question to ask user when more info needed
    confidence: float = 0.8
    
    @classmethod
    def from_json_string(cls, json_str: str) -> 'ConsolidatedReActResponse':
        """Parse JSON response from LLM into structured format."""
        try:
            # Clean up common JSON formatting issues
            cleaned_json = json_str.strip()
            
            # Remove inline comments that might break JSON parsing
            lines = cleaned_json.split('\n')
            cleaned_lines = []
            for line in lines:
                # Remove lines that are just comments
                if line.strip().startswith('//'):
                    continue
                # Remove inline comments from JSON lines
                if '//' in line and ('"' in line or '{' in line or '}' in line):
                    comment_index = line.find('//')
                    # Check if the // is inside a string literal
                    string_count = line[:comment_index].count('"') - line[:comment_index].count('\\"')
                    if string_count % 2 == 0:  # Even number means we're outside strings
                        line = line[:comment_index].rstrip() + (',' if line[:comment_index].rstrip().endswith('"') else '')
                cleaned_lines.append(line)
            
            cleaned_json = '\n'.join(cleaned_lines)
            
            data = json.loads(cleaned_json)
            return cls(
                thinking=data.get("thinking", "No thinking provided"),
                goal=data.get("goal"),  # Extract goal from JSON response
                tool_name=data.get("tool_name"),
                tool_args=data.get("tool_args", {}),
                continue_reasoning=data.get("continue_reasoning", True),
                final_response=data.get("final_response"),
                goal_compliance_check=data.get("goal_compliance_check"),  # Extract compliance check
                clarification_question=data.get("clarification_question"),  # Extract clarification question
                confidence=data.get("confidence", 0.8)
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Try to extract useful information from malformed response
            thinking_text = "I need to analyze this request and determine the appropriate action."
            
            # Look for thinking content in the malformed JSON
            if "thinking" in json_str:
                import re
                thinking_match = re.search(r'"thinking":\s*"([^"]+)"', json_str)
                if thinking_match:
                    thinking_text = thinking_match.group(1)
            
            # Look for tool information
            tool_name = None
            if "tool_name" in json_str:
                tool_match = re.search(r'"tool_name":\s*"([^"]+)"', json_str)
                if tool_match:
                    tool_name = tool_match.group(1)
            
            # Look for goal information in malformed JSON
            goal = None
            if "goal" in json_str:
                goal_match = re.search(r'"goal":\s*"([^"]+)"', json_str)
                if goal_match:
                    goal = goal_match.group(1)
            
            # Look for goal compliance check
            goal_compliance_check = None
            if "goal_compliance_check" in json_str:
                compliance_match = re.search(r'"goal_compliance_check":\s*"([^"]+)"', json_str)
                if compliance_match:
                    goal_compliance_check = compliance_match.group(1)
            
            # Look for clarification question in malformed JSON
            clarification_question = None
            if "clarification_question" in json_str:
                clarification_match = re.search(r'"clarification_question":\s*"([^"]+)"', json_str)
                if clarification_match:
                    clarification_question = clarification_match.group(1)
            
            # Fallback to text parsing if JSON fails
            return cls(
                thinking=thinking_text,
                goal=goal,  # Include extracted goal
                tool_name=tool_name,
                tool_args={},
                continue_reasoning=bool(tool_name),  # Continue if we found a tool
                final_response=None,  # Don't provide a final response, let the system handle it properly
                goal_compliance_check=goal_compliance_check,  # Include compliance check
                clarification_question=clarification_question  # Include clarification question
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
        use_llm_tool_selector: bool = True  # Default to True for intelligent behavior
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
            use_llm_tool_selector: Whether to use LLM-based tool selection (recommended: True)
        """
        self.model_provider = model_provider
        self.tools = tools
        self.logger = logger or structlog.get_logger(__name__)
        self.max_iterations = max_iterations
        self.debug_mode = debug_mode
        self.llm_response_func = llm_response_func
        
        # Store the thinking tool for agentic reasoning
        self.thinking_tool = mcp_thinking_tool
        
        # Always try to enable LLM tool selector for intelligent behavior
        self.llm_tool_selector = None
        self.use_llm_tool_selector = False
        
        if mcp_thinking_tool:
            try:
                from agent.core.llm_tool_selector import LLMToolSelector
                self.llm_tool_selector = LLMToolSelector(mcp_thinking_tool)
                self.use_llm_tool_selector = True
                self.logger.info("✅ LLM-based intelligent tool selector enabled")
            except Exception as e:
                self.logger.warning(f"❌ Failed to initialize LLM tool selector: {e}")
                self.use_llm_tool_selector = False
        else:
            if use_llm_tool_selector:
                self.logger.warning("⚠️  LLM tool selector requested but no MCP thinking tool provided")
            self.use_llm_tool_selector = False
        
        if not self.use_llm_tool_selector:
            self.logger.info("Using simple contextual fallback for tool selection")
        
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
        
        Uses agentic reasoning with the sequential thinking tool instead of keyword matching
        to intelligently decide if an action is needed based on the current thought
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
            # Use agentic reasoning instead of keyword matching
            actions_taken = len([s for s in self.scratchpad if s.phase == ReActPhase.ACT])
            
            # If no actions taken yet, definitely need to take action
            if actions_taken == 0:
                return True
            
            # Use sequential thinking tool for intelligent decision making
            if hasattr(self, 'thinking_tool') and self.thinking_tool:
                try:
                    reasoning_result = await self.thinking_tool(
                        thought=f"""Analyze this thought to determine if I should take an action with a tool or provide a final response.

CURRENT THOUGHT: {thought}

CONTEXT: {context_summary}

AVAILABLE TOOLS: {', '.join(self.tools.keys())}

ACTIONS TAKEN SO FAR: {actions_taken}

Consider:
1. Does the thought indicate I need to gather more information?
2. Does the thought suggest I should use a specific tool?
3. Do I have enough information to provide a complete answer?
4. Is the user asking for something that requires tool usage?

Determine whether I should take an action (YES) or provide a final response (NO).""",
                        nextThoughtNeeded=False,
                        thoughtNumber=1,
                        totalThoughts=1
                    )
                    
                    # Parse the reasoning result to determine action
                    reasoning_text = reasoning_result.get('thought', '').lower()
                    return 'yes' in reasoning_text and 'no' not in reasoning_text.split('yes')[0]
                    
                except Exception as thinking_error:
                    self.logger.warning("Error using thinking tool for action decision", error=str(thinking_error))
                    # Fall back to heuristic analysis
            
            # Fallback: Analyze thought content semantically without keywords
            thought_lower = thought.lower()
            
            # Check for action indicators using semantic analysis
            action_indicators = [
                "need" in thought_lower and ("to" in thought_lower or "more" in thought_lower),
                "should" in thought_lower and any(word in thought_lower for word in ["use", "call", "check", "get"]),
                "let me" in thought_lower or "i'll" in thought_lower or "i will" in thought_lower,
                any(phrase in thought_lower for phrase in ["more information", "need to", "have to", "going to"]),
                # Semantic indicators that suggest action is needed
                "information" in thought_lower and "need" in thought_lower,
                "not enough" in thought_lower or "insufficient" in thought_lower,
                "missing" in thought_lower or "lacking" in thought_lower
            ]
            
            return any(action_indicators)
            
        except Exception as e:
            self.logger.warning("Error in action decision", error=str(e))
            # Default to taking action if uncertain
            return True
    
    async def _decide_tool_action(self, context: Any) -> Optional[Dict[str, Any]]:
        """
        Decide which tool to use based on current reasoning state.
        
        Uses pure LLM-based semantic reasoning to understand user intent
        and select the most appropriate tool. No keyword matching is used.
        """
        if not self.scratchpad:
            return None
        
        # Always prefer LLM-based tool selection for intelligent decisions
        if self.use_llm_tool_selector and self.llm_tool_selector:
            llm_result = await self._llm_based_tool_selection(context)
            if llm_result:
                self.logger.info(f"LLM selected tool: {llm_result['tool']}")
                return llm_result
            else:
                self.logger.warning("LLM tool selection failed - using simple contextual fallback")
                # Simple contextual fallback without any keyword matching
                return await self._simple_contextual_fallback(context)
        else:
            # If LLM selector is not available, use basic contextual logic
            self.logger.warning("LLM tool selector not available - using basic contextual selection")
            return await self._simple_contextual_fallback(context)
    
    async def _simple_contextual_fallback(self, context: Any) -> Optional[Dict[str, Any]]:
        """
        Simple contextual fallback when LLM tool selection fails.
        
        Uses basic contextual logic without any keyword matching.
        Relies on logical flow and previous actions to make reasonable decisions.
        """
        # Get current context
        user_query = getattr(context, 'user_query', '')
        actions_taken = [s for s in self.scratchpad if s.phase == ReActPhase.ACT]
        
        # If we have taken previous actions, try to continue logically
        if actions_taken:
            last_action = actions_taken[-1].tool_name
            last_result = actions_taken[-1].tool_result if hasattr(actions_taken[-1], 'tool_result') else ""
            
            # Logical continuation based on previous action
            if last_action == "list_files" and last_result:
                # If we just listed files, user might want to read one
                # Try to extract a filename from context
                filename = self._extract_filename_from_context(context, None)
                if filename:
                    return {"tool": "read_file", "args": {"filename": filename}}
            
            elif last_action == "find_largest_file" and last_result:
                # If we found the largest file, user might want to read it
                filename = self._extract_filename_from_result(last_result)
                if filename:
                    return {"tool": "read_file", "args": {"filename": filename}}
        
        # If no logical continuation, make a safe default choice
        # List all files and directories to give user comprehensive view
        return {"tool": "list_all", "args": {}}
    
    def _extract_filename_from_result(self, result: str) -> Optional[str]:
        """Extract filename from a tool result string."""
        if not result:
            return None
        
        # Look for common filename patterns in results
        import re
        patterns = [
            r'Largest file:\s*([^\s(]+)',
            r'File:\s*([^\s]+)',
            r'filename:\s*([^\s]+)',
            r'([^\s]+\.[a-zA-Z0-9]+)'  # Basic file extension pattern
        ]
        
        for pattern in patterns:
            match = re.search(pattern, result)
            if match:
                return match.group(1)
        
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
        """Build metadata about available tools by extracting from tool metadata."""
        tools_metadata = {}
        
        # Extract metadata from tools that have it attached
        for tool_name, tool_func in self.tools.items():
            if hasattr(tool_func, 'tool_metadata'):
                # Use the metadata that's attached to the tool function
                tools_metadata[tool_name] = tool_func.tool_metadata
            else:
                # Fallback for tools without metadata (should be rare)
                tools_metadata[tool_name] = {
                    "description": f"Tool: {tool_name}",
                    "parameters": {},
                    "examples": []
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
    
    def _generate_response_from_context(self, query: str, tool_chain_context: ToolChainContext) -> str:
        """
        Generate final response from accumulated context when max iterations reached.
        
        Args:
            query: Original user query
            tool_chain_context: Context from tool executions
            
        Returns:
            Formatted response based on available context
        """
        # Check if this is an analytical query that needs proper description
        is_describe_query = any(keyword in query.lower() for keyword in [
            'describe', 'descrivi', 'analyze', 'analizza', 'explain', 'what is'
        ])
        
        # Find the most recent successful tool result
        for step in reversed(self.scratchpad):
            if step.phase == ReActPhase.ACT and step.tool_result and "error" not in step.tool_result.lower():
                # For describe queries, provide analysis instead of raw content
                if is_describe_query and step.tool_name == "read_file":
                    filename = step.tool_args.get("filename", "the file")
                    content = step.tool_result
                    
                    # Generate a proper description of the file
                    if content and len(content) > 50:
                        # Count lines and estimate file type
                        lines = content.split('\n')
                        line_count = len(lines)
                        
                        # Try to determine file type and purpose from content
                        description = f"## Description of {filename}\n\n"
                        description += f"This is a Python file with {line_count} lines of code. "
                        
                        # Analyze content for key patterns
                        if "class " in content:
                            classes = [line.strip() for line in lines if line.strip().startswith("class ")]
                            if classes:
                                description += f"It defines {len(classes)} class(es): {', '.join(c.split(':')[0].replace('class ', '') for c in classes[:3])}. "
                        
                        if "def " in content:
                            import re
                            functions = re.findall(r'def (\w+)', content)
                            if functions:
                                description += f"It contains {len(functions)} function(s) including: {', '.join(functions[:5])}. "
                        
                        if "import " in content or "from " in content:
                            description += "It includes various imports for external libraries. "
                        
                        # Look for docstrings
                        if '"""' in content or "'''" in content:
                            description += "The file includes documentation strings. "
                        
                        # Look for specific patterns in secure_agent.py
                        if "secure_agent" in filename.lower():
                            description += "\n\nThis appears to be the main agent implementation file responsible for handling secure file operations and user interactions within the AI file system."
                        
                        description += f"\n\n**File Content Preview:**\n```python\n{content[:500]}{'...' if len(content) > 500 else ''}\n```"
                        
                        return description
                    else:
                        return f"The file {filename} appears to be empty or very small with content: {content}"
                
                # For non-describe queries, return the tool result as-is
                return step.tool_result
        
        # If no successful tool execution, check tool chain context
        context_summary = tool_chain_context.get_context_summary()
        if context_summary and context_summary != "No context available":
            return f"Based on my exploration of the workspace:\n\n{context_summary}"
        
        # Fallback: provide helpful message
        return "I wasn't able to complete your request successfully. Please try rephrasing your question or check if the files you're looking for exist."

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
        """Extract filename from thought or query text using simple pattern matching."""
        import re
        
        # Look for common filename patterns with file extensions
        filename_patterns = [
            r"([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)",  # General filename pattern
            r"'([^']+\.[a-zA-Z0-9]+)'",  # Quoted filename
            r'"([^"]+\.[a-zA-Z0-9]+)"'   # Double quoted filename
        ]
        
        text = f"{thought} {query}"
        
        for pattern in filename_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
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
                    
                    # Log successful parsing in debug mode
                    if self.debug_mode:
                        self.logger.debug("Successfully parsed LLM response", 
                                        thinking=parsed_response.thinking[:100] + "...",
                                        tool_name=parsed_response.tool_name)
                        
                except Exception as e:
                    self.logger.warning(f"Failed to get LLM response: {e}")
                    # Fallback to a safe default that will generate a helpful response
                    parsed_response = ConsolidatedReActResponse(
                        thinking="I need to help analyze this request. Let me start by examining the available information.",
                        tool_name="list_all",  # Default to listing files for project analysis
                        tool_args={},
                        continue_reasoning=True,
                        final_response=None
                    )
                
                # Record the thinking step with goal if provided
                thinking_step = ReActStep(
                    phase=ReActPhase.THINK,
                    step_number=len(self.scratchpad) + 1,
                    content=parsed_response.thinking,
                    goal=parsed_response.goal  # Include goal in the step
                )
                self.scratchpad.append(thinking_step)
                
                if self.debug_mode:
                    self.logger.debug("THINK phase", 
                                    content=parsed_response.thinking,
                                    goal=parsed_response.goal or "No goal provided",
                                    clarification_question=parsed_response.clarification_question or "No clarification needed")
                
                # Handle clarification requests - agent needs more information
                if parsed_response.clarification_question:
                    # Agent is asking for clarification - this should be the final response
                    clarification_response = self._format_clarification_response(
                        parsed_response.clarification_question,
                        parsed_response.goal,
                        original_query
                    )
                    final_response = clarification_response
                    break
                
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
                
                # Special logic for analytical queries after successful file read
                is_describe_query = any(keyword in translated_query.lower() for keyword in [
                    'describe', 'descrivi', 'analyze', 'analizza', 'explain', 'what is'
                ])
                
                if (is_describe_query and parsed_response.tool_name == "read_file" and 
                    tool_result and "error" not in tool_result.lower() and len(tool_result) > 50):
                    # We successfully read a file for a describe query - force completion
                    final_response = self._generate_response_from_context(translated_query, tool_chain_context)
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
            
            # Extract goal with priority: first from parsed_response, then from reasoning steps
            goal = None
            goal_compliance_check = None
            
            # Priority 1: Get goal from the current parsed response
            if 'parsed_response' in locals() and hasattr(parsed_response, 'goal') and parsed_response.goal:
                goal = parsed_response.goal
                goal_compliance_check = getattr(parsed_response, 'goal_compliance_check', None)
            else:
                # Priority 2: Extract goal from the most recent thinking step that had one
                for step in reversed(self.scratchpad):
                    if hasattr(step, 'goal') and step.goal:
                        goal = step.goal
                        break
                
                # If no goal found, generate a default goal based on the query
                if not goal:
                    default_goal = self._generate_default_goal(translated_query)
                    
                    # Handle special cases that indicate need for clarification
                    if default_goal in ["AMBIGUOUS_REQUEST", "NEEDS_FILE_SPECIFICATION"]:
                        # Generate clarification response
                        if default_goal == "AMBIGUOUS_REQUEST":
                            clarification = "Your request seems quite general. Could you please specify what you'd like me to do with the files in your workspace?"
                        elif default_goal == "NEEDS_FILE_SPECIFICATION":
                            clarification = "I understand you want to work with a file, but could you please specify which file you're referring to?"
                        
                        # Create clarification response
                        final_response = self._format_clarification_response(
                            clarification,
                            f"Help with: {translated_query}",
                            original_query
                        )
                        goal = f"Request clarification for: {translated_query}"
                    else:
                        goal = default_goal
            
            # Validate goal compliance if we have a goal
            goal_compliance = None
            if goal:
                goal_compliance = GoalComplianceValidator.validate_compliance(
                    goal=goal,
                    response=final_response,
                    tools_used=self._get_tools_used(),
                    context={
                        'original_query': original_query,
                        'translated_query': translated_query,
                        'iterations': self.iteration_count
                    }
                )
                
                # Log compliance result in debug mode
                if self.debug_mode:
                    self.logger.debug(
                        "Goal compliance validation",
                        goal=goal,
                        compliance_level=goal_compliance.compliance_level.value,
                        confidence_score=goal_compliance.confidence_score,
                        explanation=goal_compliance.explanation
                    )
            
            result = ReActResult(
                response=final_response,
                tools_used=self._get_tools_used(),
                reasoning_steps=self._format_reasoning_steps(),
                success=True,
                iterations=self.iteration_count,
                tool_chain_context=tool_chain_context,
                goal=goal,
                goal_compliance=goal_compliance
            )
            
            self.logger.info(
                "Consolidated ReAct loop completed successfully",
                conversation_id=getattr(context, 'conversation_id', 'unknown'),
                iterations=self.iteration_count,
                tools_used=result.tools_used,
                original_query=original_query,
                translated_query=translated_query,
                goal_achieved=goal,
                goal_compliance_level=goal_compliance.compliance_level.value if goal_compliance else "Not validated",
                clarification_requested="Yes" if "Clarification Needed" in final_response else "No"
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
        
        # Build tool descriptions from tool metadata
        tools_metadata = self._build_tools_metadata()
        
        available_tool_info = []
        for tool_name in available_tools:
            if tool_name in tools_metadata:
                tool_meta = tools_metadata[tool_name]
                description = tool_meta.get('description', f"Tool: {tool_name}")
                parameters = tool_meta.get('parameters', {})
                
                # Format parameters info if available
                if parameters:
                    param_info = f" (args: {', '.join(parameters.keys())})"
                else:
                    param_info = ""
                
                available_tool_info.append(f"- {tool_name}: {description}{param_info}")
            else:
                # Fallback for tools without metadata
                available_tool_info.append(f"- {tool_name}: Tool: {tool_name}")
        
        # Get context summary from tool chain
        context_summary = tool_chain_context.get_context_summary()
        
        # Detect if this is an analytical query that should conclude after gathering info
        is_analytical_query = any(keyword in query.lower() for keyword in [
            'analizza', 'analyze', 'summary', 'overview', 'describe', 'descrivi', 'what is', 
            'tell me about', 'explain', 'review', 'show me'
        ])
        
        # Count tool actions (actual work done)
        tool_actions = [s for s in reasoning_history if s.phase == ReActPhase.ACT and s.tool_result]
        
        analytical_guidance = ""
        if is_analytical_query:
            if len(tool_actions) >= 2:
                # For analytical queries, after 2 successful tool actions, we should have enough information
                analytical_guidance = f"""
ANALYSIS GUIDANCE: You've gathered substantial information ({len(tool_actions)} tool actions completed). 
For analytical queries like "describe", "analyze", or "explain", after successfully reading file content or gathering data,
you should provide a comprehensive summary as your final_response instead of continuing to gather more data.
Set continue_reasoning=false and provide final_response with your analysis when you have enough information.
"""
            elif len(tool_actions) >= 1:
                # After first successful tool action, encourage completion if sufficient
                last_action = tool_actions[-1]
                if "read_file" in last_action.tool_name and last_action.tool_result:
                    analytical_guidance = f"""
ANALYSIS GUIDANCE: You've successfully read file content. For "describe" queries, you now have the necessary 
information to provide a comprehensive description. Set continue_reasoning=false and provide a detailed 
final_response analyzing what you found in the file.
"""
        
        iteration_guidance = ""
        iteration_count = len([s for s in reasoning_history if s.phase == ReActPhase.ACT])
        if iteration_count >= 5:
            iteration_guidance = f"""
COMPLETION GUIDANCE: You've used {iteration_count} tools already. Consider summarizing your findings 
rather than using more tools. Set continue_reasoning=false and provide a comprehensive final_response.
"""
        
        return f"""You are an AI File System Agent using ReAct reasoning for secure, multilingual file operations.

AGENT CONTEXT:
You are part of a secure AI system that helps users manage files within a sandboxed workspace. You support both English and Italian queries and operate through a supervised architecture that ensures safety and security.

CRITICAL LANGUAGE RULES:
1. ALL INTERNAL THINKING AND REASONING MUST BE IN ENGLISH ONLY - this includes the "thinking" field in your JSON response
2. ONLY the final_response field should match the user's input language
3. Your "thinking" field must always be in clear, professional English regardless of the user's query language

CAPABILITIES:
- File operations within workspace boundaries (read, write, delete, list)
- Multilingual support (English/Italian) with automatic translation
- Project analysis and content examination
- Pattern-based file searching and metadata extraction
- AI-powered question answering about file contents

SECURITY CONSTRAINTS:
- Operations limited to assigned workspace only
- No path traversal or system file access
- All requests pre-screened by safety supervisor
- Transparent reasoning process with ReAct pattern

CURRENT REQUEST:
USER QUERY: {query}
WORKSPACE: {getattr(context, 'workspace_path', 'Unknown')}

PREVIOUS REASONING STEPS:
{previous_steps or "None - this is the first iteration"}

CONTEXT FROM TOOLS:
{context_summary}
COMMON CLARIFICATION SCENARIOS:
- User says "help" or "what can you do" → Ask what specific task they need help with
- User says "read file" without specifying which → Ask which file they want to read
- User says "delete something" → Ask which specific file to delete
- User request is too vague → Ask for more specific details
- Multiple files could match → Ask which specific file they mean

{analytical_guidance}
{iteration_guidance}

AVAILABLE TOOLS:
{chr(10).join(available_tool_info)}

INSTRUCTIONS:
1. **MANDATORY: GENERATE A CLEAR GOAL** - Always start by defining what you want to achieve for this user request
2. **ANALYZE AMBIGUITY** - If the request is unclear or ambiguous, generate a clarification question instead of proceeding
3. THINK through the problem step by step (ALWAYS IN ENGLISH ONLY)
4. DECIDE if you need to use a tool, ask for clarification, or can provide a final answer  
5. If using a tool, specify the exact tool name and arguments
6. Determine if more reasoning will be needed after this action
7. **MANDATORY: VALIDATE GOAL ACHIEVEMENT** - Before providing final_response, CHECK if your response achieves the stated goal
8. For analytical queries (describe, analyze, explain): after successfully reading file content, provide comprehensive final_response instead of continuing to gather more data

CRITICAL REQUIREMENTS:
- The "goal" field is MANDATORY - never leave it null or empty
- The "goal_compliance_check" field is MANDATORY when providing final_response
- Use "clarification_question" when the request is ambiguous, unclear, or missing critical information
- Use "null" for tool_name if no tool is needed
- Set continue_reasoning to false when you have enough information to provide a complete answer OR when asking for clarification
- For analytical queries (analyze, describe, overview), after reading file content, provide comprehensive description as final_response
- The final_response should synthesize all gathered information into a clear, helpful answer
- If you've successfully read a file for a "describe" query, provide the description immediately rather than continuing

RESPONSE FORMAT:
You must respond with valid JSON in exactly this structure:
{{
    "thinking": "Your step-by-step reasoning (ALWAYS IN ENGLISH)",
    "goal": "Clear statement of what you want to achieve",
    "tool_name": "exact_tool_name" or null,
    "tool_args": {{"parameter": "value"}} or {{}},
    "continue_reasoning": true or false,
    "final_response": "Complete answer for user" or null,
    "goal_compliance_check": "How this response achieves the goal" or null,
    "clarification_question": "Question to ask user for more info" or null,
    "confidence": 0.8
}}"""

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
    
    def _generate_default_goal(self, query: str) -> str:
        """
        Generate a default goal using semantic analysis instead of keyword matching.
        
        This follows the single responsibility principle by having one clear purpose:
        generate meaningful goals for common query patterns using semantic understanding.
        
        Args:
            query: The user's translated query
            
        Returns:
            A clear, actionable goal for the request, or a flag for ambiguous requests
        """
        query_lower = query.lower()
        
        # Use semantic analysis instead of keyword matching
        # Check for ambiguous or vague requests using semantic indicators
        if len(query_lower.split()) <= 3:
            simple_words = ['help', 'what', 'how', 'can', 'you', 'do', 'something', 'anything']
            word_count = sum(1 for word in simple_words if word in query_lower)
            if word_count >= 2:
                return "AMBIGUOUS_REQUEST"  # Special flag to trigger clarification
        
        # Semantic analysis for different intent categories
        # File listing intent
        listing_indicators = {
            'list_action': any(word in query_lower for word in ['list', 'show', 'display', 'see', 'visualizza', 'mostra', 'elenca']),
            'tree_format': any(word in query_lower for word in ['tree', 'structure', 'hierarchy', 'albero']),
            'files_focus': any(word in query_lower for word in ['files', 'file', 'documento']),
            'dirs_focus': any(word in query_lower for word in ['directories', 'folders', 'directory', 'folder', 'cartelle']),
            'all_content': any(word in query_lower for word in ['all', 'tutto', 'tutti', 'everything'])
        }
        
        if listing_indicators['list_action']:
            if listing_indicators['tree_format']:
                return "Display workspace file and directory structure in tree format"
            elif listing_indicators['files_focus'] and not listing_indicators['dirs_focus']:
                return "List all files in the workspace"
            elif listing_indicators['dirs_focus'] and not listing_indicators['files_focus']:
                return "List all directories in the workspace"
            elif listing_indicators['all_content'] or (listing_indicators['files_focus'] and listing_indicators['dirs_focus']):
                return "List and display workspace contents"
            else:
                return "List and display workspace contents"
        
        # File reading/analysis intent
        reading_indicators = {
            'read_action': any(word in query_lower for word in ['read', 'describe', 'analyze', 'explain', 'leggi', 'descrivi']),
            'content_inquiry': any(phrase in query_lower for phrase in ['what is', 'what does', 'content of', 'contenuto di']),
            'file_extension': any(ext in query_lower for ext in ['.py', '.txt', '.md', '.json', '.yaml', '.yml', '.js', '.ts'])
        }
        
        if reading_indicators['read_action'] or reading_indicators['content_inquiry']:
            if reading_indicators['file_extension']:
                return "Read and analyze the specified file content"
            else:
                return "NEEDS_FILE_SPECIFICATION"  # Special flag for missing file info
        
        # File manipulation intent
        creation_indicators = {
            'create_action': any(word in query_lower for word in ['write', 'create', 'scrivi', 'crea']),
            'file_context': 'file' in query_lower or reading_indicators['file_extension']
        }
        
        if creation_indicators['create_action']:
            if creation_indicators['file_context']:
                return "Create or write content to a file"
            else:
                return "NEEDS_FILE_SPECIFICATION"
        
        deletion_indicators = {
            'delete_action': any(word in query_lower for word in ['delete', 'remove', 'elimina', 'rimuovi']),
            'file_context': reading_indicators['file_extension'] or 'file' in query_lower
        }
        
        if deletion_indicators['delete_action']:
            if deletion_indicators['file_context']:
                return "Delete the specified file"
            else:
                return "NEEDS_FILE_SPECIFICATION"
        
        # Search intent
        search_indicators = any(word in query_lower for word in ['find', 'search', 'trova', 'cerca'])
        if search_indicators:
            return "Find and locate files matching the specified criteria"
        
        # General fallback goal
        if len(query.strip()) < 5:  # Very short queries are likely ambiguous
            return "AMBIGUOUS_REQUEST"
        return f"Fulfill user request: {query[:50]}..." if len(query) > 50 else f"Fulfill user request: {query}"
    
    def _format_clarification_response(
        self, 
        clarification_question: str, 
        goal: Optional[str], 
        original_query: str
    ) -> str:
        """
        Format a clarification request for the user.
        
        This follows the single responsibility principle by having one clear purpose:
        format user-friendly clarification requests when agent needs more information.
        
        Args:
            clarification_question: The question to ask the user
            goal: The tentative goal if one was generated
            original_query: The user's original query
            
        Returns:
            Formatted clarification response for the user
        """
        # Start with the clarification question
        response = f"❓ **Clarification Needed**\n\n{clarification_question}\n\n"
        
        # Add context about what we understood
        if goal:
            response += f"💡 **What I understand so far:**\nI'm trying to: {goal}\n\n"
        
        # Add the original query for reference
        response += f"📝 **Your original request:** \"{original_query}\"\n\n"
        
        # Add helpful suggestions
        response += "💬 **Please provide more details so I can help you better.**"
        
        return response
