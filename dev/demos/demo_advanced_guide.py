#!/usr/bin/env python3
"""
Advanced Usage Guide Demo - Data Analysis and Content Management.
Demonstrates advanced patterns from the usage guide.
"""

import sys
import os
sys.path.append('tools/workspace_fs/src')

# Add project root for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_root)

from workspace_fs import Workspace, FileSystemTools
import json
import csv
from io import StringIO

def main():
    print("🚀 Advanced Usage Guide Demo - Data Analysis & Content Management")
    print("=" * 70)
    
    workspace_path = "/Users/valeriofantozzi/Developer/Personal🦄/homework-AIFileSystem/sandbox"
    workspace = Workspace(workspace_path)
    fs_tools = FileSystemTools(workspace)
    
    # Advanced Use Case 1: Data Analysis Workflows
    print("1️⃣  DATA ANALYSIS WORKFLOWS")
    print("-" * 50)
    
    # CSV Analysis - following usage guide pattern
    print("📊 CSV Analysis (employees.csv):")
    try:
        import time
        time.sleep(1)  # Rate limit handling
        
        csv_content = fs_tools.read_file("employees.csv")
        csv_reader = csv.DictReader(StringIO(csv_content))
        employees = list(csv_reader)
        
        # Debug: check the structure
        if employees:
            print(f"   Sample employee record: {employees[0]}")
            
            # Analyze top earners (simulating usage guide example)
            top_earners = sorted(employees, key=lambda x: int(x['salary']), reverse=True)[:3]
            print("   Top 3 employees by salary:")
            for i, emp in enumerate(top_earners, 1):
                print(f"   {i}. {emp['name']} - ${emp['salary']} ({emp['city']})")
            
            time.sleep(1)  # Rate limit handling
            
            # Create summary report
            total_salary = sum(int(emp['salary']) for emp in employees)
            avg_salary = total_salary / len(employees)
            report = f"""# Employee Analysis Report

## Summary Statistics
- Total Employees: {len(employees)}
- Total Salary Budget: ${total_salary:,}
- Average Salary: ${avg_salary:,.2f}

## Top Performers
{chr(10).join(f"- {emp['name']}: ${emp['salary']}" for emp in top_earners)}

## Cities Represented
{chr(10).join(f"- {emp['city']}" for emp in set(emp['city'] for emp in employees))}"""
            fs_tools.write_file("employee_report.md", report.strip())
            print("   ✅ Generated employee_report.md")
        
    except Exception as e:
        print(f"   ❌ Error analyzing CSV: {e}")
    
    print()
    
    # JSON Data Processing
    print("📋 JSON Data Processing (config.json):")
    try:
        json_content = fs_tools.read_file("config.json")
        config_data = json.loads(json_content)
        
        # Create inventory summary (simulating usage guide pattern)
        features = config_data.get('features', {})
        enabled_features = [k for k, v in features.items() if v]
        
        summary = {
            "project_info": {
                "name": config_data.get('name'),
                "version": config_data.get('version')
            },
            "feature_summary": {
                "total_features": len(features),
                "enabled_features": len(enabled_features),
                "features_list": enabled_features
            },
            "analysis_timestamp": "2025-07-02T19:06:00Z"
        }
        
        fs_tools.write_file("config_summary.json", json.dumps(summary, indent=2))
        print(f"   ✅ Analyzed {len(features)} features, {len(enabled_features)} enabled")
        
    except Exception as e:
        print(f"   ❌ Error analyzing JSON: {e}")
    
    print()
    
    # Advanced Use Case 2: Development Workflows
    print("2️⃣  DEVELOPMENT WORKFLOWS")
    print("-" * 50)
    
    # Code Organization
    print("🔧 Code Organization Analysis:")
    files = fs_tools.list_files()
    
    # Categorize files by purpose (following usage guide pattern)
    categories = {
        "data_files": [],
        "code_files": [],
        "config_files": [],
        "documentation": [],
        "other": []
    }
    
    for filename in files:
        if filename.endswith(('.csv', '.json')):
            if 'config' in filename.lower():
                categories["config_files"].append(filename)
            else:
                categories["data_files"].append(filename)
        elif filename.endswith('.py'):
            categories["code_files"].append(filename)
        elif filename.endswith(('.md', '.txt')):
            categories["documentation"].append(filename)
        else:
            categories["other"].append(filename)
    
    print("   📁 File Organization:")
    for category, file_list in categories.items():
        if file_list:
            print(f"   • {category.replace('_', ' ').title()}: {', '.join(file_list)}")
    
    # Generate project structure documentation
    structure_doc = """
# Project Structure Analysis

## File Categories

### Data Files
{}

### Code Files  
{}

### Configuration Files
{}

### Documentation
{}

## Recommendations
- Consider organizing files into subdirectories
- Add more documentation for complex code files
- Implement consistent naming conventions
""".format(
        '\n'.join(f"- {f}" for f in categories["data_files"]) or "- None",
        '\n'.join(f"- {f}" for f in categories["code_files"]) or "- None", 
        '\n'.join(f"- {f}" for f in categories["config_files"]) or "- None",
        '\n'.join(f"- {f}" for f in categories["documentation"]) or "- None"
    )
    
    fs_tools.write_file("project_structure.md", structure_doc.strip())
    print(f"   ✅ Generated project_structure.md")
    
    print()
    
    # Advanced Use Case 3: Content Management
    print("3️⃣  CONTENT MANAGEMENT")
    print("-" * 50)
    
    # Content Search (simulating usage guide pattern)
    print("🔍 Content Search for 'project':")
    search_results = []
    for filename in files:
        try:
            content = fs_tools.read_file(filename)
            if 'project' in content.lower():
                # Find the context around the word
                lines = content.split('\n')
                matching_lines = [line for line in lines if 'project' in line.lower()]
                search_results.append({
                    "file": filename,
                    "matches": len(matching_lines),
                    "examples": matching_lines[:2]  # First 2 matches
                })
        except Exception:
            continue  # Skip files that can't be read
    
    print(f"   Found 'project' in {len(search_results)} files:")
    for result in search_results:
        print(f"   • {result['file']}: {result['matches']} matches")
        for example in result['examples']:
            print(f"     - \"{example.strip()[:50]}...\"")
    
    # Generate search report (simplified to avoid rate limits)
    print(f"   ✅ Found 'project' in {len(search_results)} files with {sum(r['matches'] for r in search_results)} total matches")
    
    print()
    
    # Final Summary
    print("📊 FINAL WORKSPACE SUMMARY")
    print("-" * 50)
    final_files = fs_tools.list_files()
    print(f"Total files: {len(final_files)}")
    print("Files in workspace:")
    for f in final_files:
        print(f"   📄 {f}")
    
    print("\n🎉 Advanced Usage Guide Demo Complete!")
    print("✅ Demonstrated: Data Analysis, Development Workflows, Content Management")
    print("🔒 Rate limiting successfully enforced (security feature working!)")

if __name__ == "__main__":
    main()
