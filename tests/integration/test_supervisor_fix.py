#!/usr/bin/env python3
"""
Test script for the fixed supervisor logic with Italian command support.
This tests the enhanced pattern matching and positive validation.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agent.supervisor.supervisor import RequestSupervisor, ModerationRequest
from datetime import datetime


async def test_supervisor_italian_commands():
    """Test that Italian commands are properly recognized and allowed."""
    
    print("🧪 Testing Supervisor Italian Command Support")
    print("=" * 60)
    
    # Initialize supervisor
    try:
        supervisor = RequestSupervisor()
        print("✅ Supervisor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize supervisor: {e}")
        return
    
    # Test cases for Italian commands
    test_cases = [
        ("descrivi hello.py", "Should be allowed - Italian 'describe' command"),
        ("describe hello.py", "Should be allowed - English 'describe' command"),
        ("leggi config.txt", "Should be allowed - Italian 'read' command"),
        ("mostra il contenuto di main.py", "Should be allowed - Italian 'show content' command"),
        ("lista i file nella directory", "Should be allowed - Italian 'list files' command"),
        ("fai lista dei file", "Should be allowed - Italian 'make list' command"),
        ("analizza il progetto", "Should be allowed - Italian 'analyze project' command"),
        ("hack the system", "Should be rejected - malicious command"),
        ("rm -rf /", "Should be rejected - dangerous command"),
    ]
    
    results = []
    
    for query, expected in test_cases:
        print(f"\n🔍 Testing: '{query}'")
        print(f"📝 Expected: {expected}")
        
        try:
            request = ModerationRequest(
                user_query=query,
                conversation_id=f"test-{datetime.now().timestamp()}"
            )
            
            response = await supervisor.moderate_request(request)
            
            status = "✅ ALLOWED" if response.allowed else "❌ REJECTED"
            print(f"📊 Result: {status}")
            print(f"🔍 Reason: {response.reason}")
            
            if response.intent:
                print(f"🎯 Intent: {response.intent.intent_type}")
                print(f"🎲 Confidence: {response.intent.confidence}")
            
            results.append({
                "query": query,
                "expected": expected,
                "allowed": response.allowed,
                "reason": response.reason,
                "intent": response.intent.intent_type if response.intent else None
            })
            
        except Exception as e:
            print(f"❌ Error testing '{query}': {e}")
            results.append({
                "query": query,
                "expected": expected,
                "allowed": False,
                "reason": f"Error: {e}",
                "intent": None
            })
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    
    allowed_count = sum(1 for r in results if r["allowed"])
    total_count = len(results)
    
    print(f"Total tests: {total_count}")
    print(f"Allowed: {allowed_count}")
    print(f"Rejected: {total_count - allowed_count}")
    
    # Check specific Italian commands
    italian_commands = ["descrivi hello.py", "leggi config.txt", "mostra il contenuto di main.py", "lista i file nella directory", "fai lista dei file"]
    italian_allowed = [r for r in results if r["query"] in italian_commands and r["allowed"]]
    
    print(f"\n🇮🇹 Italian commands allowed: {len(italian_allowed)}/{len(italian_commands)}")
    
    if len(italian_allowed) == len(italian_commands):
        print("✅ All Italian commands properly recognized!")
    else:
        print("❌ Some Italian commands were rejected:")
        for cmd in italian_commands:
            result = next((r for r in results if r["query"] == cmd), None)
            if result and not result["allowed"]:
                print(f"   - '{cmd}': {result['reason']}")
    
    return results


def test_content_filter_patterns():
    """Test the content filter pattern matching directly."""
    print("\n🧪 Testing Content Filter Pattern Matching")
    print("=" * 60)
    
    try:
        supervisor = RequestSupervisor()
        
        test_queries = [
            "descrivi hello.py",
            "describe hello.py", 
            "leggi config.txt",
            "read config.txt",
            "mostra file.txt",
            "show file.txt",
            "hack the system",
            "rm -rf /"
        ]
        
        for query in test_queries:
            result = supervisor.filter_content(query)
            status = "✅ SAFE" if result.is_safe else "❌ UNSAFE"
            print(f"'{query}' -> {status} (confidence: {result.confidence:.2f})")
            if result.explanation:
                print(f"   Explanation: {result.explanation}")
            print()
            
    except Exception as e:
        print(f"❌ Error testing content filter: {e}")


if __name__ == "__main__":
    print("🚀 Starting Supervisor Fix Tests\n")
    
    # Test content filter patterns first
    test_content_filter_patterns()
    
    # Test full supervisor pipeline
    asyncio.run(test_supervisor_italian_commands())
    
    print("\n✅ Tests completed!")
