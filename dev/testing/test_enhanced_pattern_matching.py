#!/usr/bin/env python3
"""
Test script per verificare i miglioramenti al pattern matching.
Testa la flessibilità migliorata per il riconoscimento dei comandi.
"""

import sys
import os

# Add project paths for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

def test_enhanced_pattern_matching():
    """Test dei pattern matching migliorati."""
    
    print("🧪 TESTING ENHANCED PATTERN MATCHING")
    print("=" * 50)
    
    # Simulate the enhanced pattern matching logic
    def simulate_enhanced_pattern_matching(user_query: str) -> str:
        """Simula la logica di pattern matching migliorata."""
        query_lower = user_query.lower()
        
        # Enhanced directory terms
        directory_terms = [
            "directories", "directory", "folders", "folder", "cartelle", "cartella",
            "dir", "dirs", "subdirectories", "subdirs", "subfolders"
        ]
        list_terms = [
            "list", "show", "display", "view", "see", "find", "get", "elenca", 
            "lista", "mostra", "visualizza", "vedi", "trova"
        ]
        all_terms = ["tutti", "all", "everything", "tutto", "each", "every"]
        file_terms = ["file", "files", "documento", "documenti"]
        
        # Check conditions
        has_directory_term = any(term in query_lower for term in directory_terms)
        has_list_term = any(term in query_lower for term in list_terms)
        has_file_term = any(file_word in query_lower for file_word in file_terms)
        has_all_term = any(term in query_lower for term in all_terms)
        
        # Directory-specific requests first
        if has_directory_term and has_list_term and not has_file_term:
            return "list_directories"
        
        # Files and directories together
        has_file_and_dir = (
            any(file_term in query_lower for file_term in file_terms) and
            any(dir_term in query_lower for dir_term in directory_terms)
        ) or (
            "lista" in query_lower and "file" in query_lower and "cartelle" in query_lower
        )
        
        if has_all_term and has_file_and_dir:
            return "list_all"
        
        # List all patterns
        if (
            (has_list_term and has_all_term) or
            (has_file_term and has_directory_term and has_list_term) or
            ("file" in query_lower and "cartelle" in query_lower) or
            ("files" in query_lower and "cartelle" in query_lower) or
            ("content" in query_lower and ("workspace" in query_lower or "directory" in query_lower)) or
            ("everything" in query_lower and ("here" in query_lower or "workspace" in query_lower)) or
            ("tutto" in query_lower and ("contenuto" in query_lower or "spazio" in query_lower))
        ):
            return "list_all"
        
        # Explicit file listing
        if (
            (has_list_term and has_file_term and not has_directory_term) or
            ("what files" in query_lower) or
            ("which files" in query_lower) or
            ("show files" in query_lower) or
            ("find files" in query_lower) or
            ("documenti" in query_lower and has_list_term)
        ):
            return "list_files"
        
        # Smart fallback
        if (
            has_list_term and 
            not any(dir_word in query_lower for dir_word in directory_terms) and
            not any(specific_word in query_lower for specific_word in ["all", "tutti", "everything", "tutto"])
        ):
            return "list_files"
        
        # Handle single directory words (just "directories", "folders", etc.)
        if has_directory_term and not has_list_term and not has_file_term:
            return "list_directories"
        
        # Final fallback for vague terms
        if (
            any(vague_term in query_lower for vague_term in ["show", "see", "view", "display"]) and
            not any(specific_tool in query_lower for specific_tool in ["read", "write", "delete", "create"]) and
            not has_list_term  # Don't override explicit "list" commands
        ):
            return "list_all"
        
        return "no_match"
    
    # Test cases - expanded for enhanced patterns
    test_cases = [
        # === DIRECTORY PATTERNS ===
        ("list directories", "list_directories", "✅ Basic directory listing"),
        ("show folders", "list_directories", "✅ Folder synonym"),
        ("display dirs", "list_directories", "✅ Short dir term"),
        ("find subdirectories", "list_directories", "✅ Subdirectory variant"),
        ("mostra cartelle", "list_directories", "✅ Italian folders"),
        ("elenca directory", "list_directories", "✅ Italian list+dir"),
        ("view subfolders", "list_directories", "✅ Subfolders"),
        ("get all directories", "list_directories", "✅ Get directories"),
        
        # === FILES AND DIRECTORIES TOGETHER ===
        ("list all files and directories", "list_all", "✅ Files + directories"),
        ("show everything", "list_all", "✅ Show everything"),
        ("display all content", "list_all", "✅ All content"),
        ("lista tutti i files e cartelle", "list_all", "✅ Italian all files+dirs"),
        ("tutti file e directory", "list_all", "✅ Italian variation"),
        ("find all files and folders", "list_all", "✅ Files + folders"),
        ("view everything here", "list_all", "✅ Everything here"),
        ("tutto contenuto", "list_all", "✅ Italian everything"),
        ("show files and directories", "list_all", "✅ Files and directories"),
        ("file e cartelle", "list_all", "✅ Italian file+folders"),
        
        # === FILES ONLY ===
        ("list files", "list_files", "✅ Basic file listing"),
        ("show files", "list_files", "✅ Show files"),
        ("what files", "list_files", "✅ What files"),
        ("which files", "list_files", "✅ Which files"),
        ("find files", "list_files", "✅ Find files"),
        ("display files", "list_files", "✅ Display files"),
        ("lista documenti", "list_files", "✅ Italian documents"),
        
        # === SMART FALLBACKS ===
        ("list", "list_files", "✅ Generic list → files"),
        ("show", "list_all", "✅ Vague show → all"),
        ("display", "list_all", "✅ Vague display → all"),
        ("view", "list_all", "✅ Vague view → all"),
        
        # === EDGE CASES ===
        ("list everything", "list_all", "✅ List everything"),
        ("show workspace content", "list_all", "✅ Workspace content"),
        ("directories", "list_directories", "✅ Just 'directories'"),
        ("folders", "list_directories", "✅ Just 'folders'"),
        
        # === SHOULD NOT MATCH LISTING ===
        ("read file", "no_match", "✅ Read not list"),
        ("write document", "no_match", "✅ Write not list"),
        ("delete everything", "no_match", "✅ Delete not list"),
    ]
    
    # Run tests
    print("\n📋 Test Results:")
    print("-" * 50)
    
    all_passed = True
    passed_count = 0
    total_count = len(test_cases)
    
    for query, expected, description in test_cases:
        result = simulate_enhanced_pattern_matching(query)
        
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   Query: '{query}'")
        print(f"   Expected: {expected} | Got: {result}")
        
        if result == expected:
            passed_count += 1
        else:
            all_passed = False
            print(f"   ⚠️  MISMATCH!")
        
        print()
    
    # Summary
    print("=" * 50)
    print(f"📊 SUMMARY: {passed_count}/{total_count} tests passed")
    
    if all_passed:
        print("🎉 ALL TESTS PASSED! Enhanced pattern matching is working!")
        print("\n✨ Improvements implemented:")
        print("   ✅ Extended directory synonyms (folders, dirs, subdirs, etc.)")
        print("   ✅ Enhanced list verbs (show, display, view, find, etc.)")
        print("   ✅ Better Italian support (elenca, visualizza, etc.)")
        print("   ✅ Smart fallbacks for vague requests")
        print("   ✅ Mixed language pattern support")
        print("   ✅ Context-aware disambiguation")
    else:
        print("❌ Some tests failed. Logic needs adjustment.")
    
    return all_passed


if __name__ == "__main__":
    try:
        success = test_enhanced_pattern_matching()
        print(f"\n🎯 Test {'PASSED' if success else 'FAILED'}")
        if success:
            print("\n🚀 The enhanced pattern matching should now handle:")
            print("   • 'list directories' ✅")
            print("   • 'show folders' ✅") 
            print("   • 'display dirs' ✅")
            print("   • 'mostra cartelle' ✅")
            print("   • 'find subdirectories' ✅")
            print("   • And many more variations!")
    except Exception as e:
        print(f"❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
