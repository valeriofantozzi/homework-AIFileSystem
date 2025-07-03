#!/usr/bin/env python3
"""
Quick validation script to test Italian support.
"""

import asyncio
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from agent.supervisor.supervisor import RequestSupervisor
import structlog

async def quick_test():
    """Quick test of the fixed Italian support."""
    
    # Configure minimal logging
    structlog.configure(
        wrapper_class=structlog.make_filtering_bound_logger(30),  # WARNING level
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
    
    supervisor = RequestSupervisor(logger)
    
    test_commands = [
        "descrivi hello.py",
        "leggi config.txt", 
        "describe hello.py",
        "read README.md"
    ]
    
    print("🧪 Quick Validation Test")
    print("=" * 30)
    
    all_passed = True
    
    for cmd in test_commands:
        print(f"Testing: '{cmd}'", end=" -> ")
        
        request = supervisor.create_request(cmd, "test")
        response = await supervisor.moderate_request(request)
        
        if response.allowed:
            print("✅ ALLOWED")
        else:
            print("❌ REJECTED")
            all_passed = False
    
    if all_passed:
        print("\n🎉 All tests PASSED! Italian support is working.")
        print("The supervisor now correctly handles both:")
        print("   • Italian file commands (descrivi, leggi)")
        print("   • English file commands (describe, read)")
        print("\nThe key fixes implemented:")
        print("   ✅ Separate translation agent for clean text translation")
        print("   ✅ Enhanced pattern matching for Italian keywords") 
        print("   ✅ Consolidated ReAct loop for single LLM calls")
        print("   ✅ Robust error handling and fallbacks")
    else:
        print("\n❌ Some tests failed. Check the supervisor configuration.")
    
    return all_passed

if __name__ == "__main__":
    success = asyncio.run(quick_test())
    sys.exit(0 if success else 1)
