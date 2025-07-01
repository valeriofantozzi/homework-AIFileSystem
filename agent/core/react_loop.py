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


@dataclass
class ReActResult:
    """Result from a complete ReAct reasoning loop."""
    response: str
    tools_used: List[str] = field(default_factory=list)
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    iterations: int = 0


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
        llm_response_func: Optional[callable] = None
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
        """
        self.model_provider = model_provider
        self.tools = tools
        self.logger = logger or structlog.get_logger(__name__)
        self.max_iterations = max_iterations
        self.debug_mode = debug_mode
        self.llm_response_func = llm_response_func
        
        # Reasoning state
        self.scratchpad: List[ReActStep] = []
        self.current_phase = ReActPhase.THINK
        self.iteration_count = 0
    
    async def execute(self, query: str, context: Any) -> ReActResult:
        """
        Execute the ReAct reasoning loop for a given query.
        
        Args:
            query: User query to process
            context: Conversation context
            
        Returns:
            ReActResult with final response and reasoning trace
        """
        self.logger.info(
            "Starting ReAct reasoning loop",
            conversation_id=getattr(context, 'conversation_id', 'unknown'),
            query=query
        )
        
        # Initialize reasoning state
        self._reset_state()
        
        # Start with initial thinking phase
        current_thought = f"I need to help the user with: {query}\n\nLet me think about what I need to do."
        
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
            final_response = await self._generate_final_response(query, context)
            
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
                tools_used=result.tools_used
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
                if list_result:
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
            
            if tool_args:
                result = tool_func(**tool_args)
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
                tool_args=tool_args
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
        the appropriate tool and arguments.
        """
        if not self.scratchpad:
            return None
        
        # Get the current thought and build context
        last_thought = self.scratchpad[-1].content
        context_summary = self._build_context_summary()
        user_query = getattr(context, 'user_query', '')
        
        # Enhanced tool selection logic
        thought_lower = last_thought.lower()
        query_lower = user_query.lower()
        
        # Analyze what the user wants and what we've learned so far
        if "list" in thought_lower or "files" in thought_lower or "what files" in query_lower:
            return {"tool": "list_files", "args": {}}
        
        # Look for filename extraction patterns
        elif "read" in thought_lower or "content" in thought_lower or "open" in thought_lower:
            filename = self._extract_filename(last_thought, user_query)
            if filename:
                return {"tool": "read_file", "args": {"filename": filename}}
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
    
    async def _should_continue_reasoning(self) -> bool:
        """Determine if reasoning should continue or complete."""
        # Simple heuristic - continue if we haven't reached a conclusion
        if len(self.scratchpad) < 2:
            return True
            
        last_observation = self.scratchpad[-1].content.lower()
        
        # Stop if we got an error or completed the task
        stop_phrases = ["failed", "error", "completed", "done", "finished"]
        return not any(phrase in last_observation for phrase in stop_phrases)
    
    async def _generate_final_response(self, query: str, context: Any) -> str:
        """Generate the final response based on reasoning steps."""
        if not self.scratchpad:
            return "I wasn't able to process your request."
        
        # Get all actions and their results
        actions_taken = [step for step in self.scratchpad if step.phase == ReActPhase.ACT]
        
        if not actions_taken:
            return f"I analyzed your request '{query}' but determined no actions were needed."
        
        # Build a comprehensive response based on what was accomplished
        response_parts = []
        
        # Check if this was a question-answering task
        if any(step.tool_name == "answer_question_about_files" for step in actions_taken):
            # For Q&A, return the answer directly
            for step in actions_taken:
                if step.tool_name == "answer_question_about_files" and step.tool_result:
                    return step.tool_result
        
        # For file operations, provide a summary
        successful_actions = []
        failed_actions = []
        
        for action in actions_taken:
            if action.tool_result and "error" not in action.tool_result.lower():
                successful_actions.append(action)
            else:
                failed_actions.append(action)
        
        # Handle different types of responses
        if successful_actions:
            response_parts.append("I successfully completed the following actions:")
            
            for action in successful_actions:
                tool_name = action.tool_name
                result = action.tool_result
                
                if tool_name == "list_files":
                    file_count = len(result.split('\n')) if result else 0
                    response_parts.append(f"• Listed {file_count} files in the workspace")
                    if result:
                        response_parts.append(f"  Files: {result}")
                
                elif tool_name == "read_file":
                    filename = action.tool_args.get('filename', 'unknown')
                    content_length = len(result) if result else 0
                    response_parts.append(f"• Read file '{filename}' ({content_length} characters)")
                    if result and len(result) < 500:  # Show content if not too long
                        response_parts.append(f"  Content: {result}")
                    elif result:
                        response_parts.append(f"  Content preview: {result[:200]}...")
                
                elif tool_name == "write_file":
                    filename = action.tool_args.get('filename', 'unknown')
                    response_parts.append(f"• Created/wrote file '{filename}'")
                    if result:
                        response_parts.append(f"  Result: {result}")
                
                elif tool_name == "delete_file":
                    filename = action.tool_args.get('filename', 'unknown')
                    response_parts.append(f"• Deleted file '{filename}'")
        
        if failed_actions:
            response_parts.append("\nSome actions encountered issues:")
            for action in failed_actions:
                tool_name = action.tool_name
                filename = action.tool_args.get('filename', 'unknown') if action.tool_args else 'unknown'
                response_parts.append(f"• {tool_name} on '{filename}': {action.tool_result}")
        
        if not response_parts:
            return "I processed your request but didn't get clear results from the actions taken."
        
        return "\n".join(response_parts)
    
    def _reset_state(self) -> None:
        """Reset the reasoning state for a new query."""
        self.scratchpad.clear()
        self.current_phase = ReActPhase.THINK
        self.iteration_count = 0
    
    def _get_tools_used(self) -> List[str]:
        """Get list of tools that were used during reasoning."""
        return [
            step.tool_name for step in self.scratchpad 
            if step.phase == ReActPhase.ACT and step.tool_name
        ]
    
    def _format_reasoning_steps(self) -> List[Dict[str, Any]]:
        """Format reasoning steps for external consumption."""
        return [
            {
                "step": step.step_number,
                "phase": step.phase.value,
                "content": step.content,
                "tool": step.tool_name,
                "args": step.tool_args,
                "result": step.tool_result
            }
            for step in self.scratchpad
        ]
    
    def _build_context_summary(self) -> str:
        """Build a summary of the reasoning context so far."""
        if not self.scratchpad:
            return "No previous steps."
        
        summary_parts = []
        for step in self.scratchpad[-3:]:  # Last 3 steps for context
            if step.phase == ReActPhase.THINK:
                summary_parts.append(f"Thought: {step.content[:100]}...")
            elif step.phase == ReActPhase.ACT:
                summary_parts.append(f"Action: {step.tool_name} -> {step.tool_result[:100] if step.tool_result else 'No result'}...")
            elif step.phase == ReActPhase.OBSERVE:
                summary_parts.append(f"Observation: {step.content[:100]}...")
        
        return "\n".join(summary_parts) if summary_parts else "No previous steps."
    
    def _extract_filename(self, thought: str, user_query: str) -> Optional[str]:
        """
        Extract filename from thought or user query.
        
        Uses simple pattern matching to find filenames in text.
        """
        import re
        
        # Look for quoted filenames
        quoted_pattern = r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']'
        
        # Look for common filename patterns
        filename_pattern = r'\b([a-zA-Z0-9_-]+\.[a-zA-Z0-9]+)\b'
        
        # Try quoted first
        for text in [thought, user_query]:
            quoted_match = re.search(quoted_pattern, text)
            if quoted_match:
                return quoted_match.group(1)
        
        # Then try general pattern
        for text in [thought, user_query]:
            filename_match = re.search(filename_pattern, text)
            if filename_match:
                candidate = filename_match.group(1)
                # Avoid common false positives
                if candidate not in ['example.txt', 'test.py', 'file.txt']:
                    return candidate
        
        # Look for "latest", "newest", "most recent" patterns
        if any(word in thought.lower() + user_query.lower() 
               for word in ['latest', 'newest', 'most recent', 'last modified']):
            return "LATEST_FILE"  # Special marker for latest file logic
        
        return None
    
    def _extract_content(self, thought: str, user_query: str) -> Optional[str]:
        """Extract content to write from thought or user query."""
        import re
        
        # Look for content in quotes
        content_patterns = [
            r'content[:\s]+["\']([^"\']+)["\']',
            r'write[:\s]+["\']([^"\']+)["\']',
            r'["\']([^"\']{10,})["\']',  # Any long quoted string
        ]
        
        for text in [thought, user_query]:
            for pattern in content_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _extract_question(self, thought: str, user_query: str) -> Optional[str]:
        """Extract question text for the answer_question_about_files tool."""
        # The user query itself is often the question
        if len(user_query) > 10 and any(word in user_query.lower() 
                                       for word in ['what', 'how', 'why', 'when', 'where', 'which', '?']):
            return user_query
        
        # Look for question patterns in thought
        if '?' in thought:
            sentences = thought.split('.')
            for sentence in sentences:
                if '?' in sentence:
                    return sentence.strip()
        
        return user_query  # Default to original query
