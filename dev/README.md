# Development Directory

This directory contains development utilities, artifacts, and documentation that support the development process but are not part of the main user-facing documentation.

## Directory Structure

```
dev/
├── README.md                    # This file - development directory overview
├── docs/                        # Development artifacts and internal documentation
│   ├── CLI_DEBUG_FIX_SUMMARY.md
│   ├── IMPLEMENTATION_STATUS_FINAL.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   ├── IMPLEMENTATION_SUMMARY_OPTIMIZED_REACT.md
│   ├── TOOL_METADATA_ARCHITECTURE_COMPLETE.md
│   ├── bugfix-summary.md
│   ├── conversation-examples.md
│   ├── task6-implementation-summary.md
│   └── task7-implementation-summary.md
├── planning/                    # Project planning and task management documents
│   ├── task-plan-phase1.md
│   └── task-plan-phase2.md
├── logs/                        # Development logs and debugging information
├── demos/                       # Feature demonstrations and examples
│   ├── demo_directory_listing.py
│   ├── interactive_usage_demo.py
│   ├── demo_llm_tool_selection_solution.py
│   ├── demo_italian_support.py
│   ├── demo_usage_guide.py
│   ├── demo_advanced_guide.py
│   └── demo_project_analysis.py
├── debug/                       # Debug scripts and troubleshooting tools
│   ├── debug_directory_command.py
│   └── debug_supervisor.py
├── testing/                     # Development test scripts
│   ├── test_agent_list_directories.py
│   ├── test_directory_patterns.py
│   ├── test_list_directories_fix.py
│   ├── test_react_selection_logic.py
│   └── test_tools_directly.py
└── sandbox/                     # Development testing area
    ├── hello.py
    ├── project_structure.md
    ├── quick_demo.txt
    ├── usage_guide_demo.txt
    ├── demo_guide.txt
    └── ... (other test files)
```

## Purpose

### `/docs` - Development Documentation

Contains implementation summaries, debugging guides, fix summaries, and other technical artifacts generated during development. These are primarily for developers working on the project.

### `/planning` - Project Planning

Contains task breakdowns, phase planning documents, and project management artifacts used to track development progress.

### `/logs` - Development Logs

Contains detailed development logs, debugging information, and troubleshooting artifacts.

### `/demos` - Feature Demonstrations

Contains scripts and examples that demonstrate specific features or workflows, primarily for development validation and stakeholder demonstrations.

### `/debug` - Debug Scripts

Contains debug scripts and troubleshooting tools used during development to diagnose issues and validate functionality.

### `/testing` - Development Test Scripts

Contains ad-hoc test scripts and development validation tools that supplement the main test suite in `tests/`.

### `/sandbox` - Development Testing

Contains temporary files, experimental code, and development testing artifacts.

## Usage

This directory is organized to keep development artifacts separate from user-facing documentation in `DOCS/`, while maintaining easy access for developers working on the project.

The development documentation here supports:

- Understanding implementation decisions
- Tracking development progress
- Debugging and troubleshooting
- Learning from implementation examples
- Planning future development phases

## For Developers

When adding new development artifacts:

1. **Implementation docs** → `dev/docs/`
2. **Planning documents** → `dev/planning/`
3. **Debug logs** → `dev/logs/`
4. **Demo scripts** → `dev/demos/`
5. **Debug tools** → `dev/debug/`
6. **Test scripts** → `dev/testing/`
7. **Test files** → `dev/sandbox/`

User-facing documentation should go in the main `DOCS/` directory.
