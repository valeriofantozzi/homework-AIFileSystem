# Comprehensive Project Report

_(Synthesized from the entire design conversation – free of sou├── tests/ # unit + e2e
├── mcp_config.json
├── pyproject.toml + poetry.lock (or requirements.txt)
└── README.md # architecture, setup, usage, security model, ready for peer-level engineering review.)_

---

## 1. Purpose & Scope

**Goal.** Deliver a production-quality _tool-using autonomous agent_ that:

1. **Understands natural-language tasks** and plans a multi-step solution (ReAct-style reasoning loop).
2. **Operates strictly inside a sandboxed workspace** (one predefined directory on disk).
3. **Exposes five file-oriented capabilities** – list, read, write, delete, and cross-file Q&A – as callable tools.
4. **Supports local interaction** (CLI/UI) _and_ remote integration through an MCP-compliant server endpoint.
5. Demonstrates **robust engineering practices**: modular packaging, high test coverage, policy-based safety, CI/CD, and clear documentation.

The assignment must be completed in four intense development days, _including_ bonus features (security filter, ≥ 80 % coverage, structured logs, demo UI).

---

## 2. Hard Constraints

| Constraint                                       | Implication for design                                                                                                       |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| **Fixed base directory** at agent start-up       | All file paths resolved relative to this root; no absolute or “..” traversal permitted.                                      |
| **No tool accepts directory paths**              | Public APIs receive _filenames only_. Any “pathlike” input is rejected up-front.                                             |
| **All interactions scoped to workspace**         | Symlinks, device nodes, or mounts outside the root are blocked.                                                              |
| **Internal planning loop** (ReAct / Reflexion)   | Agent must iteratively: **THINK → ACT(tool) → OBSERVE → THINK … → FINAL**.                                                   |
| **Multi-tool chaining** in one turn              | Example: “read the latest modified file” triggers list → timestamp sort → read → respond.                                    |
| **Directory structure must match specification** | Mandatory top-level folders: `agent/`, `tools/`, `chat_interface/`, `server/`, `tests/`, plus manifest and dependency files. |

---

## 3. High-Level Architecture

User ──▶ chat_interface (CLI / Streamlit)
│
▼
orchestrator_lite (light LLM gatekeeper & router)
│
▲ allowed? │ ┌───────────────────────────┐
│ └──▶│ SecureAgent (ReAct LLM) │
│ └─────┬───────────┬────────┘
│ │ │
│ direct tool call ◀┘ │ ReAct loop invokes…
│ ▼
│ File-system tools
│ │
└────────── logs & metrics ◀────┘

### Key Layers & Packages

| Layer / Package                       | Responsibility                                                                                                                  | Notes                                     |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| **`workspace_fs`** (in `tools/`)      | Safe path resolution, CRUD primitives, rate limiting, size quotas.                                                              | Pure Python, zero external deps.          |
| **`crud_tools`** (in `tools/`)        | Thin wrappers that expose the five required capabilities as "Pydantic-AI tools".                                                | Depend on `workspace_fs`.                 |
| **`config`** (in `config/`)           | Environment and model configuration system with secure API key management and provider flexibility.                             | Centralized configuration with templates. |
| **`orchestrator_lite`** (in `agent/`) | Small LLM (`gpt-4o-mini`) that performs safety moderation _and_ intent extraction. Returns JSON with `{allowed, intent, args}`. | Uses configured models via `config`.      |
| **`agent_core`** (in `agent/`)        | Builds `SecureAgent`: registers tools, runs full LLM (`gpt-4o`) in ReAct mode when orchestrator decides a complex question.     | Model selection via configuration system. |
| **`chat_interface`**                  | `cli_chat` (Rich TTY) and optional `demo_streamlit`.                                                                            | Consume `agent_core` with env configs.    |
| **`server`**                          | FastAPI app exposing `/mcp` endpoint plus `mcp_config.json`.                                                                    | Compatible with Cursor/IDE clients.       |
| **`tests`**                           | Unit and end-to-end suites; use `FakeChatModel` where LLM determinism required.                                                 | Coverage target ≥ 80 %.                   |

---

## 4. Security & Safety Design

| Measure                            | Detail                                                                                                                                |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| **Sandbox enforcement**            | Every filename passes through `safe_join`; traversal and symlinks blocked.                                                            |
| **Rate limiting**                  | Per-instance window (e.g., 50 ops/s) prevents runaway loops.                                                                          |
| **Size limits**                    | Read/Write caps (default 64 KB) guard against large payload attacks.                                                                  |
| **Light-LLM moderation**           | Orchestrator denies prompts with jailbreak strings, traversal attempts, secret extraction, or policy violations before any tool runs. |
| **Structured logging**             | `structlog` JSON per conversation + per tool call for audit/tracing.                                                                  |
| **Container hardening (optional)** | Rootless Docker, `noexec` mount for workspace, cgroups for CPU/RAM, default seccomp profile.                                          |

---

## 5. Deliverable Directory Layout

/project-root
├── agent/
│ ├── core/ # SecureAgent, ReAct logic
│ └── orchestrator/ # LLM gatekeeper
├── config/ # Environment and model configuration
│ ├── env/ # Environment template files
│ └── models.yaml # Model definitions
├── tools/
│ ├── workspace_fs/ # sandbox & FS helpers
│ └── crud_tools/ # list/read/write/delete/answer tools
├── chat_interface/
│ ├── cli_chat/
│ └── demo_streamlit/ # optional bonus
├── server/
│ └── api_mcp/ # FastAPI endpoint and manifest
├── tests/ # unit + e2e
├── manage_env.py # Environment management CLI
├── demo_env_system.py # Configuration demo
├── ENV_SETUP.md # Setup documentation
├── .env.\*.template # Environment templates
├── mcp_config.json
├── pyproject.toml + poetry.lock (or requirements.txt)
└── README.md # architecture, setup, usage, security model

_Each sub-package is individually installable (`pip install -e`)._

---

## 6. Development Timeline (4-Day Sprint)

| Day                               | Focus                                                                                                    | Milestones                                                                   |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| **0 (Kick-off)**                  | Repo bootstrap, CI skeleton, poetry workspace.                                                           | Lint & test hooks green on empty repo.                                       |
| **1 (FS Layer)**                  | Implement `workspace_fs` with 4 CRUD ops + rate & size guards, ≥ 95 % coverage.                          | All traversal/symlink tests pass.                                            |
| **2 (Tools & Agent)**             | Build `crud_tools`, write/delete/answer; create `SecureAgent` with ReAct loop; unit tests with Fake LLM. | CLI smoke test “write→read” succeeds.                                        |
| **3 (Orchestrator & Interfaces)** | Add `orchestrator_lite`; integrate with agent; FastAPI MCP server; Streamlit demo UI; end-to-end tests.  | CLI shows Thoughts-Actions-Observations chain; `/mcp` endpoint returns JSON. |
| **4 (Polish & Docs)**             | Boost coverage to 80 %, write README, build rootless Docker image, finalize CI/CD and badges.            | `docker run` demo, docs reviewed, zip/tag for submission.                    |

---

## 7. Testing Strategy

- **Unit tests** per library – path guards, rate limit, tool happy+fail paths.
- **E2E tests** – simulate multi-tool queries (“read newest file”, “delete then list”).
- **Mock LLM** – deterministic responses for orchestration and planning verification.
- **Coverage gates** – CI fails if total < 80 % or `workspace_fs` < 95 %.
- **Static analysis** – Ruff, Black, Bandit in pre-commit and CI.

---

## 8. Logging & Observability

- **Conversation log** – JSONL file per `conversation_id` (user, agent thoughts, tool actions, final reply).
- **Audit trail** – each tool call emits event with timestamp, filename, size; ready for aggregation.
- **Debug CLI flag** – `--debug` prints the entire ReAct scratchpad live.

---

## 9. Deployment & Integration

- **MCP server** – single POST `/mcp` taking `conversation_id` & `prompt`; returns agent response JSON.
- **Docker** – slim Python 3.12 image running uvicorn; volume-mount workspace.
- **IDE plug-in** – any MCP-aware client points to `endpoint` in `mcp_config.json`.

---

## 10. Bonus Features Embedded from Day 1

- Quick demo UI (Streamlit) for non-terminal stakeholders.
- Coverage badge & CI matrix (unit, lint, e2e).
- Animated CLI recording (asciinema) in README.
- Modular packages ready for independent release.

---

## 11. Environment & Model Configuration System

### Configuration Architecture

The project implements a sophisticated configuration system that separates concerns across multiple dimensions:

| Dimension       | Options                                  | Purpose                                                               |
| --------------- | ---------------------------------------- | --------------------------------------------------------------------- |
| **Environment** | local, development, testing, production  | Different deployment contexts with appropriate security levels        |
| **Provider**    | OpenAI, Anthropic, Gemini, Groq, local   | Multiple LLM providers for flexibility and cost optimization          |
| **Role**        | agent, orchestrator, file_analysis, chat | Different models for different use cases and performance requirements |

### Key Features

- **Secure API Key Management**: Environment-specific `.env` files with comprehensive templates
- **Model Flexibility**: YAML-based model definitions with capability descriptions
- **Environment Isolation**: Complete separation of development, testing, and production configurations
- **CLI Management**: `config/manage_env.py` tool for setup, validation, and environment listing
- **Template System**: Pre-configured templates for quick environment setup
- **Validation**: Built-in validation for API keys, model availability, and configuration completeness

### Configuration Files

```
config/
├── model_config.py      # Core configuration system
├── env_loader.py        # Environment variable loading
├── models.yaml          # Model definitions and capabilities
├── exceptions.py        # Configuration-specific exceptions
├── __init__.py         # Public API
├── manage_env.py       # CLI tool for environment management
├── demo_env_system.py  # Configuration system demonstration
├── ENV_SETUP.md        # Environment setup documentation
└── env/                # Environment template files
    ├── .env.template           # Quick setup template
    ├── .env.local.template     # Local development template
    ├── .env.development.template # Development environment template
    ├── .env.testing.template   # Testing environment template
    └── .env.production.template # Production environment template

manage_env.py           # CLI tool for environment management
demo_env_system.py      # Configuration system demonstration
ENV_SETUP.md           # Comprehensive setup guide
```

### Usage Workflow

1. **Environment Setup**: `python config/manage_env.py setup --env development`
2. **Configuration**: Edit generated `config/.env.development` file with API keys
3. **Validation**: `python config/manage_env.py validate --env development`
4. **Integration**: Use `ModelConfig` class throughout the application
5. **Environment Switching**: Change `ENVIRONMENT` variable to switch contexts

This system ensures secure, flexible, and maintainable configuration management across all deployment scenarios.

---

### Summary

The project is a tightly scoped but production-ready autonomous agent platform:

- **Security-first** sandboxed filesystem access.
- **LLM-driven** planning (ReAct) and gatekeeping (mini orchestrator).
- **Modular codebase** with reusable libraries, high test coverage and continuous integration.
- **Compliant deliverables** matching the exact folder spec of the assignment.
