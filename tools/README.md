# 🧰 tools/ — Modular Tools for AI Agents & Apps 🚀

Welcome to the **tools** layer!  
This directory is your toolbox for building, extending, and customizing AI-powered systems.  
Each subpackage is high-cohesion, low-coupling, and ready for plug-and-play integration. 🦾🔌

---

## What’s Inside? 📦

- **crud_tools/**: 🛠️ Core CRUD operations, LLM-powered question answering, and adapters
- **memory_tools/**: 🧠 Conversation memory, context management, and session persistence
- **workspace_fs/**: 🗂️ Secure, sandboxed file system operations for safe agent actions

---

## Key Principles & Features ✨

- **High Cohesion**: Each tool does one thing, and does it well
- **Low Coupling**: No hidden dependencies—import only what you need
- **SOLID & Clean**: No business logic in infrastructure, no global state
- **Extensible**: Add new tools or swap implementations with minimal friction
- **Poetry-First**: All packages use Poetry for dev, test, and CI

---

## Quickstart 🚀

```bash
# Install dependencies for a tool package (e.g., workspace_fs)
cd tools/workspace_fs
poetry install

# Run all CI checks
make ci

# Or run tests directly
poetry run pytest
```

---

## Subpackage Overview 🗂️

| Package         | Purpose & Highlights                                    |
| --------------- | ------------------------------------------------------- |
| `crud_tools/`   | 🛠️ CRUD ops, LLM-powered tools, adapters, and utilities |
| `memory_tools/` | 🧠 Conversation/session memory for context-aware agents |
| `workspace_fs/` | 🗂️ Secure, sandboxed file system for safe agent actions |

---

## Best Practices 🏛️

- **No secrets in code**: All config via env or pyproject.toml
- **No cyclic deps**: Each tool is independently testable and replaceable
- **Testable**: 80%+ coverage targets, clear API boundaries
- **Composable**: Mix and match tools to build your own agent stack

---

**Build smarter, safer, and more modular AI systems—one tool at a time!** 🧰✨
