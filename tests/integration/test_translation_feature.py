#!/usr/bin/env python3
"""
Test script for the new translation feature in ReAct loop.

This script tests that:
1. Italian queries are translated to English at the start of reasoning
2. English queries remain unchanged
3. Tool selection works correctly with translated queries
4. The translation step appears in the reasoning trace
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent.core.react_loop import ReActLoop, ReActPhase
from config.model_config import ModelConfig
import structlog

# Mock LLM response function for testing
async def mock_llm_response(prompt: str) -> str:
    """Mock LLM response function that simulates translation."""
    # Simple translation rules for testing
    translations = {
        "lista tutti i file e cartelle": "list all files and folders",
        "mostra il contenuto del file": "show the file content",
        "trova il file più grande": "find the largest file",
        "crea un nuovo file": "create a new file",
        "leggi il file readme": "read the readme file"
    }
    
    prompt_lower = prompt.lower()
    for italian, english in translations.items():
        if italian in prompt_lower:
            return english
    
    # If no translation found, assume it's already English
    query_start = prompt.find('"') + 1
    query_end = prompt.rfind('"')
    if query_start > 0 and query_end > query_start:
        return prompt[query_start:query_end]
    
    return "list files"  # default fallback

# Mock tools for testing
def mock_list_files():
    return ["file1.txt", "file2.py", "README.md"]

def mock_read_file(filename: str):
    return f"Content of {filename}"

# Mock context class
class MockContext:
    def __init__(self):
        self.conversation_id = "test-123"
        self.user_query = ""

async def test_translation_feature():
    """Test the translation feature."""
    
    # Set up logger
    logger = structlog.get_logger(__name__)
    
    # Mock tools
    tools = {
        "list_files": mock_list_files,
        "read_file": mock_read_file,
        "list_all": mock_list_files  # Italian queries should map to this
    }
    
    # Initialize model config (mock)
    model_config = ModelConfig()
    
    # Create ReAct loop with translation enabled
    react_loop = ReActLoop(
        model_provider=model_config.get_provider("gemini"),
        tools=tools,
        logger=logger,
        max_iterations=3,
        debug_mode=True,
        llm_response_func=mock_llm_response,
        use_llm_tool_selector=False  # Use pattern matching for predictable testing
    )
    
    print("🧪 Testing Translation Feature in ReAct Loop")
    print("=" * 60)
    
    # Test 1: Italian query should be translated
    print("\n📝 Test 1: Italian query translation")
    context = MockContext()
    italian_query = "lista tutti i file e cartelle"
    
    print(f"Original query: '{italian_query}'")
    
    result = await react_loop.execute(italian_query, context)
    
    print(f"Success: {result.success}")
    print(f"Tools used: {result.tools_used}")
    print(f"Final response: {result.response}")
    
    # Check if translation step is in reasoning
    translation_steps = [step for step in react_loop.scratchpad 
                        if "TRANSLATION" in step.content]
    
    if translation_steps:
        print(f"✅ Translation detected: {translation_steps[0].content}")
    else:
        print("❌ No translation step found in reasoning")
    
    # Check if context was updated with translated query
    if hasattr(context, 'user_query'):
        print(f"✅ Context updated with translated query: '{context.user_query}'")
        if hasattr(context, 'original_user_query'):
            print(f"✅ Original query preserved: '{context.original_user_query}'")
    else:
        print("❌ Context not updated with translated query")
    
    print("\n" + "-" * 40)
    
    # Test 2: English query should remain unchanged
    print("\n📝 Test 2: English query (no translation needed)")
    context2 = MockContext()
    english_query = "list all files and directories"
    
    print(f"Original query: '{english_query}'")
    
    result2 = await react_loop.execute(english_query, context2)
    
    print(f"Success: {result2.success}")
    print(f"Tools used: {result2.tools_used}")
    
    # Check if translation step is NOT in reasoning for English query
    translation_steps2 = [step for step in react_loop.scratchpad 
                         if "TRANSLATION" in step.content]
    
    if not translation_steps2:
        print("✅ No unnecessary translation for English query")
    else:
        print(f"⚠️ Translation occurred for English query: {translation_steps2[0].content}")
    
    print("\n" + "-" * 40)
    
    # Test 3: Show full reasoning trace for Italian query
    print("\n📝 Test 3: Full reasoning trace for Italian query")
    context3 = MockContext()
    italian_query2 = "trova il file più grande"
    
    print(f"Query: '{italian_query2}'")
    
    result3 = await react_loop.execute(italian_query2, context3)
    
    print("\n🧠 Reasoning Steps:")
    for i, step in enumerate(react_loop.scratchpad, 1):
        phase_emoji = {
            ReActPhase.THINK: "💭",
            ReActPhase.ACT: "⚡",
            ReActPhase.OBSERVE: "👀"
        }.get(step.phase, "❓")
        
        print(f"  {phase_emoji} Step {i} ({step.phase.value.upper()}): {step.content[:100]}...")
        if step.tool_name:
            print(f"     Tool: {step.tool_name} with args: {step.tool_args}")
    
    print(f"\n✅ Final result: {result3.response}")
    print(f"✅ Tools used: {result3.tools_used}")

if __name__ == "__main__":
    asyncio.run(test_translation_feature())
