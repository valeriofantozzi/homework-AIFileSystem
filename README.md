# 🚀 **AI File-System Agent**

> A production-ready agent that **reads, writes & reasons** about your files, chats with you locally, and ships as an ⚡️ _MCP server_ — all wrapped in Clean-Architecture goodness.

---

## ✨ Why It’s Cool

| 🧩 Layer       | ⭐️ Highlights                                                       |
| -------------- | -------------------------------------------------------------------- |
| **Agent Core** | ReAct-style planner, lightweight guard model, multi-agent supervisor |
| **Tools**      | Sandbox-safe CRUD, memory recall, LLM-powered Q&A                    |
| **Chat UI**    | Zero-install CLI with streaming markdown & safe refusals             |
| **MCP Server** | FastAPI wrapper, manifest ready for Claude Desktop / Cursor          |
| **Dev-Ops**    | Dockerfile, CI hooks, Bandit security scan, health checks            |

---

## 🗂️ Project Tour

```text
agent/            🤖  Core planning, guard & supervisor
tools/            🛠️  CRUD, memory & helper toolkits
chat_interface/   💬  Local CLI chat UI
server/           🌐  MCP server & Docker deployment
config/           ⚙️  Model routing & .env management
tests/            ✅  Pytest coverage (CRUD, reasoning, MCP)
DOCS/             📚  ADRs, architecture & guides
logs/             📝  Rotating runtime logs
```

---

## ✅ Implementation Checklist

- **Fixed Workspace Sandbox** `workspace_fs/workspace.py`
- **CRUD Tools** `list_files`, `read_file`, `write_file`, `delete_file`
- **ReAct Planning Loop** `core/react_loop.py`
- **CLI Chat Interface** `chat_interface/cli_chat/chat.py`
- **Safe Refusals** `core/secure_agent.py`
- **MCP Server & Manifest** `server/api_mcp/mcp_server.py`, `mcp_config.json`
- **Docker & Health Checks** `server/docker/*`, `deployment/health_check.py`

### 🌟 Bonus Achievements

| 🌟 Bonus                 | ✔️ Status | 📎 Evidence                                        |
| ------------------------ | --------- | -------------------------------------------------- |
| Pytest Suite             | **Done**  | `tests/`                                           |
| Safe & Aligned Behaviour | **Done**  | Guard model + refusal demo                         |
| Lightweight Guard Model  | **Done**  | `config/models.yaml` (`groq:llama-3.1-8b-instant`) |

### 🎁 Extra Goodies

- **Multi-Agent Supervisor** `agent/supervisor/`
- **Memory Tools** `tools/memory_tools/`
- **Diagnostics CLI** `agent/diagnostic_cli.py`
- **CI & Static-Analysis** Bandit report, Makefile, `ci_validate.py`
- **Extensive Docs & ADRs** in `DOCS/`
- **Rotating Logs** auto-created in `logs/`

---

## ⚡️ Quick Start

```bash
# Install deps
poetry install && poetry shell

# Chat locally
python -m chat_interface.cli_chat.chat
```

### 🌐 Run the MCP Server

```bash
# Dev mode (FastAPI on :8000)
python -m server.api_mcp.mcp_server
```

_or_ via Docker 🐳:

```bash
docker compose up --build
```

### 🧪 Run Tests

```bash
pytest -q
```

---

## 💬 Sample Conversation

```text
You ▸ list python files updated last
Agent ▸ (uses list_files → read_file) … shows filenames
You ▸ show me the contents of math_utils.py
Agent ▸ …returns file snippet with syntax highlighting
```

_See_ `demo_cli_features.py` _for a full scripted run._

---

## 🛠️ Dev Notes

- **Clean Architecture** ensures high cohesion & low coupling.
- **Security-First**: path traversal blocked, guard model, Bandit scan.
- **Plug-and-Play**: drop new tools under `tools/` and register — they auto-expose.

---

## 📜 License

Released under the MIT License — do awesome things! ✌️
