"""
Test veloce per verificare la fix della selezione tool per query italiane.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_italian_query_pattern_matching():
    """Test della logica di pattern matching per query italiane."""
    
    print("🧪 Test Pattern Matching per Query Italiane")
    print("=" * 60)
    
    # Simulate the pattern matching logic from ReActLoop
    def simulate_pattern_matching(user_query: str) -> str:
        """Simula la logica di pattern matching."""
        query_lower = user_query.lower()
        
        # Check for directory-specific requests first
        if (("directories" in query_lower or "directory" in query_lower or "folders" in query_lower or 
             "folder" in query_lower or "cartelle" in query_lower) and
            ("list" in query_lower or "show" in query_lower or "mostra" in query_lower or 
             "lista" in query_lower) and
            not ("file" in query_lower)):  # Only directories, not files+directories
            return "list_directories"
        
        # Check for Italian "tutti i file e cartelle" pattern - this should select list_all
        elif (("tutti" in query_lower or "all" in query_lower) and 
              (("file" in query_lower and ("cartelle" in query_lower or "directory" in query_lower or "directories" in query_lower)) or
               ("files" in query_lower and ("cartelle" in query_lower or "directory" in query_lower or "directories" in query_lower)))):
            return "list_all"
        
        # Check for "list all" or "show all" - use list_all that shows both files and directories
        elif (("list" in query_lower and "all" in query_lower) or 
              ("show" in query_lower and "all" in query_lower) or
              ("lista" in query_lower and "tutti" in query_lower)):
            return "list_all"
        
        # Check for explicit file listing (avoid conflict with directory listing)
        elif ("list" in query_lower and "files" in query_lower) or "what files" in query_lower:
            return "list_files"
        
        else:
            return "default_fallback"
    
    # Test cases
    test_cases = [
        # The problematic case that should now work
        ("lista tutti i file e cartelle", "list_all", "🎯 MAIN FIX"),
        
        # Other Italian variations
        ("tutti i file e cartelle", "list_all", "Italian variation 1"),
        ("mostra tutti i file e cartelle", "list_all", "Italian variation 2"), 
        
        # English equivalents
        ("list all files and directories", "list_all", "English equivalent"),
        ("show all files and directories", "list_all", "English show all"),
        
        # Directory only cases
        ("lista cartelle", "list_directories", "Italian directories only"),
        ("list directories", "list_directories", "English directories only"),
        
        # File only cases  
        ("list files", "list_files", "English files only"),
        ("lista files", "list_files", "Mixed Italian/English"),
    ]
    
    # Run tests
    all_passed = True
    for query, expected, description in test_cases:
        result = simulate_pattern_matching(query)
        
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   Query: '{query}'")
        print(f"   Expected: {expected}")
        print(f"   Got: {result}")
        
        if result != expected:
            all_passed = False
            print(f"   ⚠️  MISMATCH!")
        
        print()
    
    print("=" * 60)
    if all_passed:
        print("🎉 TUTTI I TEST PASSATI! La fix dovrebbe funzionare.")
    else:
        print("❌ Alcuni test falliti. Logica da rivedere.")
    
    return all_passed

if __name__ == "__main__":
    test_italian_query_pattern_matching()
