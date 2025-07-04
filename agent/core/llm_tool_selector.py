"""
LLM-based tool selector for intelligent tool selection in the ReAct loop.

This module provides an LLM-driven approach to tool selection that replaces
simple pattern matching with semantic understanding and reasoning.
"""

import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ToolSelectionResult:
    """Result of tool selection analysis."""
    selected_tool: str
    confidence: float
    reasoning: str
    alternative_tools: List[str]
    requires_parameters: bool
    suggested_parameters: Dict[str, Any]


class LLMToolSelector:
    """
    Intelligent tool selector using LLM reasoning for semantic tool selection.
    
    This class replaces simple keyword/pattern matching with LLM-based reasoning
    to select the most appropriate tool for a given user query. It supports
    multilingual queries and can handle complex, ambiguous requests.
    """
    
    def __init__(self, mcp_thinking_tool: Callable):
        """
        Initialize the LLM tool selector.
        
        Args:
            mcp_thinking_tool: The MCP sequential thinking tool function
        """
        self.mcp_thinking_tool = mcp_thinking_tool
        
    async def select_tool(self, 
                   user_query: str, 
                   available_tools: Dict[str, Dict[str, Any]], 
                   context: Optional[Dict[str, Any]] = None) -> ToolSelectionResult:
        """
        Select the most appropriate tool for the given user query.
        
        Args:
            user_query: The user's request/query
            available_tools: Dictionary of available tools with their descriptions
            context: Optional context information (current directory, previous actions, etc.)
            
        Returns:
            ToolSelectionResult with the selected tool and reasoning
        """
        logger.info(f"Selecting tool for query: {user_query}")
        
        try:
            # Prepare the analysis prompt for the MCP thinking tool
            analysis_prompt = self._build_analysis_prompt(user_query, available_tools, context)
            
            # Use MCP sequential thinking to analyze and select the best tool
            reasoning_result = await self._reason_about_tool_selection(analysis_prompt)
            
            # Parse the reasoning result and extract tool selection
            selection_result = self._parse_reasoning_result(reasoning_result, available_tools)
            
            logger.info(f"Selected tool: {selection_result.selected_tool} (confidence: {selection_result.confidence})")
            return selection_result
            
        except Exception as e:
            logger.error(f"Error in LLM tool selection: {e}")
            # Fallback to a safe default or raise for handling upstream
            return ToolSelectionResult(
                selected_tool="help",
                confidence=0.1,
                reasoning=f"Error in tool selection: {e}. Falling back to help.",
                alternative_tools=[],
                requires_parameters=False,
                suggested_parameters={}
            )
    
    def _build_analysis_prompt(self, 
                              user_query: str, 
                              available_tools: Dict[str, Dict[str, Any]], 
                              context: Optional[Dict[str, Any]]) -> str:
        """Build the analysis prompt for the MCP thinking tool."""
        
        # Format available tools information
        tools_info = self._format_tools_info(available_tools)
        
        # Format context information
        context_info = self._format_context_info(context) if context else "No additional context available."
        
        prompt = f"""
You are an intelligent tool selector for a file system agent. Your task is to analyze a user query and select the most appropriate tool from the available options.

CRITICAL LANGUAGE RULE: ALL of your thinking, reasoning, and analysis must be in ENGLISH ONLY. Do not use Italian or any other language in your internal reasoning process.

USER QUERY: "{user_query}"

AVAILABLE TOOLS:
{tools_info}

CONTEXT:
{context_info}

TASK:
1. Analyze the user's intent from their query (consider both English and Italian)
2. Evaluate each available tool's suitability for this intent  
3. Consider the context and any special requirements
4. Select the BEST tool for this specific query
5. Provide confidence level (0.0-1.0) and clear reasoning (IN ENGLISH ONLY)

SPECIAL CONSIDERATIONS:
- "lista tutti i files e directory" = list all files AND directories (use "list_all")
- "list directories" or "lista directory" = list only directories (use "list_directories")  
- "list files" or "lista files" = list only files (use "list_files")
- Consider multilingual queries (English/Italian)
- Handle ambiguous requests by selecting the most comprehensive appropriate tool
- If the user wants both files and directories, prefer "list_all"

IMPORTANT: Think and reason in English only. Your analysis and reasoning must be in English regardless of the user's query language.

Please think through this step by step and provide your final recommendation.
"""
        return prompt
    
    def _format_tools_info(self, available_tools: Dict[str, Dict[str, Any]]) -> str:
        """Format available tools information for the prompt."""
        tools_list = []
        for tool_name, tool_info in available_tools.items():
            description = tool_info.get('description', 'No description available')
            parameters = tool_info.get('parameters', {})
            
            tool_entry = f"""
- {tool_name}: {description}
  Parameters: {list(parameters.keys()) if parameters else 'None'}"""
            tools_list.append(tool_entry)
        
        return "\n".join(tools_list)
    
    def _format_context_info(self, context: Dict[str, Any]) -> str:
        """Format context information for the prompt."""
        context_parts = []
        
        if 'current_directory' in context:
            context_parts.append(f"Current directory: {context['current_directory']}")
        
        if 'previous_action' in context:
            context_parts.append(f"Previous action: {context['previous_action']}")
        
        if 'user_language' in context:
            context_parts.append(f"User language: {context['user_language']}")
            
        return "\n".join(context_parts) if context_parts else "No specific context."
    
    async def _reason_about_tool_selection(self, analysis_prompt: str) -> str:
        """Use MCP sequential thinking to reason about tool selection."""
        try:
            # Use the MCP thinking tool to analyze the query and select the best tool
            # We'll do a multi-step reasoning process to carefully analyze the request
            result = await self.mcp_thinking_tool(
                thought=analysis_prompt,
                nextThoughtNeeded=True,
                thoughtNumber=1,
                totalThoughts=3
            )
            
            # Continue the reasoning process to get a thorough analysis
            reasoning_steps = [result]
            
            # Step 2: Analyze intent and requirements
            step2_result = await self.mcp_thinking_tool(
                thought="Based on the user query and available tools, what is the specific intent and what are the requirements? What tool would best serve this intent?",
                nextThoughtNeeded=True,
                thoughtNumber=2,
                totalThoughts=3
            )
            reasoning_steps.append(step2_result)
            
            # Step 3: Final decision with confidence
            step3_result = await self.mcp_thinking_tool(
                thought="Now I'll make my final tool selection decision with confidence level and reasoning. What is the BEST tool for this query and why?",
                nextThoughtNeeded=False,
                thoughtNumber=3,
                totalThoughts=3
            )
            reasoning_steps.append(step3_result)
            
            # Combine all reasoning steps
            full_reasoning = ""
            for i, step in enumerate(reasoning_steps, 1):
                if isinstance(step, dict):
                    step_content = step.get('thought', str(step))
                else:
                    step_content = str(step)
                full_reasoning += f"Step {i}: {step_content}\n\n"
            
            return full_reasoning
                
        except Exception as e:
            logger.error(f"Error in MCP thinking tool: {e}")
            raise
    
    def _parse_reasoning_result(self, 
                               reasoning_result: str, 
                               available_tools: Dict[str, Dict[str, Any]]) -> ToolSelectionResult:
        """Parse the reasoning result and extract tool selection."""
        
        reasoning_lower = reasoning_result.lower()
        
        # Extract tool selection from reasoning with improved logic
        selected_tool = None
        confidence = 0.5
        alternative_tools = []
        
        # Look for explicit tool selection patterns first
        tool_selection_patterns = [
            r"'([a-zA-Z_]+)'\s+tool",  # 'list_all' tool
            r"\"([a-zA-Z_]+)\"\s+tool", # "list_all" tool
            r"use\s+['\"]*([a-zA-Z_]+)['\"]*",  # use list_all
            r"tool\s+['\"]*([a-zA-Z_]+)['\"]*",  # tool list_all
            r"select\s+['\"]*([a-zA-Z_]+)['\"]*",  # select list_all
            r"recommend\s+['\"]*([a-zA-Z_]+)['\"]*",  # recommend list_all
            r"choose\s+['\"]*([a-zA-Z_]+)['\"]*"  # choose list_all
        ]
        
        import re
        for pattern in tool_selection_patterns:
            match = re.search(pattern, reasoning_lower)
            if match:
                potential_tool = match.group(1)
                if potential_tool in available_tools:
                    selected_tool = potential_tool
                    break
        
        # If no explicit pattern found, score tools by context and mentions
        if not selected_tool:
            tool_scores = {}
            for tool_name in available_tools.keys():
                score = 0
                tool_lower = tool_name.lower()
                
                # Direct mentions
                mentions = reasoning_lower.count(tool_lower)
                score += mentions * 3
                
                # Positive context patterns
                positive_patterns = [
                    f"{tool_lower} is the",
                    f"{tool_lower} would",
                    f"{tool_lower} should",
                    f"{tool_lower} best",
                    f"{tool_lower} perfect",
                    f"use {tool_lower}",
                    f"select {tool_lower}",
                    f"choose {tool_lower}"
                ]
                
                for pattern in positive_patterns:
                    if pattern in reasoning_lower:
                        score += 2
                
                tool_scores[tool_name] = score
            
            # Select tool with highest score
            if tool_scores:
                selected_tool = max(tool_scores, key=tool_scores.get)
                if tool_scores[selected_tool] == 0:
                    selected_tool = None  # No clear winner
        
        # If still no tool selected, use safe default
        if not selected_tool:
            selected_tool = "help"
        
        # Determine confidence based on certainty indicators
        confidence_indicators = {
            'high': ["clearly", "definitely", "obvious", "certain", "best choice", "perfect", "exactly"],
            'medium': ["probably", "likely", "seems", "appears", "good choice", "suitable"],
            'low': ["might", "could", "perhaps", "possibly", "maybe", "uncertain"]
        }
        
        confidence = 0.6  # default
        for level, indicators in confidence_indicators.items():
            if any(indicator in reasoning_lower for indicator in indicators):
                if level == 'high':
                    confidence = 0.9
                elif level == 'medium':
                    confidence = 0.7
                else:  # low
                    confidence = 0.4
                break
        
        # Extract alternative tools mentioned
        for tool_name in available_tools.keys():
            if (tool_name != selected_tool and 
                tool_name.lower() in reasoning_lower and
                len(alternative_tools) < 3):  # limit alternatives
                alternative_tools.append(tool_name)
        
        # Determine if parameters are required
        requires_params = bool(available_tools.get(selected_tool, {}).get('parameters'))
        
        # Extract suggested parameters from reasoning if any
        suggested_parameters = {}
        if requires_params:
            suggested_parameters = self._extract_parameters_from_reasoning(
                reasoning_result, selected_tool, available_tools.get(selected_tool, {})
            )
        
        return ToolSelectionResult(
            selected_tool=selected_tool,
            confidence=confidence,
            reasoning=reasoning_result,
            alternative_tools=alternative_tools,
            requires_parameters=requires_params,
            suggested_parameters=suggested_parameters
        )
    
    def _extract_parameters_from_reasoning(self, 
                                          reasoning: str, 
                                          tool_name: str, 
                                          tool_info: Dict[str, Any]) -> Dict[str, Any]:
        """Extract suggested parameters from reasoning text."""
        parameters = {}
        reasoning_lower = reasoning.lower()
        
        # Get parameter definitions
        tool_params = tool_info.get('parameters', {})
        
        # Look for filename patterns
        if 'filename' in tool_params:
            import re
            filename_patterns = [
                r"filename[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)",
                r"file[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)",
                r"read[:\s]+([^\s,\.]+\.[a-zA-Z0-9]+)"
            ]
            
            for pattern in filename_patterns:
                match = re.search(pattern, reasoning_lower)
                if match:
                    parameters['filename'] = match.group(1)
                    break
        
        # Look for pattern parameters
        if 'pattern' in tool_params:
            import re
            pattern_matches = re.findall(r"pattern[:\s]+[\"']([^\"']+)[\"']", reasoning_lower)
            if pattern_matches:
                parameters['pattern'] = pattern_matches[0]
        
        return parameters
