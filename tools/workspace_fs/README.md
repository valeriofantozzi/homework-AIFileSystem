# 🗂️ workspace_fs — Secure Workspace File System Tools 🔒

Welcome to **workspace_fs**!  
This package delivers safe, high-cohesion file system operations for AI agents and apps—sandboxed, tested, and ready for production.  
If you need to list, read, write, or delete files securely in a workspace, you’re in the right place. 🦾

---

## What’s Inside? 📦

- **src/**: 🧩 All core logic (Workspace, FileSystemTools, path safety, etc.)
- **tests/**: 🧪 Unit and integration tests (80%+ coverage target)
- **Makefile**: 🛠️ One-liner CI, lint, test, and coverage commands
- **ci_validate.py**: 🤖 Python CI script for local/CI automation
- **pyproject.toml**: 📦 Poetry + tool config (ruff, pytest, bandit)
- **bandit-report.json**: 🔍 Security scan results
- **.github-actions-example.yml**: 🚦 GitHub Actions CI template

---

## Key Features & Principles ✨

- **Sandbox Enforcement**: All file ops are locked to a workspace root—no path traversal, no symlinks, no surprises
- **High Cohesion, Low Coupling**: Each module/class does one thing, and does it well
- **SOLID & Clean**: No business logic in I/O, no hidden state, no global singletons
- **Security by Default**: Bandit, ruff, and coverage checks in every pipeline
- **Extensible**: Add new file ops or policies with minimal friction
- **Poetry-First**: All dev/test/lint flows use Poetry

---

## Quickstart 🚀

```bash
# Install dependencies
poetry install

# Run all CI checks (lint, security, test, coverage)
make ci

# Or run the full pipeline (install + ci + coverage report)
make all
```

---

## Usage Example 🧑‍💻

```python
from workspace_fs import Workspace, FileSystemTools

# Initialize a secure workspace
workspace = Workspace("/path/to/workspace")
fs_tools = FileSystemTools(workspace)

# List files
files = fs_tools.list_files()

# Read a file
content = fs_tools.read_file("example.txt")

# Write a file
fs_tools.write_file("new_file.txt", "content")

# Delete a file
fs_tools.delete_file("old_file.txt")
```

---

## CI/CD & Quality Gates 🛡️

- **Linting**: `make lint` (ruff)
- **Security**: `make security` (bandit)
- **Testing**: `make test` (pytest + coverage)
- **Coverage**: `make coverage` (HTML report)
- **All-in-one**: `make ci` or `python ci_validate.py`
- **GitHub Actions**: See `.github-actions-example.yml` for ready-to-go CI

---

## Architecture & Best Practices 🏛️

- **No secrets in code**: All config via env or pyproject.toml
- **No domain logic in I/O**: Pure file ops, no business rules
- **No cyclic deps**: Clean, layered design
- **Testable**: 80%+ coverage, clear API boundaries

---

**Build secure, testable, and maintainable file system tools—one safe operation at a time!** 🛡️🗂️
