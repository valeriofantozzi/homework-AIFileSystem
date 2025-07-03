#!/usr/bin/env python3
"""
Debug script to test supervisor Italian language support directly.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_supervisor_italian():
    """Test supervisor with Italian commands directly."""
    print("🔍 Testing Supervisor Italian Language Support")
    print("=" * 50)
    
    try:
        from agent.supervisor.supervisor import RequestSupervisor, ModerationRequest
        
        # Initialize supervisor
        supervisor = RequestSupervisor()
        print(f"✅ Supervisor initialized")
        
        # Test queries
        test_queries = [
            "descrivi hello.py",
            "leggi config.txt", 
            "mostra contenuto di test.py",
            "read hello.py",  # English control
            "describe hello.py"  # English control
        ]
        
        for query in test_queries:
            print(f"\n📋 Testing: '{query}'")
            
            # Create moderation request
            request = ModerationRequest(
                user_query=query,
                conversation_id="test-123"
            )
            
            # Test moderation
            try:
                response = await supervisor.moderate_request(request)
                
                # Show results
                status = "✅ ALLOWED" if response.allowed else "❌ REJECTED"
                print(f"   Result: {status}")
                print(f"   Decision: {response.decision.value}")
                print(f"   Reason: {response.reason[:100]}...")
                if response.intent:
                    print(f"   Intent: {response.intent.intent_type.value}")
                    print(f"   Tools: {response.intent.tools_needed}")
                if response.risk_factors:
                    print(f"   Risks: {response.risk_factors}")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Test direct content filtering
        print(f"\n🔧 Testing Content Filter Directly")
        print("-" * 30)
        
        for query in ["descrivi hello.py", "read hello.py"]:
            filter_result = supervisor.filter_content(query)
            print(f"Query: '{query}'")
            print(f"  Safe: {filter_result.is_safe}")
            print(f"  Confidence: {filter_result.confidence}")
            print(f"  Risks: {filter_result.detected_risks}")
            print(f"  Explanation: {filter_result.explanation}")
            print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_pattern_matching():
    """Test pattern matching directly."""
    print("\n🧪 Testing Pattern Matching")
    print("=" * 30)
    
    import re
    
    # Test patterns
    italian_read_patterns = [
        r'leggi.*file', r'mostra.*contenuto', r'visualizza.*file', r'descrivi.*file',
        r'descrivi.*\.', r'apri.*file', r'contenuto.*di', r'vedi.*file'
    ]
    
    test_queries = [
        "descrivi hello.py",
        "leggi config.txt",
        "mostra contenuto di test.py"
    ]
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        matches = []
        for pattern in italian_read_patterns:
            if re.search(pattern, query.lower(), re.IGNORECASE):
                matches.append(pattern)
        
        if matches:
            print(f"  ✅ Matches patterns: {matches}")
        else:
            print(f"  ❌ No pattern matches")
            
        # Test keyword matching
        italian_keywords = [
            'leggi', 'scrivi', 'crea', 'salva', 'elimina', 'rimuovi', 'cancella',
            'modifica', 'aggiorna', 'cambia', 'edita', 'descrivi', 'apri',
            'contenuto', 'vedi', 'visualizza', 'aggiungi', 'elenca'
        ]
        
        found_keywords = [kw for kw in italian_keywords if kw in query.lower()]
        if found_keywords:
            print(f"  ✅ Contains keywords: {found_keywords}")
        else:
            print(f"  ❌ No keywords found")

if __name__ == "__main__":
    test_pattern_matching()
    asyncio.run(test_supervisor_italian())
